from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func
from app.extensions import db
from app.models.donor import Donor, BLOOD_TYPES
from app.models.requester import Requester
from app.models.inventory import BloodUnit, Donation
from app.models.request import BloodRequest
from app.services.auth_service import role_required, get_current_user
from app.services.inventory_service import get_realtime_inventory_summary, get_units_list
from app.services.request_service import (
    get_prioritized_request_queue, approve_blood_request, reject_blood_request
)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    inventory_summary = get_realtime_inventory_summary()

    # Real DB aggregates
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

    # Top prioritized pending requests
    pending_queue = get_prioritized_request_queue(status='pending')[:5]

    return render_template(
        'admin/dashboard.html',
        metrics={
            'total_available_units': inventory_summary['total_units'],
            'expiring_soon_count': inventory_summary['expiring_soon_count'],
            'low_stock_count': inventory_summary['low_stock_count'],
            'pending_requests': pending_requests_count,
            'critical_requests': critical_requests_count,
            'fulfilled_requests': fulfilled_requests_count,
            'total_donors': total_donors,
            'total_requesters': total_requesters,
            'total_donations': total_donations
        },
        inventory_summary=inventory_summary['inventory'],
        low_stock_types=inventory_summary['low_stock_types'],
        pending_queue=pending_queue
    )


@admin_bp.route('/queue')
@role_required('admin')
def queue():
    status = request.args.get('status', 'pending')
    requests_list = get_prioritized_request_queue(status=status if status != 'all' else None)
    return render_template('admin/request_queue.html', requests=requests_list, current_status=status)


@admin_bp.route('/queue/<int:request_id>/approve', methods=['POST'])
@role_required('admin')
def approve_request_action(request_id):
    user = get_current_user()
    success, message, result = approve_blood_request(request_id=request_id, admin_user_id=user.id)

    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(request.referrer or url_for('admin.queue'))


@admin_bp.route('/queue/<int:request_id>/reject', methods=['POST'])
@role_required('admin')
def reject_request_action(request_id):
    user = get_current_user()
    reason = request.form.get('reason', '').strip()
    success, message, result = reject_blood_request(
        request_id=request_id,
        admin_user_id=user.id,
        reason=reason
    )

    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(request.referrer or url_for('admin.queue'))


@admin_bp.route('/units')
@role_required('admin')
def units_list():
    blood_type = request.args.get('blood_type')
    status = request.args.get('status')

    units = get_units_list(blood_type=blood_type, status=status)
    return render_template(
        'admin/units.html',
        units=units,
        blood_types=BLOOD_TYPES,
        selected_type=blood_type,
        selected_status=status
    )
