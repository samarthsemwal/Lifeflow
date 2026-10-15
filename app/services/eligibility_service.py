"""
Donor Eligibility Service.
Enforces age requirements (18+) and the 90-day donation interval rule server-side.
"""
from datetime import date, timedelta
from typing import Tuple, Optional, Dict, Any
from app.models.donor import Donor

MINIMUM_DONOR_AGE = 18
DONATION_INTERVAL_DAYS = 90

def check_donor_eligibility(donor: Donor, target_date: Optional[date] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Checks donor eligibility against age and 90-day interval rules.

    Returns:
        (is_eligible: bool, message: str, metadata: dict)
        Metadata includes: age, last_donation_date, next_eligible_date, days_remaining
    """
    check_date = target_date or date.today()

    # Rule 1: Age verification (Minimum 18 years)
    if not donor.date_of_birth:
        return False, "Date of birth is required to verify donor eligibility.", {"rule": "dob_missing"}

    # Exact age calculation accounting for leap years and month/day
    years = check_date.year - donor.date_of_birth.year - (
        (check_date.month, check_date.day) < (donor.date_of_birth.month, donor.date_of_birth.day)
    )

    if years < MINIMUM_DONOR_AGE:
        return False, (
            f"Donor is ineligible: must be at least {MINIMUM_DONOR_AGE} years of age. "
            f"Current age is {years}."
        ), {
            "rule": "under_age",
            "current_age": years,
            "minimum_age": MINIMUM_DONOR_AGE
        }

    # Rule 2: 90-Day Donation Interval Rule
    if donor.last_donation_date:
        days_since_last = (check_date - donor.last_donation_date).days

        if days_since_last < 0:
            return False, "Invalid donation record: last donation date cannot be in the future.", {
                "rule": "invalid_date"
            }

        if days_since_last < DONATION_INTERVAL_DAYS:
            next_eligible = donor.last_donation_date + timedelta(days=DONATION_INTERVAL_DAYS)
            days_remaining = (next_eligible - check_date).days
            formatted_date = next_eligible.strftime("%B %d, %Y")

            return False, (
                f"Donor is ineligible under the {DONATION_INTERVAL_DAYS}-day rule. "
                f"Last donation was {days_since_last} days ago. "
                f"Next eligible donation date is {formatted_date} ({days_remaining} day{'s' if days_remaining != 1 else ''} remaining)."
            ), {
                "rule": "interval_restriction",
                "days_since_last": days_since_last,
                "days_remaining": days_remaining,
                "next_eligible_date": next_eligible.isoformat(),
                "formatted_next_eligible_date": formatted_date
            }

    return True, "Donor is fully eligible to donate blood.", {
        "rule": "eligible",
        "current_age": years,
        "last_donation_date": donor.last_donation_date.isoformat() if donor.last_donation_date else None
    }
