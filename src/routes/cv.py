from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.content import CV, CVTemplate
from src.services.cv_generator_service import CVGeneratorService
import json
import os

cv_bp = Blueprint('cv', __name__)

# Initialize CV generator service
cv_generator = CVGeneratorService()

@cv_bp.route('/templates', methods=['GET'])
def get_cv_templates():
    """Get available CV templates"""
    try:
        # Return predefined templates
        templates = [
            {
                'id': 'modern',
                'name': 'Modern',
                'name_ar': 'عصري',
                'description': 'Clean and modern design with gradient header',
                'description_ar': 'تصميم نظيف وعصري مع رأس متدرج',
                'preview_url': '/static/templates/modern_preview.png',
                'ats_compliant': True
            },
            {
                'id': 'professional',
                'name': 'Professional',
                'name_ar': 'مهني',
                'description': 'Traditional professional layout',
                'description_ar': 'تخطيط مهني تقليدي',
                'preview_url': '/static/templates/professional_preview.png',
                'ats_compliant': True
            },
            {
                'id': 'creative',
                'name': 'Creative',
                'name_ar': 'إبداعي',
                'description': 'Creative design for artistic fields',
                'description_ar': 'تصميم إبداعي للمجالات الفنية',
                'preview_url': '/static/templates/creative_preview.png',
                'ats_compliant': False
            },
            {
                'id': 'simple',
                'name': 'Simple',
                'name_ar': 'بسيط',
                'description': 'Minimalist ATS-friendly design',
                'description_ar': 'تصميم بسيط متوافق مع أنظمة التتبع',
                'preview_url': '/static/templates/simple_preview.png',
                'ats_compliant': True
            }
        ]
        
        return jsonify({'templates': templates}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/create', methods=['POST'])
@jwt_required()
def create_cv():
    """Create a new CV"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['template_id', 'language', 'cv_data']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create new CV
        cv = CV(
            user_id=user_id,
            template_id=data['template_id'],
            language=data['language'],
            data_json=json.dumps(data['cv_data']),
            title=data.get('title', 'My CV')
        )
        
        db.session.add(cv)
        db.session.commit()
        
        return jsonify({
            'message': 'CV created successfully',
            'cv': cv.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>', methods=['GET'])
@jwt_required()
def get_cv():
    """Get a specific CV"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        return jsonify({'cv': cv.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>', methods=['PUT'])
@jwt_required()
def update_cv():
    """Update an existing CV"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        data = request.get_json()
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        # Update CV data
        if 'cv_data' in data:
            cv.data_json = json.dumps(data['cv_data'])
        if 'title' in data:
            cv.title = data['title']
        if 'template_id' in data:
            cv.template_id = data['template_id']
        
        db.session.commit()
        
        return jsonify({
            'message': 'CV updated successfully',
            'cv': cv.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>', methods=['DELETE'])
@jwt_required()
def delete_cv():
    """Delete a CV"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        # Delete associated PDF file if exists
        if cv.generated_pdf_url:
            try:
                pdf_path = cv.generated_pdf_url.replace('/uploads/cvs/', '')
                full_path = os.path.join(cv_generator.output_dir, pdf_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            except:
                pass  # Continue even if file deletion fails
        
        db.session.delete(cv)
        db.session.commit()
        
        return jsonify({'message': 'CV deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/list', methods=['GET'])
@jwt_required()
def list_user_cvs():
    """Get user's CV list"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get paginated CVs
        cvs = CV.query.filter_by(user_id=user_id)\
            .order_by(CV.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'cvs': [cv.to_dict() for cv in cvs.items],
            'total': cvs.total,
            'pages': cvs.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>/generate-pdf', methods=['POST'])
@jwt_required()
def generate_cv_pdf():
    """Generate PDF for a CV"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        # Parse CV data
        cv_data = json.loads(cv.data_json)
        
        # Generate PDF using CV generator service
        result = cv_generator.generate_cv_pdf(cv_data, cv.template_id, cv.language)
        
        if result['success']:
            # Update CV record with generated PDF info
            cv.generated_pdf_url = result['file_url']
            cv.is_ats_compliant = result['ats_compliant']
            cv.ats_compliance_score = result.get('ats_issues', [])
            
            db.session.commit()
            
            return jsonify({
                'message': 'PDF generated successfully',
                'pdf_url': result['file_url'],
                'file_path': result['file_path'],
                'is_ats_compliant': result['ats_compliant'],
                'ats_issues': result['ats_issues']
            }), 200
        else:
            return jsonify({
                'error': result['error']
            }), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>/download', methods=['GET'])
@jwt_required()
def download_cv_pdf():
    """Download CV PDF file"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        if not cv.generated_pdf_url:
            return jsonify({'error': 'PDF not generated yet'}), 404
        
        # Extract filename from URL
        filename = cv.generated_pdf_url.split('/')[-1]
        file_path = os.path.join(cv_generator.output_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'PDF file not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"cv_{cv.title.replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/<int:cv_id>/check-ats', methods=['GET'])
@jwt_required()
def check_ats_compliance():
    """Check ATS compliance of a CV"""
    try:
        user_id = get_jwt_identity()
        cv_id = request.view_args['cv_id']
        
        # Verify CV belongs to user
        cv = CV.query.filter_by(id=cv_id, user_id=user_id).first()
        if not cv:
            return jsonify({'error': 'CV not found'}), 404
        
        # Parse CV data
        cv_data = json.loads(cv.data_json)
        
        # Check ATS compliance
        if cv.generated_pdf_url:
            filename = cv.generated_pdf_url.split('/')[-1]
            file_path = os.path.join(cv_generator.output_dir, filename)
            compliance_result = cv_generator.check_ats_compliance(cv_data, file_path)
        else:
            # Check data compliance without PDF
            compliance_result = cv_generator.check_ats_compliance(cv_data, None)
        
        return jsonify({
            'ats_compliant': compliance_result['compliant'],
            'compliance_score': compliance_result['score'],
            'issues': compliance_result['issues']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cv_bp.route('/sample-data', methods=['GET'])
def get_sample_cv_data():
    """Get sample CV data structure"""
    language = request.args.get('language', 'en')
    sample_data = cv_generator.get_sample_cv_data(language)
    
    return jsonify({'sample_data': sample_data}), 200

@cv_bp.route('/ats-guidelines', methods=['GET'])
def get_ats_guidelines():
    """Get ATS compliance guidelines"""
    language = request.args.get('language', 'en')
    
    if language == 'ar':
        guidelines = {
            'title': 'إرشادات التوافق مع أنظمة تتبع المتقدمين (ATS)',
            'description': 'اتبع هذه الإرشادات لضمان توافق سيرتك الذاتية مع أنظمة تتبع المتقدمين',
            'rules': [
                'استخدم خطوط قياسية مثل Arial أو Times New Roman',
                'تجنب الصور والرسوم البيانية المعقدة',
                'استخدم عناوين قياسية مثل "الخبرة المهنية" و"التعليم"',
                'احفظ الملف بصيغة PDF أو DOCX',
                'تأكد من أن حجم الملف أقل من 2 ميجابايت',
                'استخدم تخطيط بسيط بعمود واحد أو عمودين كحد أقصى',
                'تجنب الجداول المعقدة والتنسيق المتقدم',
                'استخدم نقاط واضحة ومباشرة',
                'تأكد من وجود معلومات الاتصال الأساسية',
                'استخدم كلمات مفتاحية ذات صلة بالوظيفة'
            ]
        }
    else:
        guidelines = {
            'title': 'ATS Compliance Guidelines',
            'description': 'Follow these guidelines to ensure your CV is compatible with Applicant Tracking Systems',
            'rules': [
                'Use standard fonts like Arial, Times New Roman, or Calibri',
                'Avoid complex graphics and images',
                'Use standard section headings like "Experience" and "Education"',
                'Save file as PDF or DOCX format',
                'Keep file size under 2MB',
                'Use simple layout with maximum 2 columns',
                'Avoid complex tables and advanced formatting',
                'Use clear and direct bullet points',
                'Include essential contact information',
                'Use relevant keywords for the job position'
            ]
        }
    
    return jsonify({'guidelines': guidelines}), 200

