from datetime import datetime
from app.extensions import db

class Requester(db.Model):
    __tablename__ = 'requesters'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    organization_name = db.Column(db.String(150), nullable=False)
    contact_phone = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='requester_profile')
    requests = db.relationship('BloodRequest', back_populates='requester', cascade='all, delete-orphan',
                               order_by='BloodRequest.requested_at.desc()')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'contact_name': self.user.name if self.user else None,
            'email': self.user.email if self.user else None,
            'organization_name': self.organization_name,
            'contact_phone': self.contact_phone,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Requester id={self.id} org='{self.organization_name}'>"
