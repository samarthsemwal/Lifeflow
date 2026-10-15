"""
Donation Intake Service.
Enforces eligibility checks and provides transaction-safe atomic creation of
Donation and BloodUnit records.
"""
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from app.extensions import db
from app.models.donor import Donor
from app.models.inventory import BloodUnit, Donation
from app.services.eligibility_service import check_donor_eligibility

def record_donation(
    donor_id: int,
    notes: Optional[str] = None,
    donation_date: Optional[datetime] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Executes a transaction-safe donation intake:
    1. Verifies donor existence and server-side eligibility (age 18+, 90-day rule).
    2. Atomically creates a BloodUnit and a Donation record inside a single DB transaction.
    3. Updates the donor's last_donation_date.
    4. Rolls back both if any database or constraint error occurs.

    Returns:
        (success: bool, message: str, data: dict)
    """
    donor = Donor.query.get(donor_id)
    if not donor:
        return False, f"Donor with ID {donor_id} not found.", {}

    now = donation_date or datetime.utcnow()

    # Step 1: Server-side eligibility validation
    is_eligible, reason, meta = check_donor_eligibility(donor, target_date=now.date())
    if not is_eligible:
        return False, reason, meta

    # Step 2: Atomic Transaction for BloodUnit + Donation creation
    try:
        # Create blood unit (42-day viability)
        unit = BloodUnit(
            blood_type=donor.blood_type,
            collected_at=now,
            expires_at=BloodUnit.calculate_expiry(now),
            status='available'
        )
        db.session.add(unit)
        db.session.flush()  # Generates unit.id within the active transaction

        # Create donation log
        donation = Donation(
            donor_id=donor.id,
            unit_id=unit.id,
            donated_at=now,
            notes=notes
        )
        db.session.add(donation)
        db.session.flush()

        # Link unit back to donation for bi-directional traceability
        unit.donation_id = donation.id

        # Update donor's last donation date
        donor.last_donation_date = now.date()

        # Atomic commit
        db.session.commit()

        return True, "Donation recorded successfully and blood unit added to inventory.", {
            'donation_id': donation.id,
            'unit_id': unit.id,
            'blood_type': unit.blood_type,
            'collected_at': unit.collected_at.isoformat(),
            'expires_at': unit.expires_at.isoformat(),
            'donor_id': donor.id,
            'last_donation_date': donor.last_donation_date.isoformat()
        }

    except Exception as e:
        db.session.rollback()
        return False, f"Transaction error during donation intake: {str(e)}", {}
