"""
Inventory Management Service.
Handles real-time inventory aggregation, expiration checks, and stock level alerts.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import func
from app.extensions import db
from app.models.inventory import BloodUnit
from app.models.donor import BLOOD_TYPES

LOW_STOCK_THRESHOLD = 3
EXPIRING_SOON_DAYS = 7

def get_realtime_inventory_summary() -> Dict[str, Any]:
    """
    Returns live available blood unit counts grouped by blood type.
    Ensures all 8 blood types are represented even if count is 0.
    Filters out any units that have passed their expiration date.
    """
    now = datetime.utcnow()

    # Optimized single aggregation query using the composite index (status, blood_type)
    counts_query = (
        db.session.query(BloodUnit.blood_type, func.count(BloodUnit.id).label('count'))
        .filter(
            BloodUnit.status == 'available',
            BloodUnit.expires_at > now
        )
        .group_by(BloodUnit.blood_type)
        .all()
    )

    counts_dict = {row.blood_type: row.count for row in counts_query}

    # Build consistent 8-type dictionary with status indicators
    inventory_by_type = {}
    total_available_units = 0
    low_stock_types = []

    for b_type in BLOOD_TYPES:
        count = counts_dict.get(b_type, 0)
        total_available_units += count
        is_low = count < LOW_STOCK_THRESHOLD
        if is_low:
            low_stock_types.append(b_type)

        inventory_by_type[b_type] = {
            'blood_type': b_type,
            'count': count,
            'is_low_stock': is_low,
            'status': 'critical' if count == 0 else ('low' if is_low else 'adequate')
        }

    # Count expiring soon units (within 7 days)
    expiring_soon_threshold = now + timedelta(days=EXPIRING_SOON_DAYS)
    expiring_soon_count = (
        db.session.query(func.count(BloodUnit.id))
        .filter(
            BloodUnit.status == 'available',
            BloodUnit.expires_at > now,
            BloodUnit.expires_at <= expiring_soon_threshold
        )
        .scalar()
    ) or 0

    return {
        'timestamp': now.isoformat(),
        'total_units': total_available_units,
        'expiring_soon_count': expiring_soon_count,
        'low_stock_types': low_stock_types,
        'low_stock_count': len(low_stock_types),
        'inventory': inventory_by_type
    }


def get_units_list(blood_type: str = None, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Returns unit-level details with optional filtering for staff/admin inspection.
    """
    query = BloodUnit.query

    if blood_type:
        query = query.filter(BloodUnit.blood_type == blood_type)
    if status:
        query = query.filter(BloodUnit.status == status)

    units = query.order_by(BloodUnit.expires_at.asc()).limit(limit).all()
    return [unit.to_dict() for unit in units]


def update_expired_units() -> int:
    """
    Maintenance task: marks any units past their expiry date as 'expired'.
    Returns number of units updated.
    """
    now = datetime.utcnow()
    expired_units = (
        BloodUnit.query
        .filter(
            BloodUnit.status == 'available',
            BloodUnit.expires_at <= now
        )
        .all()
    )

    for unit in expired_units:
        unit.status = 'expired'

    if expired_units:
        db.session.commit()

    return len(expired_units)
