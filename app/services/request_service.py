"""
Blood Request Management & Allocation Service.
Implements:
1. Urgency-driven prioritization (Critical > Urgent > Routine, tiebreak by requested_at ASC).
2. Transaction-safe approval with SELECT ... FOR UPDATE pessimistic row-locking.
3. Blood compatibility enforcement.
4. Double-allocation prevention via unique constraints and audit trail.
"""
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy import case, and_
from app.extensions import db
from app.models.request import BloodRequest, RequestFulfillment
from app.models.inventory import BloodUnit
from app.models.requester import Requester
from app.services.compatibility_service import get_compatible_donor_types

def create_blood_request(
    requester_id: int,
    blood_type_requested: str,
    units_requested: int,
    urgency: str = 'routine'
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Submits a new blood request into the pending admin queue.
    """
    if units_requested <= 0:
        return False, "Units requested must be a positive integer greater than zero.", {}

    valid_urgencies = ('critical', 'urgent', 'routine')
    if urgency not in valid_urgencies:
        return False, f"Invalid urgency level: {urgency}. Must be one of {valid_urgencies}.", {}

    requester = Requester.query.get(requester_id)
    if not requester:
        return False, f"Requester with ID {requester_id} not found.", {}

    try:
        req = BloodRequest(
            requester_id=requester_id,
            blood_type_requested=blood_type_requested,
            units_requested=units_requested,
            urgency=urgency,
            status='pending',
            requested_at=datetime.utcnow()
        )
        db.session.add(req)
        db.session.commit()

        return True, "Blood request submitted successfully and queued for approval.", req.to_dict()
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to submit blood request: {str(e)}", {}


def get_prioritized_request_queue(status: str = 'pending') -> List[BloodRequest]:
    """
    Returns blood requests ordered by urgency-driven priority:
    1. Urgency: 'critical' (Rank 1) -> 'urgent' (Rank 2) -> 'routine' (Rank 3)
    2. FIFO Tie-breaker: requested_at ASC (earliest submitted gets priority)

    Utilizes the composite index (status, urgency, requested_at).
    """
    urgency_order = case(
        (BloodRequest.urgency == 'critical', 1),
        (BloodRequest.urgency == 'urgent', 2),
        (BloodRequest.urgency == 'routine', 3),
        else_=4
    )

    query = BloodRequest.query
    if status:
        query = query.filter(BloodRequest.status == status)

    return query.order_by(urgency_order.asc(), BloodRequest.requested_at.asc()).all()


def approve_blood_request(
    request_id: int,
    admin_user_id: int
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Transaction-safe, concurrency-isolated request approval:
    1. Locks the blood_request row and compatible blood_unit rows using SELECT ... FOR UPDATE.
    2. Validates compatibility rules to find acceptable donor blood types.
    3. Allocates units using FEFO (First Expired, First Out) ordering.
    4. Creates RequestFulfillment records (unique unit_id prevents double-allocation).
    5. Updates BloodUnit status to 'used' and BloodRequest status to 'approved'.
    6. Commits atomically. If inventory is insufficient or an error occurs, rolls back.
    """
    try:
        # Atomic database transaction block
        with db.session.begin_nested():
            # Lock the request row
            req = (
                BloodRequest.query
                .filter(BloodRequest.id == request_id)
                .with_for_update()
                .first()
            )

            if not req:
                return False, f"Blood request #{request_id} not found.", {}

            if req.status != 'pending':
                return False, f"Request #{request_id} cannot be approved because its status is '{req.status}'.", {}

            # Step 1: Identify compatible donor blood types
            compatible_types = get_compatible_donor_types(req.blood_type_requested)
            now = datetime.utcnow()

            # Step 2: Fetch candidate available units with pessimistic row-locking (FOR UPDATE)
            # FEFO strategy: order by expires_at ASC so older viable blood is used first
            candidate_units = (
                BloodUnit.query
                .filter(
                    BloodUnit.status == 'available',
                    BloodUnit.blood_type.in_(compatible_types),
                    BloodUnit.expires_at > now
                )
                .order_by(
                    # Prefer exact match first, then compatible, then earliest expiry
                    case((BloodUnit.blood_type == req.blood_type_requested, 0), else_=1).asc(),
                    BloodUnit.expires_at.asc()
                )
                .with_for_update()
                .limit(req.units_requested)
                .all()
            )

            # Step 3: Validate inventory sufficiency under lock
            if len(candidate_units) < req.units_requested:
                available_count = (
                    BloodUnit.query
                    .filter(
                        BloodUnit.status == 'available',
                        BloodUnit.blood_type.in_(compatible_types),
                        BloodUnit.expires_at > now
                    )
                    .count()
                )
                return False, (
                    f"Insufficient compatible inventory for request #{request_id}. "
                    f"Required: {req.units_requested} units of type {req.blood_type_requested} "
                    f"(compatible with {compatible_types}), but only {available_count} unit(s) currently available."
                ), {
                    'required_units': req.units_requested,
                    'available_units': available_count,
                    'compatible_types': compatible_types
                }

            # Step 4: Allocate units and write audit records
            allocated_units_info = []
            for unit in candidate_units:
                unit.status = 'used'

                fulfillment = RequestFulfillment(
                    request_id=req.id,
                    unit_id=unit.id,
                    allocated_at=now
                )
                db.session.add(fulfillment)

                allocated_units_info.append({
                    'unit_id': unit.id,
                    'blood_type': unit.blood_type,
                    'expires_at': unit.expires_at.isoformat()
                })

            # Step 5: Mark request approved
            req.status = 'approved'
            req.resolved_at = now
            req.resolved_by = admin_user_id

        # Commit transaction
        db.session.commit()

        return True, f"Request #{request_id} approved successfully. {len(allocated_units_info)} units allocated.", {
            'request_id': req.id,
            'status': req.status,
            'allocated_units': allocated_units_info,
            'resolved_at': req.resolved_at.isoformat(),
            'resolved_by': admin_user_id
        }

    except Exception as e:
        db.session.rollback()
        return False, f"Transaction error during request approval: {str(e)}", {}


def reject_blood_request(
    request_id: int,
    admin_user_id: int,
    reason: Optional[str] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Rejects a pending blood request with an explicit reason for requester audit.
    """
    try:
        req = BloodRequest.query.filter(BloodRequest.id == request_id).first()
        if not req:
            return False, f"Blood request #{request_id} not found.", {}

        if req.status != 'pending':
            return False, f"Request #{request_id} cannot be rejected because its status is '{req.status}'.", {}

        now = datetime.utcnow()
        req.status = 'rejected'
        req.rejection_reason = reason or "Rejected by blood bank administration."
        req.resolved_at = now
        req.resolved_by = admin_user_id

        db.session.commit()

        return True, f"Request #{request_id} rejected.", {
            'request_id': req.id,
            'status': req.status,
            'rejection_reason': req.rejection_reason,
            'resolved_at': req.resolved_at.isoformat()
        }
    except Exception as e:
        db.session.rollback()
        return False, f"Error rejecting request: {str(e)}", {}
