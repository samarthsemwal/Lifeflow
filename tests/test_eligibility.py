from datetime import date, timedelta
from app.models.donor import Donor
from app.services.eligibility_service import check_donor_eligibility

def test_donor_under_18_rejected():
    today = date.today()
    # 17 years old
    dob = today - timedelta(days=365 * 17)
    donor = Donor(date_of_birth=dob, blood_type='O+', last_donation_date=None)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert not eligible
    assert meta['rule'] == 'under_age'
    assert "at least 18 years of age" in msg


def test_donor_exactly_18_eligible():
    today = date.today()
    # Exactly 18 years old today
    dob = date(today.year - 18, today.month, today.day)
    donor = Donor(date_of_birth=dob, blood_type='A+', last_donation_date=None)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert eligible
    assert meta['rule'] == 'eligible'
    assert "fully eligible" in msg


def test_90_day_rule_boundary_89_days_rejected():
    today = date.today()
    dob = date(today.year - 25, today.month, today.day)
    # Donated 89 days ago (1 day short of the 90-day requirement)
    last_donation = today - timedelta(days=89)
    donor = Donor(date_of_birth=dob, blood_type='B+', last_donation_date=last_donation)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert not eligible
    assert meta['rule'] == 'interval_restriction'
    assert meta['days_since_last'] == 89
    assert meta['days_remaining'] == 1
    assert "Next eligible donation date is" in msg
    expected_next = (last_donation + timedelta(days=90)).isoformat()
    assert meta['next_eligible_date'] == expected_next


def test_90_day_rule_boundary_90_days_eligible():
    today = date.today()
    dob = date(today.year - 25, today.month, today.day)
    # Donated exactly 90 days ago
    last_donation = today - timedelta(days=90)
    donor = Donor(date_of_birth=dob, blood_type='B+', last_donation_date=last_donation)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert eligible
    assert meta['rule'] == 'eligible'


def test_first_time_donor_eligible():
    today = date.today()
    dob = date(today.year - 22, today.month, today.day)
    donor = Donor(date_of_birth=dob, blood_type='AB-', last_donation_date=None)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert eligible
    assert meta['rule'] == 'eligible'


def test_future_donation_date_rejected():
    today = date.today()
    dob = date(today.year - 22, today.month, today.day)
    future_date = today + timedelta(days=5)
    donor = Donor(date_of_birth=dob, blood_type='AB+', last_donation_date=future_date)

    eligible, msg, meta = check_donor_eligibility(donor, target_date=today)
    assert not eligible
    assert meta['rule'] == 'invalid_date'
