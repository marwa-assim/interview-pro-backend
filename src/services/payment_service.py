import stripe
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from src.models.subscription import (
    SubscriptionPlan, UserSubscription, DiscountVoucher, 
    VoucherUse, PaymentTransaction, db
)
import json

class PaymentService:
    def __init__(self):
        # Initialize Stripe with API key (in production, use environment variable)
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')  # Replace with actual test key
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')
    
    def create_subscription_plans(self):
        """Create default subscription plans"""
        plans_data = [
            {
                'id': 'free',
                'name': 'Free Plan',
                'name_ar': 'الخطة المجانية',
                'description': 'Basic features for getting started',
                'description_ar': 'الميزات الأساسية للبدء',
                'price_monthly': 0.0,
                'price_yearly': 0.0,
                'max_interviews_per_month': 3,
                'max_cvs': 1,
                'max_business_cards': 1,
                'ai_feedback': False,
                'advanced_analytics': False,
                'priority_support': False,
                'custom_branding': False
            },
            {
                'id': 'basic',
                'name': 'Basic Plan',
                'name_ar': 'الخطة الأساسية',
                'description': 'Perfect for individual job seekers',
                'description_ar': 'مثالية للباحثين عن عمل الأفراد',
                'price_monthly': 9.99,
                'price_yearly': 99.99,
                'max_interviews_per_month': 20,
                'max_cvs': 5,
                'max_business_cards': 3,
                'ai_feedback': True,
                'advanced_analytics': False,
                'priority_support': False,
                'custom_branding': False
            },
            {
                'id': 'premium',
                'name': 'Premium Plan',
                'name_ar': 'الخطة المميزة',
                'description': 'Advanced features for serious professionals',
                'description_ar': 'ميزات متقدمة للمهنيين الجادين',
                'price_monthly': 19.99,
                'price_yearly': 199.99,
                'max_interviews_per_month': 0,  # Unlimited
                'max_cvs': 0,  # Unlimited
                'max_business_cards': 0,  # Unlimited
                'ai_feedback': True,
                'advanced_analytics': True,
                'priority_support': True,
                'custom_branding': False
            },
            {
                'id': 'enterprise',
                'name': 'Enterprise Plan',
                'name_ar': 'خطة المؤسسات',
                'description': 'Complete solution for organizations',
                'description_ar': 'حل شامل للمؤسسات',
                'price_monthly': 49.99,
                'price_yearly': 499.99,
                'max_interviews_per_month': 0,  # Unlimited
                'max_cvs': 0,  # Unlimited
                'max_business_cards': 0,  # Unlimited
                'ai_feedback': True,
                'advanced_analytics': True,
                'priority_support': True,
                'custom_branding': True
            }
        ]
        
        for plan_data in plans_data:
            existing_plan = SubscriptionPlan.query.filter_by(id=plan_data['id']).first()
            if not existing_plan:
                plan = SubscriptionPlan(**plan_data)
                db.session.add(plan)
        
        db.session.commit()
        return True
    
    def create_stripe_products_and_prices(self):
        """Create Stripe products and prices for subscription plans"""
        plans = SubscriptionPlan.query.filter(SubscriptionPlan.price_monthly > 0).all()
        
        for plan in plans:
            try:
                # Create Stripe product
                product = stripe.Product.create(
                    name=plan.name,
                    description=plan.description,
                    metadata={'plan_id': plan.id}
                )
                
                # Create monthly price
                monthly_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan.price_monthly * 100),  # Convert to cents
                    currency=plan.currency.lower(),
                    recurring={'interval': 'month'},
                    metadata={'plan_id': plan.id, 'billing_cycle': 'monthly'}
                )
                
                # Create yearly price
                yearly_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan.price_yearly * 100),  # Convert to cents
                    currency=plan.currency.lower(),
                    recurring={'interval': 'year'},
                    metadata={'plan_id': plan.id, 'billing_cycle': 'yearly'}
                )
                
                # Update plan with Stripe price IDs
                plan.stripe_price_id_monthly = monthly_price.id
                plan.stripe_price_id_yearly = yearly_price.id
                
            except stripe.error.StripeError as e:
                print(f"Error creating Stripe product for plan {plan.id}: {str(e)}")
                continue
        
        db.session.commit()
        return True
    
    def create_customer(self, user_email: str, user_name: str, metadata: Dict = None) -> str:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=user_email,
                name=user_name,
                metadata=metadata or {}
            )
            return customer.id
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create Stripe customer: {str(e)}")
    
    def create_subscription(self, user_id: int, plan_id: str, billing_cycle: str = 'monthly', 
                          voucher_code: str = None) -> Dict[str, Any]:
        """Create a new subscription for a user"""
        try:
            # Get user and plan
            from src.models.user import User
            user = User.query.get(user_id)
            plan = SubscriptionPlan.query.get(plan_id)
            
            if not user or not plan:
                return {'success': False, 'error': 'User or plan not found'}
            
            # Handle free plan
            if plan.price_monthly == 0:
                return self._create_free_subscription(user_id, plan_id)
            
            # Get or create Stripe customer
            stripe_customer_id = user.stripe_customer_id
            if not stripe_customer_id:
                stripe_customer_id = self.create_customer(
                    user.email, 
                    user.full_name,
                    {'user_id': str(user_id)}
                )
                user.stripe_customer_id = stripe_customer_id
                db.session.commit()
            
            # Get Stripe price ID
            price_id = (plan.stripe_price_id_monthly if billing_cycle == 'monthly' 
                       else plan.stripe_price_id_yearly)
            
            if not price_id:
                return {'success': False, 'error': 'Stripe price not configured for this plan'}
            
            # Apply voucher if provided
            discount_coupon = None
            if voucher_code:
                voucher_result = self._apply_voucher(voucher_code, user_id, plan_id)
                if voucher_result['success']:
                    discount_coupon = voucher_result['stripe_coupon_id']
                else:
                    return {'success': False, 'error': voucher_result['error']}
            
            # Create Stripe subscription
            subscription_params = {
                'customer': stripe_customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'payment_settings': {'save_default_payment_method': 'on_subscription'},
                'expand': ['latest_invoice.payment_intent'],
                'metadata': {
                    'user_id': str(user_id),
                    'plan_id': plan_id,
                    'billing_cycle': billing_cycle
                }
            }
            
            if discount_coupon:
                subscription_params['coupon'] = discount_coupon
            
            stripe_subscription = stripe.Subscription.create(**subscription_params)
            
            # Create local subscription record
            end_date = None
            if billing_cycle == 'monthly':
                next_billing = datetime.utcnow() + timedelta(days=30)
            else:
                next_billing = datetime.utcnow() + timedelta(days=365)
            
            user_subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                status='pending',  # Will be updated when payment is confirmed
                billing_cycle=billing_cycle,
                end_date=end_date,
                next_billing_date=next_billing,
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=stripe_customer_id
            )
            
            db.session.add(user_subscription)
            db.session.commit()
            
            return {
                'success': True,
                'subscription_id': user_subscription.id,
                'stripe_subscription_id': stripe_subscription.id,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret,
                'payment_intent_id': stripe_subscription.latest_invoice.payment_intent.id
            }
            
        except stripe.error.StripeError as e:
            return {'success': False, 'error': f'Payment processing error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _create_free_subscription(self, user_id: int, plan_id: str) -> Dict[str, Any]:
        """Create a free subscription"""
        try:
            # Cancel any existing subscription
            existing = UserSubscription.query.filter_by(
                user_id=user_id, 
                status='active'
            ).first()
            
            if existing:
                existing.status = 'cancelled'
                existing.cancelled_at = datetime.utcnow()
            
            # Create free subscription
            user_subscription = UserSubscription(
                user_id=user_id,
                plan_id=plan_id,
                status='active',
                billing_cycle='monthly',
                end_date=None  # Free plan doesn't expire
            )
            
            db.session.add(user_subscription)
            db.session.commit()
            
            return {
                'success': True,
                'subscription_id': user_subscription.id,
                'message': 'Free subscription activated'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _apply_voucher(self, voucher_code: str, user_id: int, plan_id: str) -> Dict[str, Any]:
        """Apply a discount voucher"""
        try:
            voucher = DiscountVoucher.query.filter_by(code=voucher_code).first()
            if not voucher:
                return {'success': False, 'error': 'Invalid voucher code'}
            
            # Validate voucher
            is_valid, error_message = voucher.is_valid(user_id, plan_id)
            if not is_valid:
                return {'success': False, 'error': error_message}
            
            # Create Stripe coupon for this voucher use
            coupon_id = f"voucher_{voucher.id}_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            if voucher.discount_type == 'percentage':
                stripe_coupon = stripe.Coupon.create(
                    id=coupon_id,
                    percent_off=voucher.discount_value,
                    duration='once',
                    metadata={'voucher_id': str(voucher.id), 'user_id': str(user_id)}
                )
            else:  # fixed_amount
                stripe_coupon = stripe.Coupon.create(
                    id=coupon_id,
                    amount_off=int(voucher.discount_value * 100),  # Convert to cents
                    currency=voucher.currency.lower(),
                    duration='once',
                    metadata={'voucher_id': str(voucher.id), 'user_id': str(user_id)}
                )
            
            return {
                'success': True,
                'stripe_coupon_id': stripe_coupon.id,
                'voucher_id': voucher.id
            }
            
        except stripe.error.StripeError as e:
            return {'success': False, 'error': f'Voucher processing error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cancel_subscription(self, user_id: int, immediate: bool = False) -> Dict[str, Any]:
        """Cancel a user's subscription"""
        try:
            subscription = UserSubscription.query.filter_by(
                user_id=user_id,
                status='active'
            ).first()
            
            if not subscription:
                return {'success': False, 'error': 'No active subscription found'}
            
            # Cancel Stripe subscription if it exists
            if subscription.stripe_subscription_id:
                if immediate:
                    stripe.Subscription.delete(subscription.stripe_subscription_id)
                    subscription.status = 'cancelled'
                    subscription.end_date = datetime.utcnow()
                else:
                    stripe.Subscription.modify(
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True
                    )
                    subscription.status = 'cancelled'
                    # Keep end_date as next billing date for access until period end
            else:
                # Free subscription
                subscription.status = 'cancelled'
                subscription.end_date = datetime.utcnow()
            
            subscription.cancelled_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Subscription cancelled successfully',
                'immediate': immediate
            }
            
        except stripe.error.StripeError as e:
            return {'success': False, 'error': f'Payment processing error: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_voucher(self, code: str, discount_type: str, discount_value: float,
                      valid_until: datetime, max_uses: int = 1, 
                      applicable_plans: List[str] = None, created_by: int = None) -> Dict[str, Any]:
        """Create a new discount voucher"""
        try:
            # Check if code already exists
            existing = DiscountVoucher.query.filter_by(code=code).first()
            if existing:
                return {'success': False, 'error': 'Voucher code already exists'}
            
            voucher = DiscountVoucher(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                valid_until=valid_until,
                max_uses=max_uses,
                applicable_plans=json.dumps(applicable_plans) if applicable_plans else None,
                created_by=created_by
            )
            
            db.session.add(voucher)
            db.session.commit()
            
            return {
                'success': True,
                'voucher_id': voucher.id,
                'message': 'Voucher created successfully'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_voucher(self, voucher_code: str, user_id: int = None, 
                        plan_id: str = None) -> Dict[str, Any]:
        """Validate a voucher code"""
        try:
            voucher = DiscountVoucher.query.filter_by(code=voucher_code).first()
            if not voucher:
                return {'success': False, 'error': 'Invalid voucher code'}
            
            is_valid, error_message = voucher.is_valid(user_id, plan_id)
            
            if is_valid:
                return {
                    'success': True,
                    'voucher': voucher.to_dict(),
                    'message': 'Voucher is valid'
                }
            else:
                return {'success': False, 'error': error_message}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Get user's current active subscription"""
        return UserSubscription.query.filter_by(
            user_id=user_id,
            status='active'
        ).first()
    
    def get_subscription_plans(self, language: str = 'en') -> List[Dict[str, Any]]:
        """Get all available subscription plans"""
        plans = SubscriptionPlan.query.filter_by(is_active=True).all()
        return [plan.to_dict() for plan in plans]
    
    def handle_stripe_webhook(self, payload: str, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            
            if event['type'] == 'invoice.payment_succeeded':
                return self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                return self._handle_subscription_deleted(event['data']['object'])
            
            return {'success': True, 'message': 'Event processed'}
            
        except ValueError as e:
            return {'success': False, 'error': 'Invalid payload'}
        except stripe.error.SignatureVerificationError as e:
            return {'success': False, 'error': 'Invalid signature'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_payment_succeeded(self, invoice) -> Dict[str, Any]:
        """Handle successful payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return {'success': True, 'message': 'Not a subscription payment'}
            
            # Find local subscription
            user_subscription = UserSubscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            
            if user_subscription:
                user_subscription.status = 'active'
                
                # Update next billing date
                if user_subscription.billing_cycle == 'monthly':
                    user_subscription.next_billing_date = datetime.utcnow() + timedelta(days=30)
                else:
                    user_subscription.next_billing_date = datetime.utcnow() + timedelta(days=365)
                
                # Create payment transaction record
                transaction = PaymentTransaction(
                    user_id=user_subscription.user_id,
                    subscription_id=user_subscription.id,
                    transaction_type='subscription',
                    status='completed',
                    amount=invoice['amount_paid'] / 100,  # Convert from cents
                    currency=invoice['currency'].upper(),
                    stripe_invoice_id=invoice['id'],
                    description=f"Subscription payment for {user_subscription.plan_id}"
                )
                
                db.session.add(transaction)
                db.session.commit()
            
            return {'success': True, 'message': 'Payment processed'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_payment_failed(self, invoice) -> Dict[str, Any]:
        """Handle failed payment"""
        try:
            subscription_id = invoice.get('subscription')
            if not subscription_id:
                return {'success': True, 'message': 'Not a subscription payment'}
            
            # Find local subscription
            user_subscription = UserSubscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            
            if user_subscription:
                # Don't immediately cancel, Stripe will retry
                # You might want to send notification to user
                
                # Create failed payment transaction record
                transaction = PaymentTransaction(
                    user_id=user_subscription.user_id,
                    subscription_id=user_subscription.id,
                    transaction_type='subscription',
                    status='failed',
                    amount=invoice['amount_due'] / 100,  # Convert from cents
                    currency=invoice['currency'].upper(),
                    stripe_invoice_id=invoice['id'],
                    description=f"Failed subscription payment for {user_subscription.plan_id}"
                )
                
                db.session.add(transaction)
                db.session.commit()
            
            return {'success': True, 'message': 'Failed payment processed'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _handle_subscription_deleted(self, subscription) -> Dict[str, Any]:
        """Handle subscription deletion"""
        try:
            # Find local subscription
            user_subscription = UserSubscription.query.filter_by(
                stripe_subscription_id=subscription['id']
            ).first()
            
            if user_subscription:
                user_subscription.status = 'cancelled'
                user_subscription.end_date = datetime.utcnow()
                user_subscription.cancelled_at = datetime.utcnow()
                db.session.commit()
            
            return {'success': True, 'message': 'Subscription cancelled'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

