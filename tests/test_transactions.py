import concurrent.futures
from datetime import datetime, timedelta
from app.models.inventory import BloodUnit, Donation
from app.models.request import BloodRequest, RequestFulfillment
from app.services.donation_service import record_donation
from app.services.request_service import approve_blood_request

def test_donation_intake_transaction_safety(db_session, eligible_donor):
    """
    Verifies that donation intake atomically creates both a BloodUnit and Donation record,
    updating the donor's last_donation_date in a single commit.
    """
    initial_donations = Donation.query.filter(Donation.donor_id == eligible_donor.id).count()
    initial_units = BloodUnit.query.filter(BloodUnit.blood_type == eligible_donor.blood_type).count()

    success, msg, data = record_donation(donor_id=eligible_donor.id, notes="Test atomic donation")

    assert success is True
    assert "Donation recorded successfully" in msg
    assert data['unit_id'] is not None

    # Check both records exist in DB
    unit = BloodUnit.query.get(data['unit_id'])
    donation = Donation.query.get(data['donation_id'])

    assert unit is not None
    assert donation is not None
    assert unit.blood_type == eligible_donor.blood_type
    assert unit.status == 'available'
    assert donation.unit_id == unit.id
    assert eligible_donor.last_donation_date == datetime.utcnow().date()


def test_concurrent_request_approvals_scarce_unit_concurrency(app, admin_user, requester_user):
    """
    Concurrency Race Condition Test:
    Two concurrent approval operations compete for a SINGLE available unit.
    Asserts:
    1. SELECT ... FOR UPDATE and transactional locking prevent double-allocation.
    2. Exactly ONE request succeeds and is marked 'approved'.
    3. The second request fails safely with an 'insufficient inventory' message.
    4. Total available inventory drops to 0 (never negative).
    5. Exactly one RequestFulfillment row is inserted for the scarce unit.
    """
    with app.app_context():
        # Setup: Create exactly 1 scarce unit of AB-
        now = datetime.utcnow()
        scarce_unit = BloodUnit(
            blood_type='AB-',
            collected_at=now,
            expires_at=now + timedelta(days=30),
            status='available'
        )
        app.extensions['sqlalchemy'].session.add(scarce_unit)

        # Create two competing requests, each needing 1 unit of AB-
        req1 = BloodRequest(
            requester_id=requester_user.id,
            blood_type_requested='AB-',
            units_requested=1,
            urgency='urgent',
            status='pending',
            requested_at=now - timedelta(minutes=10)
        )
        req2 = BloodRequest(
            requester_id=requester_user.id,
            blood_type_requested='AB-',
            units_requested=1,
            urgency='critical',
            status='pending',
            requested_at=now - timedelta(minutes=5)
        )
        app.extensions['sqlalchemy'].session.add_all([req1, req2])
        app.extensions['sqlalchemy'].session.commit()

        req1_id = req1.id
        req2_id = req2.id
        admin_id = admin_user.id

    results = []

    def run_approval(request_id):
        with app.app_context():
            return approve_blood_request(request_id=request_id, admin_user_id=admin_id)

    # Launch two concurrent approval threads simultaneously against MySQL
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_approval, req1_id)
        f2 = executor.submit(run_approval, req2_id)
        results = [f1.result(), f2.result()]

    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    # Exactly one approval must succeed
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
    # Exactly one approval must fail
    assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}: {results}"

    assert "Insufficient compatible inventory" in failures[0][1]

    # Verify database consistency under inspection
    with app.app_context():
        final_req1 = BloodRequest.query.get(req1_id)
        final_req2 = BloodRequest.query.get(req2_id)

        # One approved, one remains pending
        statuses = {final_req1.status, final_req2.status}
        assert statuses == {'approved', 'pending'}

        # Physical unit status must be 'used'
        unit = BloodUnit.query.filter(BloodUnit.blood_type == 'AB-').first()
        assert unit.status == 'used'

        # Must have exactly 1 fulfillment record (No double-allocation)
        fulfillments = RequestFulfillment.query.filter(RequestFulfillment.unit_id == unit.id).all()
        assert len(fulfillments) == 1

        # Available count must be 0, never negative
        available_count = BloodUnit.query.filter(
            BloodUnit.blood_type == 'AB-',
            BloodUnit.status == 'available'
        ).count()
        assert available_count == 0
