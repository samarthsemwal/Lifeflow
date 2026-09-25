from datetime import datetime
from app.extensions import db
from app.models.donor import BLOOD_TYPES

URGENCY_LEVELS = ('critical', 'urgent', 'routine')
REQUEST_STATUSES = ('pending', 'approved', 'rejected', 'fulfilled')

class BloodRequest(db.Model):
    __tablename__ = 'blood_requests'

    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('requesters.id', ondelete='CASCADE'), nullable=False)
    blood_type_requested = db.Column(db.Enum(*BLOOD_TYPES, name='blood_types'), nullable=False)
    units_requested = db.Column(db.Integer, nullable=False)
    urgency = db.Column(db.Enum(*URGENCY_LEVELS, name='urgency_levels'), default='routine', nullable=False)
    status = db.Column(db.Enum(*REQUEST_STATUSES, name='request_statuses'), default='pending', nullable=False)
    rejection_reason = db.Column(db.String(255), nullable=True)
    requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    __table_args__ = (
        db.Index('idx_requests_queue', 'status', 'urgency', 'requested_at'),
    )

    # Relationships
    requester = db.relationship('Requester', back_populates='requests')
    fulfillments = db.relationship('RequestFulfillment', back_populates='request', cascade='all, delete-orphan')
    resolver = db.relationship('User', foreign_keys=[resolved_by])

    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester_id,
            'organization_name': self.requester.organization_name if self.requester else None,
            'contact_phone': self.requester.contact_phone if self.requester else None,
            'blood_type_requested': self.blood_type_requested,
            'units_requested': self.units_requested,
            'urgency': self.urgency,
            'status': self.status,
            'rejection_reason': self.rejection_reason,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolver.name if self.resolver else None,
            'fulfilled_units': [f.unit_id for f in self.fulfillments]
        }

    def __repr__(self):
        return f"<BloodRequest id={self.id} type='{self.blood_type_requested}' units={self.units_requested} urgency='{self.urgency}'>"


class RequestFulfillment(db.Model):
    __tablename__ = 'request_fulfillments'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('blood_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('blood_units.id', ondelete='RESTRICT'), unique=True, nullable=False)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    request = db.relationship('BloodRequest', back_populates='fulfillments')
    unit = db.relationship('BloodUnit', back_populates='fulfillment')

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'unit_id': self.unit_id,
            'blood_type': self.unit.blood_type if self.unit else None,
            'allocated_at': self.allocated_at.isoformat() if self.allocated_at else None
        }

    def __repr__(self):
        return f"<RequestFulfillment request_id={self.request_id} unit_id={self.unit_id}>"
