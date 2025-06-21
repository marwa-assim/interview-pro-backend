from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.subscription import (
    SubscriptionPlan, UserSubscription, DiscountVoucher, 
    VoucherUse, PaymentTransaction
)
from src.services.payment_service import PaymentService
from datetime import datetime, timedelta
import json

subscription_bp = Blueprint('subscription', __name__)

# Initialize payment service
payment_service = PaymentService()

@subscription_bp.route('/plans', methods=['GET'])
def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        language = request.args.get('language', 'en')
        plans = payment_service.get_subscription_plans(language)
        
        return jsonify({
            'plans': plans,
            'currency': 'USD'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_subscription():
    """Get user's current subscription"""
    try:
        user_id = get_jwt_identity()
        subscription = payment_service.get_user_subscription(user_id)
        
        if subscription:
            return jsonify({
                'subscription': subscription.to_dict(),
                'plan': subscription.plan.to_dict() if subscription.plan else None
            }), 200
        else:
            return jsonify({
                'subscription': None,
                'message': 'No active subscription'
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create a new subscription"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['plan_id', 'billing_cycle']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        plan_id = data['plan_id']
        billing_cycle = data['billing_cycle']
        voucher_code = data.get('voucher_code')
        
        # Validate billing cycle
        if billing_cycle not in ['monthly', 'yearly']:
            return jsonify({'error': 'Invalid billing cycle'}), 400
        
        # Check if user already has an active subscription
        existing_subscription = payment_service.get_user_subscription(user_id)
        if existing_subscription and existing_subscription.is_active():
            return jsonify({
                'error': 'User already has an active subscription',
                'current_subscription': existing_subscription.to_dict()
            }), 400
        
        # Create subscription
        result = payment_service.create_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            voucher_code=voucher_code
        )
        
        if result['success']:
            return jsonify({
                'message': 'Subscription created successfully',
                'subscription_id': result['subscription_id'],
                'client_secret': result.get('client_secret'),
                'payment_intent_id': result.get('payment_intent_id')
            }), 201
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription():
    """Cancel user's subscription"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        immediate = data.get('immediate', False)
        
        result = payment_service.cancel_subscription(user_id, immediate)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'immediate': result['immediate']
            }), 200
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/usage', methods=['GET'])
@jwt_required()
def get_usage_stats():
    """Get user's current usage statistics"""
    try:
        user_id = get_jwt_identity()
        subscription = payment_service.get_user_subscription(user_id)
        
        if not subscription:
            return jsonify({'error': 'No active subscription found'}), 404
        
        plan = subscription.plan
        usage_stats = {
            'current_plan': plan.to_dict() if plan else None,
            'usage': {
                'interviews_used_this_month': subscription.interviews_used_this_month,
                'cvs_created': subscription.cvs_created,
                'business_cards_created': subscription.business_cards_created,
                'usage_reset_date': subscription.usage_reset_date.isoformat() if subscription.usage_reset_date else None
            },
            'limits': {
                'max_interviews_per_month': plan.max_interviews_per_month if plan else 0,
                'max_cvs': plan.max_cvs if plan else 0,
                'max_business_cards': plan.max_business_cards if plan else 0
            },
            'features': {
                'ai_feedback': subscription.can_use_feature('ai_feedback'),
                'advanced_analytics': subscription.can_use_feature('advanced_analytics'),
                'priority_support': subscription.can_use_feature('priority_support'),
                'custom_branding': subscription.can_use_feature('custom_branding')
            }
        }
        
        return jsonify(usage_stats), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/check-feature', methods=['POST'])
@jwt_required()
def check_feature_access():
    """Check if user can access a specific feature"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        feature_type = data.get('feature_type')
        if not feature_type:
            return jsonify({'error': 'feature_type is required'}), 400
        
        subscription = payment_service.get_user_subscription(user_id)
        
        if not subscription:
            return jsonify({
                'can_use': False,
                'reason': 'No active subscription'
            }), 200
        
        can_use = subscription.can_use_feature(feature_type)
        
        return jsonify({
            'can_use': can_use,
            'feature_type': feature_type,
            'current_plan': subscription.plan_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/increment-usage', methods=['POST'])
@jwt_required()
def increment_usage():
    """Increment usage counter for a feature"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        feature_type = data.get('feature_type')
        if not feature_type:
            return jsonify({'error': 'feature_type is required'}), 400
        
        subscription = payment_service.get_user_subscription(user_id)
        
        if not subscription:
            return jsonify({'error': 'No active subscription found'}), 404
        
        # Check if user can use the feature before incrementing
        if not subscription.can_use_feature(feature_type):
            return jsonify({
                'error': 'Feature usage limit reached or not available in current plan'
            }), 403
        
        # Increment usage
        subscription.increment_usage(feature_type)
        
        return jsonify({
            'message': 'Usage incremented successfully',
            'feature_type': feature_type,
            'new_usage': getattr(subscription, f'{feature_type}s_used_this_month' if feature_type == 'interview' 
                                else f'{feature_type}s_created', 0)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/vouchers/validate', methods=['POST'])
def validate_voucher():
    """Validate a voucher code"""
    try:
        data = request.get_json()
        voucher_code = data.get('voucher_code')
        plan_id = data.get('plan_id')
        
        if not voucher_code:
            return jsonify({'error': 'voucher_code is required'}), 400
        
        # Get user_id if authenticated
        user_id = None
        try:
            user_id = get_jwt_identity()
        except:
            pass  # Not authenticated, that's okay for validation
        
        result = payment_service.validate_voucher(voucher_code, user_id, plan_id)
        
        if result['success']:
            return jsonify({
                'valid': True,
                'voucher': result['voucher'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': result['error']
            }), 200  # Return 200 even for invalid vouchers
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_user_transactions():
    """Get user's payment transaction history"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        transactions = PaymentTransaction.query.filter_by(user_id=user_id)\
            .order_by(PaymentTransaction.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'transactions': [transaction.to_dict() for transaction in transactions.items],
            'total': transactions.total,
            'pages': transactions.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get('Stripe-Signature')
        
        if not sig_header:
            return jsonify({'error': 'Missing Stripe signature'}), 400
        
        result = payment_service.handle_stripe_webhook(payload, sig_header)
        
        if result['success']:
            return jsonify({'message': result['message']}), 200
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin routes for voucher management
@subscription_bp.route('/admin/vouchers', methods=['POST'])
@jwt_required()
def create_voucher():
    """Create a new discount voucher (Admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is admin (you should implement proper admin check)
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['code', 'discount_type', 'discount_value', 'valid_until', 'max_uses']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Parse valid_until date
        try:
            valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid valid_until date format'}), 400
        
        result = payment_service.create_voucher(
            code=data['code'],
            discount_type=data['discount_type'],
            discount_value=data['discount_value'],
            valid_until=valid_until,
            max_uses=data['max_uses'],
            applicable_plans=data.get('applicable_plans'),
            created_by=user_id
        )
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'voucher_id': result['voucher_id']
            }), 201
        else:
            return jsonify({'error': result['error']}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/admin/vouchers', methods=['GET'])
@jwt_required()
def list_vouchers():
    """List all vouchers (Admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is admin
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        vouchers = DiscountVoucher.query\
            .order_by(DiscountVoucher.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'vouchers': [voucher.to_dict() for voucher in vouchers.items],
            'total': vouchers.total,
            'pages': vouchers.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/admin/vouchers/<int:voucher_id>', methods=['PUT'])
@jwt_required()
def update_voucher():
    """Update a voucher (Admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is admin
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        voucher_id = request.view_args['voucher_id']
        data = request.get_json()
        
        voucher = DiscountVoucher.query.get(voucher_id)
        if not voucher:
            return jsonify({'error': 'Voucher not found'}), 404
        
        # Update voucher fields
        if 'is_active' in data:
            voucher.is_active = data['is_active']
        if 'max_uses' in data:
            voucher.max_uses = data['max_uses']
        if 'valid_until' in data:
            try:
                voucher.valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid valid_until date format'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Voucher updated successfully',
            'voucher': voucher.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/admin/analytics', methods=['GET'])
@jwt_required()
def get_subscription_analytics():
    """Get subscription analytics (Admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Check if user is admin
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        
        # Get subscription statistics
        total_subscriptions = UserSubscription.query.count()
        active_subscriptions = UserSubscription.query.filter_by(status='active').count()
        cancelled_subscriptions = UserSubscription.query.filter_by(status='cancelled').count()
        
        # Get plan distribution
        plan_stats = db.session.query(
            UserSubscription.plan_id,
            db.func.count(UserSubscription.id).label('count')
        ).filter_by(status='active').group_by(UserSubscription.plan_id).all()
        
        # Get revenue statistics (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_revenue = db.session.query(
            db.func.sum(PaymentTransaction.amount).label('total')
        ).filter(
            PaymentTransaction.status == 'completed',
            PaymentTransaction.created_at >= thirty_days_ago
        ).scalar() or 0
        
        # Get voucher usage statistics
        total_vouchers = DiscountVoucher.query.count()
        active_vouchers = DiscountVoucher.query.filter_by(is_active=True).count()
        voucher_uses = VoucherUse.query.count()
        
        analytics = {
            'subscriptions': {
                'total': total_subscriptions,
                'active': active_subscriptions,
                'cancelled': cancelled_subscriptions,
                'plan_distribution': [{'plan_id': stat[0], 'count': stat[1]} for stat in plan_stats]
            },
            'revenue': {
                'last_30_days': float(recent_revenue),
                'currency': 'USD'
            },
            'vouchers': {
                'total': total_vouchers,
                'active': active_vouchers,
                'total_uses': voucher_uses
            }
        }
        
        return jsonify({'analytics': analytics}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

