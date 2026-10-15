import os
import pytest
from datetime import date, datetime, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.donor import Donor
from app.models.requester import Requester
from app.models.inventory import BloodUnit, Donation
from app.models.request import BloodRequest, RequestFulfillment

@pytest.fixture(scope='session')
def app():
    """Create and configure a clean Flask app for testing against test_lifeflow database."""
    test_db_url = os.getenv(
        'TEST_DATABASE_URL',
        'mysql+pymysql://lifeflow_user:lifeflow_pass@localhost:3306/test_lifeflow'
    )

    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_db_url,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })

    with app.app_context():
        db.create_all()
        yield app
        try:
            db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
            db.drop_all()
            db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.session.commit()
        except Exception:
            pass


@pytest.fixture(scope='function')
def db_session(app):
    """Provides a clean database state for each test function."""
    with app.app_context():
        # Clear all tables in reverse FK order
        RequestFulfillment.query.delete()
        BloodRequest.query.delete()
        Donation.query.delete()
        BloodUnit.query.delete()
        Donor.query.delete()
        Requester.query.delete()
        User.query.delete()
        db.session.commit()

        yield db.session

        db.session.rollback()
        RequestFulfillment.query.delete()
        BloodRequest.query.delete()
        Donation.query.delete()
        BloodUnit.query.delete()
        Donor.query.delete()
        Requester.query.delete()
        User.query.delete()
        db.session.commit()


@pytest.fixture
def client(app, db_session):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def admin_user(db_session):
    """Creates a persistent admin user."""
    admin = User(name="Admin User", email="admin.test@lifeflow.org", role="admin")
    admin.set_password("admin_pass123")
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def eligible_donor(db_session):
    """Creates an eligible donor (Age 25, last donation 100 days ago, O-)."""
    user = User(name="Eligible Donor", email="eligible.donor@lifeflow.org", role="donor")
    user.set_password("donor_pass123")
    db_session.add(user)
    db_session.flush()

    today = date.today()
    donor = Donor(
        user_id=user.id,
        blood_type="O-",
        date_of_birth=today - timedelta(days=365 * 25),
        last_donation_date=today - timedelta(days=100)
    )
    db_session.add(donor)
    db_session.commit()
    return donor


@pytest.fixture
def requester_user(db_session):
    """Creates a verified hospital requester."""
    user = User(name="Hospital Staff", email="hospital.test@lifeflow.org", role="requester")
    user.set_password("request_pass123")
    db_session.add(user)
    db_session.flush()

    requester = Requester(
        user_id=user.id,
        organization_name="Emergency Hospital Alpha",
        contact_phone="+1-555-0100"
    )
    db_session.add(requester)
    db_session.commit()
    return requester
