"""
Database Seeder for LifeFlow.
Populates realistic test data across all 3 roles, inventory, and prioritized queue.
"""
from datetime import datetime, date, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.donor import Donor
from app.models.requester import Requester
from app.models.inventory import BloodUnit, Donation
from app.models.request import BloodRequest, RequestFulfillment

app = create_app('development')

def seed_database():
    with app.app_context():
        print("🌱 Seeding LifeFlow MySQL Database...")

        # Clear existing data in reverse order of foreign keys
        RequestFulfillment.query.delete()
        BloodRequest.query.delete()
        Donation.query.delete()
        BloodUnit.query.delete()
        Donor.query.delete()
        Requester.query.delete()
        User.query.delete()
        db.session.commit()

        # 1. Create Users
        admin_user = User(name="Administrator Jane", email="admin@lifeflow.org", role="admin")
        admin_user.set_password("admin123")

        donor_user_1 = User(name="John Voluntary Donor", email="donor@lifeflow.org", role="donor")
        donor_user_1.set_password("donor123")

        donor_user_2 = User(name="Sarah Recent Donor", email="recent@lifeflow.org", role="donor")
        donor_user_2.set_password("donor123")

        requester_user_1 = User(name="Dr. Marcus Bell", email="hospital@lifeflow.org", role="requester")
        requester_user_1.set_password("request123")

        requester_user_2 = User(name="Dr. Elena Ramos", email="trauma@lifeflow.org", role="requester")
        requester_user_2.set_password("request123")

        db.session.add_all([admin_user, donor_user_1, donor_user_2, requester_user_1, requester_user_2])
        db.session.commit()

        # 2. Create Profiles
        today = date.today()

        # Donor 1: 30 years old, last donation 120 days ago (Fully Eligible)
        donor_1 = Donor(
            user_id=donor_user_1.id,
            blood_type="O-",
            date_of_birth=today - timedelta(days=365 * 30),
            last_donation_date=today - timedelta(days=120)
        )

        # Donor 2: 24 years old, last donation 25 days ago (Ineligible under 90-day rule)
        donor_2 = Donor(
            user_id=donor_user_2.id,
            blood_type="A+",
            date_of_birth=today - timedelta(days=365 * 24),
            last_donation_date=today - timedelta(days=25)
        )

        requester_1 = Requester(
            user_id=requester_user_1.id,
            organization_name="City General Hospital (Emergency Wing)",
            contact_phone="+1-555-0199"
        )

        requester_2 = Requester(
            user_id=requester_user_2.id,
            organization_name="St. Jude Trauma ICU",
            contact_phone="+1-555-0144"
        )

        db.session.add_all([donor_1, donor_2, requester_1, requester_2])
        db.session.commit()

        # 3. Create Inventory (Blood Units)
        now = datetime.utcnow()
        blood_types_stock = {
            'O-': 6,   # Universal donor
            'O+': 8,
            'A+': 5,
            'A-': 3,
            'B+': 4,
            'B-': 2,   # Low stock
            'AB+': 4,  # Universal recipient
            'AB-': 1   # Low stock
        }

        created_units = []
        for b_type, count in blood_types_stock.items():
            for i in range(count):
                # Stagger collection dates and viable expiry
                collected = now - timedelta(days=5 * (i + 1))
                # 1 unit per group expiring within 4 days to demonstrate FEFO
                if i == 0:
                    expires = now + timedelta(days=4)
                else:
                    expires = collected + timedelta(days=42)

                unit = BloodUnit(
                    blood_type=b_type,
                    collected_at=collected,
                    expires_at=expires,
                    status='available'
                )
                db.session.add(unit)
                created_units.append(unit)

        db.session.commit()

        # 4. Create Sample Past Donations
        past_donation_1 = Donation(
            donor_id=donor_1.id,
            unit_id=created_units[0].id,
            donated_at=now - timedelta(days=120),
            notes="Successful whole blood collection (450ml). Donor felt great."
        )
        past_donation_2 = Donation(
            donor_id=donor_2.id,
            unit_id=created_units[1].id,
            donated_at=now - timedelta(days=25),
            notes="Quarterly donation drive at university."
        )
        db.session.add_all([past_donation_1, past_donation_2])
        db.session.commit()

        # 5. Create Sample Blood Requests demonstrating Urgency Prioritization
        # Routine request submitted 3 hours ago
        req_routine = BloodRequest(
            requester_id=requester_1.id,
            blood_type_requested="A+",
            units_requested=2,
            urgency="routine",
            status="pending",
            requested_at=now - timedelta(hours=3)
        )

        # Urgent request submitted 2 hours ago
        req_urgent = BloodRequest(
            requester_id=requester_1.id,
            blood_type_requested="B+",
            units_requested=2,
            urgency="urgent",
            status="pending",
            requested_at=now - timedelta(hours=2)
        )

        # Critical request submitted 30 minutes ago (Must jump to Rank #1 ahead of older routine/urgent)
        req_critical = BloodRequest(
            requester_id=requester_2.id,
            blood_type_requested="O-",
            units_requested=2,
            urgency="critical",
            status="pending",
            requested_at=now - timedelta(minutes=30)
        )

        # Already approved request
        req_approved = BloodRequest(
            requester_id=requester_1.id,
            blood_type_requested="O+",
            units_requested=1,
            urgency="urgent",
            status="approved",
            requested_at=now - timedelta(days=1),
            resolved_at=now - timedelta(hours=20),
            resolved_by=admin_user.id
        )

        db.session.add_all([req_routine, req_urgent, req_critical, req_approved])
        db.session.commit()

        print("✅ Database successfully seeded!")
        print("--------------------------------------------------")
        print("Sample Accounts Created:")
        print("  Admin:     admin@lifeflow.org     / admin123")
        print("  Donor:     donor@lifeflow.org     / donor123 (Eligible, O-)")
        print("  Donor 2:   recent@lifeflow.org    / donor123 (Ineligible, last donated 25d ago)")
        print("  Requester: hospital@lifeflow.org  / request123 (City General Hospital)")
        print("  Requester: trauma@lifeflow.org    / request123 (St. Jude Trauma ICU)")
        print(f"Total Blood Units Created: {len(created_units)}")
        print("Pending Queue: 3 requests (Critical, Urgent, Routine)")
        print("--------------------------------------------------")

if __name__ == '__main__':
    seed_database()
