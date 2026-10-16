from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.donor import BLOOD_TYPES
from app.models.request import BloodRequest, URGENCY_LEVELS
from app.services.auth_service import role_required, get_current_user
from app.services.request_service import create_blood_request

requests_bp = Blueprint('requests', __name__)

@requests_bp.route('/new', methods=['GET', 'POST'])
@role_required('requester')
def new_request():
    user = get_current_user()
    requester = user.requester_profile

    if request.method == 'POST':
        blood_type = request.form.get('blood_type_requested')
        units_val = request.form.get('units_requested', '')
        urgency = request.form.get('urgency', 'routine')

        try:
            units = int(units_val)
        except ValueError:
            flash("Units requested must be a valid number.", "danger")
            return render_template('requests/create_request.html', blood_types=BLOOD_TYPES, urgencies=URGENCY_LEVELS)

        success, message, result = create_blood_request(
            requester_id=requester.id,
            blood_type_requested=blood_type,
            units_requested=units,
            urgency=urgency
        )

        if success:
            flash(message, "success")
            return redirect(url_for('requests.my_requests'))
        else:
            flash(message, "danger")

    return render_template(
        'requests/create_request.html',
        blood_types=BLOOD_TYPES,
        urgencies=URGENCY_LEVELS
    )


@requests_bp.route('/my-requests')
@role_required('requester')
def my_requests():
    user = get_current_user()
    requester = user.requester_profile

    requests = (
        BloodRequest.query
        .filter(BloodRequest.requester_id == requester.id)
        .order_by(BloodRequest.requested_at.desc())
        .all()
    )

    return render_template('requests/my_requests.html', requester=requester, requests=requests)
