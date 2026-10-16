"""
REST API Blueprint.
Strictly implements the API Surface defined in Section 6.4:
- /api/auth/register, /api/auth/login, /api/auth/logout
- /api/donors/donate, /api/donors/me/history
- /api/inventory, /api/admin/inventory/units
- /api/requests, /api/requests/me
- /api/admin/requests, /api/admin/requests/<id>/approve, /api/admin/requests/<id>/reject
- /api/admin/dashboard
"""
from flask import Blueprint, request, jsonify, session
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.donor import Donor
from app.models.requester import Requester
from app.models.inventory import BloodUnit, Donation
from app.models.request import BloodRequest
from app.services.auth_service import (
    register_user, authenticate_user, login_user_session, logout_user_session,
    role_required, get_current_user
)
from app.services.donation_service import record_donation
from app.services.request_service import (
    create_blood_request, get_prioritized_request_queue,
    approve_blood_request, reject_blood_request
)
from app.services.inventory_service import get_realtime_inventory_summary, get_units_list

api_bp = Blueprint('api', __name__)

# ----------------- Auth API Endpoints -----------------

@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or request.form.to_dict()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    profile_data = {
        'blood_type': data.get('blood_type'),
        'date_of_birth': data.get('date_of_birth'),
        'organization_name': data.get('organization_name'),
        'contact_phone': data.get('contact_phone')
    }

    success, message, user_data = register_user(name, email, password, role, profile_data)
    if not success:
        return jsonify({'success': False, 'error': message}), 400

    return jsonify({'success': True, 'message': message, 'user': user_data}), 201


@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or request.form.to_dict()
    email = data.get('email')
    password = data.get('password')

    success, message, user = authenticate_user(email, password)
    if not success or not user:
        return jsonify({'success': False, 'error': message}), 401

    login_user_session(user)
    return jsonify({
        'success': True,
        'message': message,
        'user': user.to_dict()
    }), 200


@api_bp.route('/auth/logout', methods=['POST'])
def api_logout():
    logout_user_session()
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200


# ----------------- Donor API Endpoints -----------------

@api_bp.route('/donors/donate', methods=['POST'])
@role_required('donor')
def api_donate():
    user = get_current_user()
    if not user or not user.donor_profile:
        return jsonify({'success': False, 'error': 'Donor profile not found.'}), 404

    data = request.get_json() or {}
    notes = data.get('notes')

    success, message, result = record_donation(donor_id=user.donor_profile.id, notes=notes)
    status_code = 201 if success else 400
    return jsonify({'success': success, 'message': message, 'data': result}), status_code


@api_bp.route('/donors/me/history', methods=['GET'])
@role_required('donor')
def api_donor_history():
    user = get_current_user()
    if not user or not user.donor_profile:
        return jsonify({'success': False, 'error': 'Donor profile not found.'}), 404

    donations = (
        Donation.query
        .filter(Donation.donor_id == user.donor_profile.id)
        .order_by(Donation.donated_at.desc())
        .all()
    )
    return jsonify({
        'success': True,
        'donor': user.donor_profile.to_dict(),
        'history': [d.to_dict() for d in donations]
    }), 200


# ----------------- Inventory API Endpoints -----------------

@api_bp.route('/inventory', methods=['GET'])
def api_inventory():
    summary = get_realtime_inventory_summary()
    return jsonify({'success': True, **summary}), 200


@api_bp.route('/admin/inventory/units', methods=['GET'])
@role_required('admin')
def api_admin_inventory_units():
    blood_type = request.args.get('blood_type')
    status = request.args.get('status')
    limit = int(request.args.get('limit', 100))

    units = get_units_list(blood_type=blood_type, status=status, limit=limit)
    return jsonify({'success': True, 'units': units, 'count': len(units)}), 200


# ----------------- Blood Request API Endpoints -----------------

@api_bp.route('/requests', methods=['POST'])
@role_required('requester')
def api_create_request():
    user = get_current_user()
    if not user or not user.requester_profile:
        return jsonify({'success': False, 'error': 'Requester profile not found.'}), 404

    data = request.get_json() or request.form.to_dict()
    blood_type = data.get('blood_type_requested')
    units = data.get('units_requested')
    urgency = data.get('urgency', 'routine')

    try:
        units = int(units)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Units requested must be a valid integer.'}), 400

    success, message, result = create_blood_request(
        requester_id=user.requester_profile.id,
        blood_type_requested=blood_type,
        units_requested=units,
        urgency=urgency
    )
    if not success:
        return jsonify({'success': False, 'error': message, 'message': message}), 400
    return jsonify({'success': True, 'message': message, 'request': result}), 201


@api_bp.route('/requests/me', methods=['GET'])
@role_required('requester')
def api_my_requests():
    user = get_current_user()
    if not user or not user.requester_profile:
        return jsonify({'success': False, 'error': 'Requester profile not found.'}), 404

    requests = (
        BloodRequest.query
        .filter(BloodRequest.requester_id == user.requester_profile.id)
        .order_by(BloodRequest.requested_at.desc())
        .all()
    )
    return jsonify({
        'success': True,
        'requester': user.requester_profile.to_dict(),
        'requests': [r.to_dict() for r in requests]
    }), 200


# ----------------- Admin Queue & Approval API Endpoints -----------------

@api_bp.route('/admin/requests', methods=['GET'])
@role_required('admin')
def api_admin_requests():
    status = request.args.get('status', 'pending')
    queue = get_prioritized_request_queue(status=status)
    return jsonify({
        'success': True,
        'count': len(queue),
        'queue': [r.to_dict() for r in queue]
    }), 200


@api_bp.route('/admin/requests/<int:request_id>/approve', methods=['POST'])
@role_required('admin')
def api_admin_approve_request(request_id):
    user = get_current_user()
    success, message, result = approve_blood_request(request_id=request_id, admin_user_id=user.id)
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'data': result}), status_code


@api_bp.route('/admin/requests/<int:request_id>/reject', methods=['POST'])
@role_required('admin')
def api_admin_reject_request(request_id):
    user = get_current_user()
    data = request.get_json() or {}
    reason = data.get('reason')

    success, message, result = reject_blood_request(
        request_id=request_id,
        admin_user_id=user.id,
        reason=reason
    )
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'data': result}), status_code


@api_bp.route('/admin/dashboard', methods=['GET'])
@role_required('admin')
def api_admin_dashboard():
    """
    Computes real aggregate counts directly from the database — never mocked.
    """
    inventory_summary = get_realtime_inventory_summary()

    total_donors = db.session.query(func.count(Donor.id)).scalar() or 0
    total_requesters = db.session.query(func.count(Requester.id)).scalar() or 0
    total_donations = db.session.query(func.count(Donation.id)).scalar() or 0

    pending_requests_count = (
        db.session.query(func.count(BloodRequest.id))
        .filter(BloodRequest.status == 'pending')
        .scalar()
    ) or 0

    critical_requests_count = (
        db.session.query(func.count(BloodRequest.id))
        .filter(BloodRequest.status == 'pending', BloodRequest.urgency == 'critical')
        .scalar()
    ) or 0

    fulfilled_requests_count = (
        db.session.query(func.count(BloodRequest.id))
        .filter(BloodRequest.status == 'approved')
        .scalar()
    ) or 0

    return jsonify({
        'success': True,
        'metrics': {
            'total_available_units': inventory_summary['total_units'],
            'expiring_soon_count': inventory_summary['expiring_soon_count'],
            'low_stock_types_count': inventory_summary['low_stock_count'],
            'pending_requests': pending_requests_count,
            'critical_requests': critical_requests_count,
            'fulfilled_requests': fulfilled_requests_count,
            'total_registered_donors': total_donors,
            'total_registered_requesters': total_requesters,
            'total_donations_recorded': total_donations
        },
        'inventory_summary': inventory_summary['inventory'],
        'low_stock_types': inventory_summary['low_stock_types']
    }), 200
