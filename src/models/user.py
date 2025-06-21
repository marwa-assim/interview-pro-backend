from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    full_name = db.Column(db.String(255))  # Computed field for convenience
    language_preference = db.Column(db.String(10), default='en')
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    profile_picture_url = db.Column(db.String(255))
    major = db.Column(db.String(255))
    
    # Stripe integration
    stripe_customer_id = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', backref='user', lazy=True)
    mock_interviews = db.relationship('MockInterview', backref='user', lazy=True)
    cvs = db.relationship('CV', backref='user', lazy=True)
    business_cards = db.relationship('DigitalBusinessCard', backref='user', lazy=True)

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check if the provided password matches the user's password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'language_preference': self.language_preference,
            'role': self.role,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'profile_picture_url': self.profile_picture_url,
            'major': self.major,
            'stripe_customer_id': self.stripe_customer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
