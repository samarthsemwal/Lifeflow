from datetime import datetime, timedelta
from app.extensions import db
from app.models.donor import BLOOD_TYPES

UNIT_STATUSES = ('available', 'reserved', 'used', 'expired')

class BloodUnit(db.Model):
    __tablename__ = 'blood_units'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(
        db.Integer,
        db.ForeignKey('donations.id', use_alter=True, name='fk_blood_units_donation', ondelete='SET NULL'),
        nullable=True
    )
    blood_type = db.Column(db.Enum(*BLOOD_TYPES, name='blood_types'), nullable=False)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(*UNIT_STATUSES, name='unit_statuses'), default='available', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index('idx_blood_units_status_type', 'status', 'blood_type'),
        db.Index('idx_blood_units_expiry', 'expires_at'),
    )

    # Relationships
    donation = db.relationship('Donation', foreign_keys=[donation_id], uselist=False)
    fulfillment = db.relationship('RequestFulfillment', back_populates='unit', uselist=False)

    @classmethod
    def calculate_expiry(cls, collection_date: datetime = None) -> datetime:
        """Standard whole blood shelf life is 42 days."""
        base = collection_date or datetime.utcnow()
        return base + timedelta(days=42)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'blood_type': self.blood_type,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'is_expired': self.is_expired,
            'days_until_expiry': max(0, (self.expires_at - datetime.utcnow()).days) if self.expires_at else 0
        }

    def __repr__(self):
        return f"<BloodUnit id={self.id} type='{self.blood_type}' status='{self.status}'>"


class Donation(db.Model):
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('donors.id', ondelete='CASCADE'), nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('blood_units.id', ondelete='SET NULL'), nullable=True)
    donated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = db.Column(db.String(255), nullable=True)

    # Relationships
    donor = db.relationship('Donor', back_populates='donations')
    unit = db.relationship('BloodUnit', foreign_keys=[unit_id], uselist=False)

    def to_dict(self):
        return {
            'id': self.id,
            'donor_id': self.donor_id,
            'donor_name': self.donor.user.name if self.donor and self.donor.user else None,
            'blood_type': self.donor.blood_type if self.donor else None,
            'unit_id': self.unit_id,
            'donated_at': self.donated_at.isoformat() if self.donated_at else None,
            'notes': self.notes
        }

    def __repr__(self):
        return f"<Donation id={self.id} donor_id={self.donor_id} at='{self.donated_at}'>"
