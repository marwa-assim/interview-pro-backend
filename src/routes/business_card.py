from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.content import DigitalBusinessCard, BusinessCardTemplate
from src.services.business_card_service import BusinessCardGeneratorService
import json
import os

business_card_bp = Blueprint('business_card', __name__)

# Initialize business card generator service
card_generator = BusinessCardGeneratorService()

@business_card_bp.route('/templates', methods=['GET'])
def get_business_card_templates():
    """Get available business card templates"""
    try:
        language = request.args.get('language', 'en')
        templates = card_generator.get_available_templates(language)
        return jsonify({'templates': templates}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/create', methods=['POST'])
@jwt_required()
def create_business_card():
    """Create a new digital business card"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['template_id', 'language', 'card_data']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate card data
        validation_result = card_generator.validate_card_data(data['card_data'])
        if not validation_result['valid']:
            return jsonify({
                'error': 'Invalid card data',
                'validation_errors': validation_result['errors']
            }), 400
        
        # Create new business card record
        business_card = DigitalBusinessCard(
            user_id=user_id,
            template_id=data['template_id'],
            language=data['language'],
            data_json=json.dumps(data['card_data']),
            title=data.get('title', 'My Business Card')
        )
        
        db.session.add(business_card)
        db.session.flush()  # Get the ID
        
        # Generate business card image and QR code
        generation_result = card_generator.generate_business_card(
            data['card_data'], 
            data['template_id'], 
            data['language']
        )
        
        if generation_result['success']:
            # Update business card with generated URLs
            business_card.qr_code_image_url = generation_result['qr_code_url']
            business_card.digital_card_url = generation_result['card_url']
            business_card.generated_image_path = generation_result['card_path']
            
            db.session.commit()
            
            return jsonify({
                'message': 'Business card created successfully',
                'business_card': business_card.to_dict(),
                'card_image_url': generation_result['card_url'],
                'qr_code_url': generation_result['qr_code_url'],
                'validation_warnings': validation_result.get('warnings', [])
            }), 201
        else:
            db.session.rollback()
            return jsonify({
                'error': generation_result['error']
            }), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>', methods=['GET'])
@jwt_required()
def get_business_card():
    """Get a specific business card"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        return jsonify({'business_card': card.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>', methods=['PUT'])
@jwt_required()
def update_business_card():
    """Update an existing business card"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        data = request.get_json()
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        # Update business card data
        regenerate_needed = False
        
        if 'card_data' in data:
            # Validate new card data
            validation_result = card_generator.validate_card_data(data['card_data'])
            if not validation_result['valid']:
                return jsonify({
                    'error': 'Invalid card data',
                    'validation_errors': validation_result['errors']
                }), 400
            
            card.data_json = json.dumps(data['card_data'])
            regenerate_needed = True
        
        if 'title' in data:
            card.title = data['title']
        
        if 'template_id' in data:
            card.template_id = data['template_id']
            regenerate_needed = True
        
        # Regenerate card if needed
        if regenerate_needed:
            card_data = json.loads(card.data_json)
            generation_result = card_generator.generate_business_card(
                card_data, 
                card.template_id, 
                card.language
            )
            
            if generation_result['success']:
                # Delete old files
                if card.generated_image_path and os.path.exists(card.generated_image_path):
                    try:
                        os.remove(card.generated_image_path)
                    except:
                        pass
                
                # Update with new URLs
                card.qr_code_image_url = generation_result['qr_code_url']
                card.digital_card_url = generation_result['card_url']
                card.generated_image_path = generation_result['card_path']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Business card updated successfully',
            'business_card': card.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>', methods=['DELETE'])
@jwt_required()
def delete_business_card():
    """Delete a business card"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        # Delete associated files
        if card.generated_image_path and os.path.exists(card.generated_image_path):
            try:
                os.remove(card.generated_image_path)
            except:
                pass
        
        # Delete QR code file if exists
        if card.qr_code_image_url:
            try:
                qr_filename = card.qr_code_image_url.split('/')[-1]
                qr_path = os.path.join(card_generator.qr_codes_dir, qr_filename)
                if os.path.exists(qr_path):
                    os.remove(qr_path)
            except:
                pass
        
        db.session.delete(card)
        db.session.commit()
        
        return jsonify({'message': 'Business card deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/list', methods=['GET'])
@jwt_required()
def list_user_business_cards():
    """Get user's business card list"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get paginated business cards
        cards = DigitalBusinessCard.query.filter_by(user_id=user_id)\
            .order_by(DigitalBusinessCard.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'business_cards': [card.to_dict() for card in cards.items],
            'total': cards.total,
            'pages': cards.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>/download', methods=['GET'])
@jwt_required()
def download_business_card():
    """Download business card image"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        if not card.generated_image_path or not os.path.exists(card.generated_image_path):
            return jsonify({'error': 'Business card image not found'}), 404
        
        return send_file(
            card.generated_image_path,
            as_attachment=True,
            download_name=f"business_card_{card.title.replace(' ', '_')}.png",
            mimetype='image/png'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>/qr-code', methods=['GET'])
@jwt_required()
def download_qr_code():
    """Download QR code image"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        if not card.qr_code_image_url:
            return jsonify({'error': 'QR code not found'}), 404
        
        # Extract filename from URL
        qr_filename = card.qr_code_image_url.split('/')[-1]
        qr_path = os.path.join(card_generator.qr_codes_dir, qr_filename)
        
        if not os.path.exists(qr_path):
            return jsonify({'error': 'QR code file not found'}), 404
        
        return send_file(
            qr_path,
            as_attachment=True,
            download_name=f"qr_code_{card.title.replace(' ', '_')}.png",
            mimetype='image/png'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/sample-data', methods=['GET'])
def get_sample_business_card_data():
    """Get sample business card data structure"""
    language = request.args.get('language', 'en')
    sample_data = card_generator.get_sample_card_data(language)
    
    return jsonify({'sample_data': sample_data}), 200

@business_card_bp.route('/validate-data', methods=['POST'])
def validate_business_card_data():
    """Validate business card data"""
    try:
        data = request.get_json()
        card_data = data.get('card_data', {})
        
        validation_result = card_generator.validate_card_data(card_data)
        
        return jsonify({
            'valid': validation_result['valid'],
            'errors': validation_result['errors'],
            'warnings': validation_result['warnings']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/public/<int:card_id>', methods=['GET'])
def get_public_business_card():
    """Get public view of a business card (for sharing)"""
    try:
        card_id = request.view_args['card_id']
        
        # Get business card (no authentication required for public view)
        card = DigitalBusinessCard.query.get(card_id)
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        # Return public data (excluding sensitive information)
        card_data = card.to_dict()
        # Remove user_id for privacy
        card_data.pop('user_id', None)
        
        # Parse and return the card data for display
        parsed_data = json.loads(card.data_json)
        
        return jsonify({
            'business_card': card_data,
            'card_data': parsed_data,
            'public_url': f"/api/business-cards/public/{card_id}"
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@business_card_bp.route('/<int:card_id>/share-url', methods=['GET'])
@jwt_required()
def get_share_url():
    """Get shareable URL for a business card"""
    try:
        user_id = get_jwt_identity()
        card_id = request.view_args['card_id']
        
        # Verify business card belongs to user
        card = DigitalBusinessCard.query.filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return jsonify({'error': 'Business card not found'}), 404
        
        # Generate share URL
        base_url = request.host_url.rstrip('/')
        share_url = f"{base_url}/api/business-cards/public/{card_id}"
        
        return jsonify({
            'share_url': share_url,
            'qr_code_url': card.qr_code_image_url,
            'card_image_url': card.digital_card_url
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

