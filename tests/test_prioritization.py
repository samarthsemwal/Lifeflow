from datetime import datetime, timedelta
from app.models.request import BloodRequest
from app.services.request_service import get_prioritized_request_queue

def test_urgency_priority_ordering(db_session, requester_user):
    """
    Asserts queue order is Critical (1) -> Urgent (2) -> Routine (3),
    regardless of submission timestamps.
    """
    now = datetime.utcnow()

    # 1. Routine submitted 5 hours ago (oldest)
    req_routine = BloodRequest(
        requester_id=requester_user.id,
        blood_type_requested='A+',
        units_requested=2,
        urgency='routine',
        status='pending',
        requested_at=now - timedelta(hours=5)
    )

    # 2. Urgent submitted 3 hours ago
    req_urgent = BloodRequest(
        requester_id=requester_user.id,
        blood_type_requested='B+',
        units_requested=1,
        urgency='urgent',
        status='pending',
        requested_at=now - timedelta(hours=3)
    )

    # 3. Critical submitted 30 minutes ago (newest)
    req_critical = BloodRequest(
        requester_id=requester_user.id,
        blood_type_requested='O-',
        units_requested=3,
        urgency='critical',
        status='pending',
        requested_at=now - timedelta(minutes=30)
    )

    db_session.add_all([req_routine, req_urgent, req_critical])
    db_session.commit()

    queue = get_prioritized_request_queue(status='pending')

    assert len(queue) == 3
    # Critical should be Rank 1 even though it was submitted last
    assert queue[0].id == req_critical.id
    assert queue[0].urgency == 'critical'

    # Urgent should be Rank 2
    assert queue[1].id == req_urgent.id
    assert queue[1].urgency == 'urgent'

    # Routine should be Rank 3
    assert queue[2].id == req_routine.id
    assert queue[2].urgency == 'routine'


def test_fifo_tiebreaker_within_same_urgency(db_session, requester_user):
    """
    Asserts requests with identical urgency are ordered by requested_at ASC (oldest first).
    """
    now = datetime.utcnow()

    # Older urgent request
    older_urgent = BloodRequest(
        requester_id=requester_user.id,
        blood_type_requested='O+',
        units_requested=1,
        urgency='urgent',
        status='pending',
        requested_at=now - timedelta(hours=4)
    )

    # Newer urgent request
    newer_urgent = BloodRequest(
        requester_id=requester_user.id,
        blood_type_requested='O+',
        units_requested=2,
        urgency='urgent',
        status='pending',
        requested_at=now - timedelta(hours=1)
    )

    db_session.add_all([newer_urgent, older_urgent])
    db_session.commit()

    queue = get_prioritized_request_queue(status='pending')

    assert len(queue) == 2
    # FIFO: Older must appear before newer
    assert queue[0].id == older_urgent.id
    assert queue[1].id == newer_urgent.id
