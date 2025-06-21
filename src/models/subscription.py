from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from enum import Enum
import json

# Import db from user model to avoid multiple instances
from src.models.user import db

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.String(50), primary_key=True)  # e.g., 'basic', 'premium', 'enterprise'
    name = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    price_monthly = db.Column(db.Float, nullable=False)
    price_yearly = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Feature limits
    max_interviews_per_month = db.Column(db.Integer, default=0)  # 0 = unlimited
    max_cvs = db.Column(db.Integer, default=0)  # 0 = unlimited
    max_business_cards = db.Column(db.Integer, default=0)  # 0 = unlimited
    
    # Feature access
    ai_feedback = db.Column(db.Boolean, default=False)
    advanced_analytics = db.Column(db.Boolean, default=False)
    priority_support = db.Column(db.Boolean, default=False)
    custom_branding = db.Column(db.Boolean, default=False)
    
    # Stripe integration
    stripe_price_id_monthly = db.Column(db.String(100))
    stripe_price_id_yearly = db.Column(db.String(100))
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_ar': self.name_ar,
            'description': self.description,
            'description_ar': self.description_ar,
            'price_monthly': self.price_monthly,
            'price_yearly': self.price_yearly,
            'currency': self.currency,
            'features': {
                'max_interviews_per_month': self.max_interviews_per_month,
                'max_cvs': self.max_cvs,
                'max_business_cards': self.max_business_cards,
                'ai_feedback': self.ai_feedback,
                'advanced_analytics': self.advanced_analytics,
                'priority_support': self.priority_support,
                'custom_branding': self.custom_branding
            },
            'stripe_price_id_monthly': self.stripe_price_id_monthly,
            'stripe_price_id_yearly': self.stripe_price_id_yearly,
            'is_active': self.is_active
        }

class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.String(50), db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # Subscription details
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired, suspended
    billing_cycle = db.Column(db.String(10), default='monthly')  # monthly, yearly
    
    # Dates
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    next_billing_date = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Payment details
    stripe_subscription_id = db.Column(db.String(100))
    stripe_customer_id = db.Column(db.String(100))
    
    # Usage tracking
    interviews_used_this_month = db.Column(db.Integer, default=0)
    cvs_created = db.Column(db.Integer, default=0)
    business_cards_created = db.Column(db.Integer, default=0)
    
    # Reset date for monthly limits
    usage_reset_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'status': self.status,
            'billing_cycle': self.billing_cycle,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'usage': {
                'interviews_used_this_month': self.interviews_used_this_month,
                'cvs_created': self.cvs_created,
                'business_cards_created': self.business_cards_created,
                'usage_reset_date': self.usage_reset_date.isoformat() if self.usage_reset_date else None
            },
            'stripe_subscription_id': self.stripe_subscription_id,
            'stripe_customer_id': self.stripe_customer_id
        }
    
    def is_active(self):
        """Check if subscription is currently active"""
        return (self.status == 'active' and 
                (self.end_date is None or self.end_date > datetime.utcnow()))
    
    def can_use_feature(self, feature_type):
        """Check if user can use a specific feature based on their plan limits"""
        if not self.is_active():
            return False
        
        plan = self.plan
        if not plan:
            return False
        
        # Reset monthly usage if needed
        if self.usage_reset_date and self.usage_reset_date < datetime.utcnow().replace(day=1):
            self.interviews_used_this_month = 0
            self.usage_reset_date = datetime.utcnow().replace(day=1)
            db.session.commit()
        
        if feature_type == 'interview':
            if plan.max_interviews_per_month == 0:  # Unlimited
                return True
            return self.interviews_used_this_month < plan.max_interviews_per_month
        
        elif feature_type == 'cv':
            if plan.max_cvs == 0:  # Unlimited
                return True
            return self.cvs_created < plan.max_cvs
        
        elif feature_type == 'business_card':
            if plan.max_business_cards == 0:  # Unlimited
                return True
            return self.business_cards_created < plan.max_business_cards
        
        elif feature_type == 'ai_feedback':
            return plan.ai_feedback
        
        elif feature_type == 'advanced_analytics':
            return plan.advanced_analytics
        
        elif feature_type == 'priority_support':
            return plan.priority_support
        
        elif feature_type == 'custom_branding':
            return plan.custom_branding
        
        return False
    
    def increment_usage(self, feature_type):
        """Increment usage counter for a feature"""
        if feature_type == 'interview':
            self.interviews_used_this_month += 1
        elif feature_type == 'cv':
            self.cvs_created += 1
        elif feature_type == 'business_card':
            self.business_cards_created += 1
        
        db.session.commit()

class DiscountVoucher(db.Model):
    __tablename__ = 'discount_vouchers'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    # Discount details
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed_amount
    discount_value = db.Column(db.Float, nullable=False)  # percentage (0-100) or fixed amount
    currency = db.Column(db.String(3), default='USD')
    
    # Usage limits
    max_uses = db.Column(db.Integer, default=1)  # Maximum number of times this voucher can be used
    used_count = db.Column(db.Integer, default=0)
    single_use_per_user = db.Column(db.Boolean, default=True)  # Can each user use this voucher only once?
    
    # Validity period
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=False)
    
    # Applicable plans (JSON array of plan IDs, empty means all plans)
    applicable_plans = db.Column(db.Text)  # JSON array
    
    # Admin details
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    voucher_uses = db.relationship('VoucherUse', backref='voucher', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'currency': self.currency,
            'max_uses': self.max_uses,
            'used_count': self.used_count,
            'single_use_per_user': self.single_use_per_user,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'applicable_plans': json.loads(self.applicable_plans) if self.applicable_plans else [],
            'is_active': self.is_active,
            'created_by': self.created_by
        }
    
    def is_valid(self, user_id=None, plan_id=None):
        """Check if voucher is valid for use"""
        now = datetime.utcnow()
        
        # Basic validity checks
        if not self.is_active:
            return False, "Voucher is not active"
        
        if self.valid_from and self.valid_from > now:
            return False, "Voucher is not yet valid"
        
        if self.valid_until and self.valid_until < now:
            return False, "Voucher has expired"
        
        if self.used_count >= self.max_uses:
            return False, "Voucher usage limit reached"
        
        # Plan-specific check
        if plan_id and self.applicable_plans:
            applicable_plans = json.loads(self.applicable_plans)
            if applicable_plans and plan_id not in applicable_plans:
                return False, "Voucher not applicable to this plan"
        
        # User-specific check
        if user_id and self.single_use_per_user:
            existing_use = VoucherUse.query.filter_by(
                voucher_id=self.id,
                user_id=user_id
            ).first()
            if existing_use:
                return False, "Voucher already used by this user"
        
        return True, "Voucher is valid"
    
    def calculate_discount(self, original_amount):
        """Calculate discount amount"""
        if self.discount_type == 'percentage':
            discount_amount = original_amount * (self.discount_value / 100)
        else:  # fixed_amount
            discount_amount = min(self.discount_value, original_amount)
        
        return round(discount_amount, 2)

class VoucherUse(db.Model):
    __tablename__ = 'voucher_uses'
    
    id = db.Column(db.Integer, primary_key=True)
    voucher_id = db.Column(db.Integer, db.ForeignKey('discount_vouchers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'))
    
    # Usage details
    original_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, nullable=False)
    final_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Payment details
    stripe_payment_intent_id = db.Column(db.String(100))
    
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'voucher_id': self.voucher_id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'original_amount': self.original_amount,
            'discount_amount': self.discount_amount,
            'final_amount': self.final_amount,
            'currency': self.currency,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'used_at': self.used_at.isoformat() if self.used_at else None
        }

class PaymentTransaction(db.Model):
    __tablename__ = 'payment_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'))
    voucher_use_id = db.Column(db.Integer, db.ForeignKey('voucher_uses.id'))
    
    # Transaction details
    transaction_type = db.Column(db.String(20), default='subscription')  # subscription, one_time
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, refunded
    
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Stripe details
    stripe_payment_intent_id = db.Column(db.String(100))
    stripe_charge_id = db.Column(db.String(100))
    stripe_invoice_id = db.Column(db.String(100))
    
    # Metadata
    description = db.Column(db.String(200))
    transaction_metadata = db.Column(db.Text)  # JSON for additional data
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subscription_id': self.subscription_id,
            'voucher_use_id': self.voucher_use_id,
            'transaction_type': self.transaction_type,
            'status': self.status,
            'amount': self.amount,
            'currency': self.currency,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'stripe_charge_id': self.stripe_charge_id,
            'stripe_invoice_id': self.stripe_invoice_id,
            'description': self.description,
            'metadata': json.loads(self.transaction_metadata) if self.transaction_metadata else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

