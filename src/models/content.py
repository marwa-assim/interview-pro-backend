from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

# Import db from user.py to maintain consistency
from src.models.user import db

class CVTemplate(db.Model):
    __tablename__ = 'cv_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    preview_image_url = db.Column(db.String(255))
    style_description = db.Column(db.Text)
    is_premium = db.Column(db.Boolean, default=False)
    template_data = db.Column(db.Text)  # JSON structure for template layout
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cvs = db.relationship('CV', backref='template', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'preview_image_url': self.preview_image_url,
            'style_description': self.style_description,
            'is_premium': self.is_premium,
            'template_data': json.loads(self.template_data) if self.template_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CV(db.Model):
    __tablename__ = 'cvs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('cv_templates.id'), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    data_json = db.Column(db.Text, nullable=False)  # JSON blob of all CV data
    generated_pdf_url = db.Column(db.String(255))
    is_ats_compliant = db.Column(db.Boolean)
    title = db.Column(db.String(255))  # User-defined title for the CV
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'language': self.language,
            'data_json': json.loads(self.data_json) if self.data_json else None,
            'generated_pdf_url': self.generated_pdf_url,
            'is_ats_compliant': self.is_ats_compliant,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BusinessCardTemplate(db.Model):
    __tablename__ = 'business_card_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    preview_image_url = db.Column(db.String(255))
    style_description = db.Column(db.Text)
    is_premium = db.Column(db.Boolean, default=False)
    template_data = db.Column(db.Text)  # JSON structure for template layout
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_cards = db.relationship('DigitalBusinessCard', backref='template', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'preview_image_url': self.preview_image_url,
            'style_description': self.style_description,
            'is_premium': self.is_premium,
            'template_data': json.loads(self.template_data) if self.template_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DigitalBusinessCard(db.Model):
    __tablename__ = 'digital_business_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('business_card_templates.id'), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    data_json = db.Column(db.Text, nullable=False)  # JSON blob of all business card data
    qr_code_image_url = db.Column(db.String(255))
    digital_card_url = db.Column(db.String(255))
    title = db.Column(db.String(255))  # User-defined title for the business card
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'language': self.language,
            'data_json': json.loads(self.data_json) if self.data_json else None,
            'qr_code_image_url': self.qr_code_image_url,
            'digital_card_url': self.digital_card_url,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AdminReport(db.Model):
    __tablename__ = 'admin_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    report_type = db.Column(db.String(100), nullable=False)
    generated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    generation_time = db.Column(db.DateTime, nullable=False)
    report_data_json = db.Column(db.Text)  # JSON blob of report data
    report_file_url = db.Column(db.String(255))  # URL to larger report file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'report_type': self.report_type,
            'generated_by_user_id': self.generated_by_user_id,
            'generation_time': self.generation_time.isoformat() if self.generation_time else None,
            'report_data_json': json.loads(self.report_data_json) if self.report_data_json else None,
            'report_file_url': self.report_file_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

