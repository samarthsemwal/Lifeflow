"""
LifeFlow Service Layer.
Pure domain business logic decoupled from HTTP transport.
"""
from app.services.compatibility_service import is_compatible, get_compatible_donor_types
from app.services.eligibility_service import check_donor_eligibility
from app.services.inventory_service import get_realtime_inventory_summary, get_units_list
from app.services.donation_service import record_donation
from app.services.request_service import (
    create_blood_request, get_prioritized_request_queue,
    approve_blood_request, reject_blood_request
)
from app.services.auth_service import (
    register_user, authenticate_user, login_user_session,
    logout_user_session, get_current_user, role_required
)

__all__ = [
    'is_compatible',
    'get_compatible_donor_types',
    'check_donor_eligibility',
    'get_realtime_inventory_summary',
    'get_units_list',
    'record_donation',
    'create_blood_request',
    'get_prioritized_request_queue',
    'approve_blood_request',
    'reject_blood_request',
    'register_user',
    'authenticate_user',
    'login_user_session',
    'logout_user_session',
    'get_current_user',
    'role_required',
]
