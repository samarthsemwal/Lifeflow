from datetime import datetime, date
from app.extensions import db

BLOOD_TYPES = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')

class Donor(db.Model):
    __tablename__ = 'donors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    blood_type = db.Column(db.Enum(*BLOOD_TYPES, name='blood_types'), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=False)
    last_donation_date = db.Column(db.Date, nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='donor_profile')
    donations = db.relationship('Donation', back_populates='donor', cascade='all, delete-orphan',
                                order_by='Donation.donated_at.desc()')

    @property
    def age(self) -> int:
        """Computes donor age in years accurately."""
        if not self.date_of_birth:
            return 0
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else None,
            'email': self.user.email if self.user else None,
            'blood_type': self.blood_type,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'last_donation_date': self.last_donation_date.isoformat() if self.last_donation_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Donor id={self.id} user_id={self.user_id} blood_type='{self.blood_type}'>"
