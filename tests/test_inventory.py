from datetime import datetime, timedelta
from app.models.inventory import BloodUnit
from app.services.inventory_service import get_realtime_inventory_summary

def test_inventory_aggregate_and_expired_unit_filtering(db_session):
    """
    Asserts live inventory correctly groups available units and excludes expired units.
    """
    now = datetime.utcnow()

    # 2 available viable units of A+
    unit1 = BloodUnit(blood_type='A+', collected_at=now, expires_at=now + timedelta(days=30), status='available')
    unit2 = BloodUnit(blood_type='A+', collected_at=now, expires_at=now + timedelta(days=20), status='available')

    # 1 expired unit of A+ (Must NOT be counted as available)
    unit_expired = BloodUnit(blood_type='A+', collected_at=now - timedelta(days=50), expires_at=now - timedelta(days=5), status='available')

    # 1 used unit of A+ (Must NOT be counted)
    unit_used = BloodUnit(blood_type='A+', collected_at=now, expires_at=now + timedelta(days=30), status='used')

    # 4 available viable units of O-
    for _ in range(4):
        db_session.add(BloodUnit(blood_type='O-', collected_at=now, expires_at=now + timedelta(days=35), status='available'))

    db_session.add_all([unit1, unit2, unit_expired, unit_used])
    db_session.commit()

    summary = get_realtime_inventory_summary()

    # Only unit1 and unit2 should be counted for A+ (count = 2)
    assert summary['inventory']['A+']['count'] == 2
    assert summary['inventory']['A+']['is_low_stock'] is True  # 2 < 3 threshold

    # O- has 4 units
    assert summary['inventory']['O-']['count'] == 4
    assert summary['inventory']['O-']['is_low_stock'] is False

    # Total units = 2 (A+) + 4 (O-) = 6
    assert summary['total_units'] == 6


def test_inventory_expiring_soon_count(db_session):
    now = datetime.utcnow()

    # Unit expiring in 3 days (within 7-day window)
    unit_expiring = BloodUnit(blood_type='B+', collected_at=now, expires_at=now + timedelta(days=3), status='available')
    # Unit expiring in 25 days (outside 7-day window)
    unit_safe = BloodUnit(blood_type='B+', collected_at=now, expires_at=now + timedelta(days=25), status='available')

    db_session.add_all([unit_expiring, unit_safe])
    db_session.commit()

    summary = get_realtime_inventory_summary()
    assert summary['expiring_soon_count'] == 1
