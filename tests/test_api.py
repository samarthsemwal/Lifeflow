from datetime import datetime, timedelta
from app.models.inventory import BloodUnit

def test_api_live_inventory_contract(client, db_session):
    resp = client.get('/api/inventory')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'total_units' in data
    assert 'inventory' in data
    # Ensure all 8 blood types are present
    for bt in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
        assert bt in data['inventory']


def test_api_requester_submit_and_view_requests(client, db_session, requester_user):
    # Login as requester
    client.post('/api/auth/login', json={
        'email': requester_user.user.email,
        'password': 'request_pass123'
    })

    # Submit valid blood request
    post_resp = client.post('/api/requests', json={
        'blood_type_requested': 'O+',
        'units_requested': 2,
        'urgency': 'urgent'
    })
    assert post_resp.status_code == 201
    post_data = post_resp.get_json()
    assert post_data['success'] is True
    assert post_data['request']['blood_type_requested'] == 'O+'
    assert post_data['request']['urgency'] == 'urgent'

    # View my requests
    get_resp = client.get('/api/requests/me')
    assert get_resp.status_code == 200
    get_data = get_resp.get_json()
    assert len(get_data['requests']) == 1


def test_api_invalid_request_quantities_rejected(client, db_session, requester_user):
    client.post('/api/auth/login', json={
        'email': requester_user.user.email,
        'password': 'request_pass123'
    })

    # Non-positive quantity
    resp = client.post('/api/requests', json={
        'blood_type_requested': 'O+',
        'units_requested': 0,
        'urgency': 'routine'
    })
    assert resp.status_code == 400
    assert "positive integer" in resp.get_json()['error']


def test_api_admin_dashboard_metrics(client, db_session, admin_user):
    client.post('/api/auth/login', json={
        'email': admin_user.email,
        'password': 'admin_pass123'
    })

    resp = client.get('/api/admin/dashboard')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    metrics = data['metrics']
    assert 'total_available_units' in metrics
    assert 'pending_requests' in metrics
    assert 'total_registered_donors' in metrics
