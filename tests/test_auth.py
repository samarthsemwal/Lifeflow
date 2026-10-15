from app.models.user import User
from app.services.auth_service import register_user, authenticate_user

def test_password_hashing_and_security(db_session):
    """Asserts passwords are never stored in plaintext and use PBKDF2/Werkzeug."""
    raw_pass = "SecureSecretPassword123"
    success, msg, user_data = register_user(
        name="Security Tester",
        email="security@lifeflow.org",
        password=raw_pass,
        role="donor",
        profile_data={'blood_type': 'O+', 'date_of_birth': '1998-04-12'}
    )
    assert success is True

    user = User.query.filter(User.email == "security@lifeflow.org").first()
    assert user.password_hash != raw_pass
    assert user.password_hash.startswith(('scrypt:', 'pbkdf2:'))
    assert user.check_password(raw_pass) is True
    assert user.check_password("WrongPassword") is False


def test_duplicate_email_registration_rejected(db_session):
    register_user("User One", "dupe@lifeflow.org", "pass123", "donor",
                  {'blood_type': 'A+', 'date_of_birth': '2000-01-01'})

    success, msg, data = register_user("User Two", "dupe@lifeflow.org", "pass456", "donor",
                                       {'blood_type': 'B+', 'date_of_birth': '2001-01-01'})
    assert success is False
    assert "already exists" in msg


def test_short_password_rejected(db_session):
    success, msg, data = register_user("User", "short@lifeflow.org", "12345", "donor",
                                       {'blood_type': 'A+', 'date_of_birth': '2000-01-01'})
    assert success is False
    assert "at least 6 characters" in msg


def test_role_gated_route_protection(client, db_session, eligible_donor):
    """Asserts donor cannot access admin routes."""
    # Login as donor via API
    login_resp = client.post('/api/auth/login', json={
        'email': eligible_donor.user.email,
        'password': 'donor_pass123'
    })
    assert login_resp.status_code == 200

    # Donor attempting to access admin queue API should receive 403 Forbidden
    admin_api_resp = client.get('/api/admin/requests')
    assert admin_api_resp.status_code == 403
    assert "Access forbidden" in admin_api_resp.get_json()['error']


def test_unauthenticated_api_access_rejected(client, db_session):
    """Asserts unauthenticated requests receive 401."""
    resp = client.get('/api/admin/requests')
    assert resp.status_code == 401
    assert "Authentication required" in resp.get_json()['error']
