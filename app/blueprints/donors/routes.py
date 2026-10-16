from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.inventory import Donation
from app.services.auth_service import role_required, get_current_user
from app.services.eligibility_service import check_donor_eligibility
from app.services.donation_service import record_donation

donors_bp = Blueprint('donors', __name__)

@donors_bp.route('/dashboard')
@role_required('donor')
def dashboard():
    user = get_current_user()
    donor = user.donor_profile

    # Check live eligibility
    is_eligible, eligibility_msg, eligibility_meta = check_donor_eligibility(donor)

    # Get recent donations
    donations = (
        Donation.query
        .filter(Donation.donor_id == donor.id)
        .order_by(Donation.donated_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'donors/dashboard.html',
        donor=donor,
        is_eligible=is_eligible,
        eligibility_msg=eligibility_msg,
        eligibility_meta=eligibility_meta,
        recent_donations=donations
    )


@donors_bp.route('/donate', methods=['GET', 'POST'])
@role_required('donor')
def donate():
    user = get_current_user()
    donor = user.donor_profile

    if request.method == 'POST':
        notes = request.form.get('notes', '').strip()
        success, message, result = record_donation(donor_id=donor.id, notes=notes)

        if success:
            flash(message, "success")
            return redirect(url_for('donors.history'))
        else:
            flash(message, "danger")

    is_eligible, eligibility_msg, eligibility_meta = check_donor_eligibility(donor)

    return render_template(
        'donors/donate.html',
        donor=donor,
        is_eligible=is_eligible,
        eligibility_msg=eligibility_msg,
        eligibility_meta=eligibility_meta
    )


@donors_bp.route('/history')
@role_required('donor')
def history():
    user = get_current_user()
    donor = user.donor_profile

    donations = (
        Donation.query
        .filter(Donation.donor_id == donor.id)
        .order_by(Donation.donated_at.desc())
        .all()
    )

    return render_template('donors/history.html', donor=donor, donations=donations)
