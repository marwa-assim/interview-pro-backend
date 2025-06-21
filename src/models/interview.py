from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

# Import db from user.py to maintain consistency
from src.models.user import db

class MockInterview(db.Model):
    __tablename__ = 'mock_interviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    major = db.Column(db.String(255), nullable=False)
    language = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='pending')
    report_url = db.Column(db.String(255))
    overall_score = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('InterviewQuestion', backref='interview', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'major': self.major,
            'language': self.language,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'report_url': self.report_url,
            'overall_score': float(self.overall_score) if self.overall_score else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class InterviewQuestion(db.Model):
    __tablename__ = 'interview_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('mock_interviews.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_language = db.Column(db.String(10), nullable=False)
    ai_generated = db.Column(db.Boolean, default=True)
    order_in_interview = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    responses = db.relationship('InterviewResponse', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'interview_id': self.interview_id,
            'question_text': self.question_text,
            'question_language': self.question_language,
            'ai_generated': self.ai_generated,
            'order_in_interview': self.order_in_interview,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class InterviewResponse(db.Model):
    __tablename__ = 'interview_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('interview_questions.id'), nullable=False)
    user_response_audio_url = db.Column(db.String(255))
    user_response_text = db.Column(db.Text)
    ai_feedback_text = db.Column(db.Text)
    sentiment_score = db.Column(db.Numeric(5, 2))
    clarity_score = db.Column(db.Numeric(5, 2))
    relevance_score = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'user_response_audio_url': self.user_response_audio_url,
            'user_response_text': self.user_response_text,
            'ai_feedback_text': self.ai_feedback_text,
            'sentiment_score': float(self.sentiment_score) if self.sentiment_score else None,
            'clarity_score': float(self.clarity_score) if self.clarity_score else None,
            'relevance_score': float(self.relevance_score) if self.relevance_score else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

