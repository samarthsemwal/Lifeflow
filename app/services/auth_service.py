"""
Authentication & Authorization Service.
Handles registration, password validation, role checks, and session security.
"""
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, date
from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request
from app.extensions import db
from app.models.user import User
from app.models.donor import Donor, BLOOD_TYPES
from app.models.requester import Requester

def register_user(
    name: str,
    email: str,
    password: str,
    role: str,
    profile_data: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Registers a new user and creates their corresponding role profile atomically.
    Roles supported: 'admin', 'donor', 'requester'.
    """
    profile_data = profile_data or {}
    clean_email = email.strip().lower() if email else ''

    if not name or not clean_email or not password:
        return False, "Name, email, and password are required.", {}

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", {}

    if role not in User.ROLES:
        return False, f"Invalid role: {role}. Allowed roles: {User.ROLES}.", {}

    # Check for existing email
    existing = User.query.filter(User.email == clean_email).first()
    if existing:
        return False, f"An account with email '{clean_email}' already exists.", {}

    try:
        user = User(
            name=name.strip(),
            email=clean_email,
            role=role,
            created_at=datetime.utcnow()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Generates user.id

        # Profile creation based on role
        if role == 'donor':
            blood_type = profile_data.get('blood_type')
            dob_val = profile_data.get('date_of_birth')

            if not blood_type or blood_type not in BLOOD_TYPES:
                db.session.rollback()
                return False, f"Valid blood type is required for donors ({BLOOD_TYPES}).", {}

            if not dob_val:
                db.session.rollback()
                return False, "Date of birth is required for donors.", {}

            if isinstance(dob_val, str):
                try:
                    dob = datetime.strptime(dob_val, "%Y-%m-%d").date()
                except ValueError:
                    db.session.rollback()
                    return False, "Invalid date format for date_of_birth. Use YYYY-MM-DD.", {}
            elif isinstance(dob_val, date):
                dob = dob_val
            else:
                db.session.rollback()
                return False, "Invalid date of birth provided.", {}

            donor = Donor(
                user_id=user.id,
                blood_type=blood_type,
                date_of_birth=dob
            )
            db.session.add(donor)

        elif role == 'requester':
            org_name = profile_data.get('organization_name') or name.strip()
            phone = profile_data.get('contact_phone') or ''

            if not phone:
                db.session.rollback()
                return False, "Contact phone number is required for requesters.", {}

            requester = Requester(
                user_id=user.id,
                organization_name=org_name,
                contact_phone=phone.strip()
            )
            db.session.add(requester)

        db.session.commit()
        return True, f"User registered successfully as {role}.", user.to_dict()

    except Exception as e:
        db.session.rollback()
        return False, f"Registration failed: {str(e)}", {}


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[User]]:
    """
    Authenticates a user by email and password.
    """
    clean_email = email.strip().lower() if email else ''
    if not clean_email or not password:
        return False, "Email and password are required.", None

    user = User.query.filter(User.email == clean_email).first()
    if not user or not user.check_password(password):
        return False, "Invalid email or password.", None

    return True, "Login successful.", user


def login_user_session(user: User):
    """Stores user information in the Flask session."""
    session.clear()
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_email'] = user.email
    session['user_role'] = user.role


def logout_user_session():
    """Clears user session."""
    session.clear()


def get_current_user() -> Optional[User]:
    """Retrieves active user from database based on session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


def role_required(*allowed_roles):
    """
    Decorator to enforce role-based access control on routes.
    Works for both HTML page routes and JSON API routes.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            user_role = session.get('user_role')

            is_api = request.path.startswith('/api/') or request.is_json

            if not user_id:
                if is_api:
                    return jsonify({'success': False, 'error': 'Authentication required.'}), 401
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login', next=request.path))

            if allowed_roles and user_role not in allowed_roles:
                if is_api:
                    return jsonify({'success': False, 'error': f"Access forbidden for role '{user_role}'."}), 403
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('auth.dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
