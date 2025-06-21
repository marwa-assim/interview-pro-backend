from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.interview import MockInterview
from src.models.content import CV, DigitalBusinessCard, AdminReport
from datetime import datetime, timedelta
import json
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        # Get basic statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        total_interviews = MockInterview.query.count()
        completed_interviews = MockInterview.query.filter_by(status='completed').count()
        total_cvs = CV.query.count()
        total_business_cards = DigitalBusinessCard.query.count()
        
        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_users_30d = User.query.filter(User.created_at >= thirty_days_ago).count()
        new_interviews_30d = MockInterview.query.filter(MockInterview.created_at >= thirty_days_ago).count()
        
        # Get subscription statistics
        active_subscriptions = UserSubscription.query.filter_by(is_active=True).count()
        
        stats = {
            'total_users': total_users,
            'active_users': active_users,
            'total_interviews': total_interviews,
            'completed_interviews': completed_interviews,
            'total_cvs': total_cvs,
            'total_business_cards': total_business_cards,
            'new_users_30d': new_users_30d,
            'new_interviews_30d': new_interviews_30d,
            'active_subscriptions': active_subscriptions
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    """Get paginated list of users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = User.query
        
        # Apply search filter
        if search:
            query = query.filter(
                (User.username.contains(search)) |
                (User.email.contains(search)) |
                (User.first_name.contains(search)) |
                (User.last_name.contains(search))
            )
        
        # Get paginated results
        users = query.order_by(User.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user():
    """Update user information (admin only)"""
    try:
        user_id = request.view_args['user_id']
        data = request.get_json()
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update allowed fields
        allowed_fields = ['is_active', 'role']
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/subscription-plans', methods=['GET'])
@jwt_required()
@admin_required
def get_subscription_plans():
    """Get all subscription plans"""
    try:
        plans = SubscriptionPlan.query.all()
        return jsonify({
            'plans': [plan.to_dict() for plan in plans]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/subscription-plans', methods=['POST'])
@jwt_required()
@admin_required
def create_subscription_plan():
    """Create a new subscription plan"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'price', 'duration_days']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        plan = SubscriptionPlan(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            currency=data.get('currency', 'USD'),
            duration_days=data['duration_days'],
            max_mock_interviews=data.get('max_mock_interviews'),
            max_cv_generations=data.get('max_cv_generations'),
            max_business_cards=data.get('max_business_cards')
        )
        
        db.session.add(plan)
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription plan created successfully',
            'plan': plan.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/vouchers', methods=['GET'])
@jwt_required()
@admin_required
def get_vouchers():
    """Get all vouchers"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        vouchers = Voucher.query.order_by(Voucher.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'vouchers': [voucher.to_dict() for voucher in vouchers.items],
            'total': vouchers.total,
            'pages': vouchers.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/vouchers', methods=['POST'])
@jwt_required()
@admin_required
def create_voucher():
    """Create a new discount voucher"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['code', 'percentage_discount', 'valid_from', 'valid_until']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if voucher code already exists
        existing_voucher = Voucher.query.filter_by(code=data['code']).first()
        if existing_voucher:
            return jsonify({'error': 'Voucher code already exists'}), 400
        
        voucher = Voucher(
            code=data['code'],
            percentage_discount=data['percentage_discount'],
            valid_from=datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00')),
            valid_until=datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00')),
            is_one_time_use=data.get('is_one_time_use', True)
        )
        
        db.session.add(voucher)
        db.session.commit()
        
        return jsonify({
            'message': 'Voucher created successfully',
            'voucher': voucher.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/interviews', methods=['GET'])
@jwt_required()
@admin_required
def get_all_interviews():
    """Get all interviews with user information"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        interviews = db.session.query(MockInterview, User)\
            .join(User, MockInterview.user_id == User.id)\
            .order_by(MockInterview.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        interview_data = []
        for interview, user in interviews.items:
            interview_dict = interview.to_dict()
            interview_dict['user'] = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            interview_data.append(interview_dict)
        
        return jsonify({
            'interviews': interview_data,
            'total': interviews.total,
            'pages': interviews.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports/generate', methods=['POST'])
@jwt_required()
@admin_required
def generate_report():
    """Generate admin report"""
    try:
        admin_user_id = get_jwt_identity()
        data = request.get_json()
        
        report_type = data.get('report_type', 'user_activity')
        
        # Generate different types of reports
        if report_type == 'user_activity':
            # User activity report
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            new_users_7d = User.query.filter(
                User.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            report_data = {
                'total_users': total_users,
                'active_users': active_users,
                'new_users_7d': new_users_7d,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        elif report_type == 'interview_summary':
            # Interview summary report
            total_interviews = MockInterview.query.count()
            completed_interviews = MockInterview.query.filter_by(status='completed').count()
            avg_score = db.session.query(db.func.avg(MockInterview.overall_score))\
                .filter(MockInterview.overall_score.isnot(None)).scalar()
            
            report_data = {
                'total_interviews': total_interviews,
                'completed_interviews': completed_interviews,
                'average_score': float(avg_score) if avg_score else 0,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        # Save report
        report = AdminReport(
            report_type=report_type,
            generated_by_user_id=admin_user_id,
            generation_time=datetime.utcnow(),
            report_data_json=json.dumps(report_data)
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report generated successfully',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/reports', methods=['GET'])
@jwt_required()
@admin_required
def get_reports():
    """Get all admin reports"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        reports = AdminReport.query.order_by(AdminReport.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'reports': [report.to_dict() for report in reports.items],
            'total': reports.total,
            'pages': reports.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

