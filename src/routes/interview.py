from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.models.interview import MockInterview, InterviewQuestion, InterviewResponse
from src.services.ai_interview_service import AIInterviewService
from src.services.speech_service import SpeechService
from datetime import datetime
import json
import os

interview_bp = Blueprint('interview', __name__)

# Initialize AI and Speech services
ai_service = AIInterviewService()
speech_service = SpeechService()

@interview_bp.route('/start', methods=['POST'])
@jwt_required()
def start_interview():
    """Start a new mock interview session"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('major') or not data.get('language'):
            return jsonify({'error': 'Major and language are required'}), 400
        
        # Create new interview session
        interview = MockInterview(
            user_id=user_id,
            major=data['major'],
            language=data['language'],
            start_time=datetime.utcnow(),
            status='in_progress'
        )
        
        db.session.add(interview)
        db.session.flush()  # Get the interview ID
        
        # Generate questions using AI service
        questions_data = ai_service.generate_questions(
            data['major'], 
            data['language'], 
            data.get('num_questions', 5)
        )
        
        # Save questions to database
        for question_data in questions_data:
            question = InterviewQuestion(
                interview_id=interview.id,
                question_text=question_data['question_text'],
                question_language=question_data['question_language'],
                ai_generated=question_data['ai_generated'],
                order_in_interview=question_data['order_in_interview']
            )
            db.session.add(question)
        
        db.session.commit()
        
        # Return interview details with questions
        interview_data = interview.to_dict()
        interview_data['questions'] = [q.to_dict() for q in interview.questions]
        
        return jsonify({
            'message': 'Interview started successfully',
            'interview': interview_data
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<int:interview_id>/submit-response', methods=['POST'])
@jwt_required()
def submit_response():
    """Submit response to an interview question"""
    try:
        user_id = get_jwt_identity()
        interview_id = request.view_args['interview_id']
        data = request.get_json()
        
        # Validate required fields
        if not data.get('question_id'):
            return jsonify({'error': 'Question ID is required'}), 400
        
        # Verify interview belongs to user
        interview = MockInterview.query.filter_by(id=interview_id, user_id=user_id).first()
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Verify question belongs to interview
        question = InterviewQuestion.query.filter_by(
            id=data['question_id'], 
            interview_id=interview_id
        ).first()
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        # Process audio if provided
        response_text = data.get('response_text', '')
        audio_url = data.get('audio_url')
        
        if audio_url and not response_text:
            # Transcribe audio to text
            transcription_result = speech_service.transcribe_audio_file(
                audio_url, 
                interview.language
            )
            if transcription_result['success']:
                response_text = transcription_result['text']
            else:
                return jsonify({
                    'error': f"Audio transcription failed: {transcription_result['error']}"
                }), 400
        
        # Create response record
        response = InterviewResponse(
            question_id=data['question_id'],
            user_response_text=response_text,
            user_response_audio_url=audio_url
        )
        
        # Analyze response using AI service
        if response_text:
            analysis_result = ai_service.analyze_response(
                question.question_text,
                response_text,
                interview.language
            )
            
            response.clarity_score = analysis_result['clarity_score']
            response.relevance_score = analysis_result['relevance_score']
            response.sentiment_score = analysis_result['sentiment_score']
            response.ai_feedback_text = analysis_result['ai_feedback_text']
        
        db.session.add(response)
        db.session.commit()
        
        return jsonify({
            'message': 'Response submitted successfully',
            'response': response.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<int:interview_id>/upload-audio', methods=['POST'])
@jwt_required()
def upload_audio():
    """Upload audio file for transcription"""
    try:
        user_id = get_jwt_identity()
        interview_id = request.view_args['interview_id']
        
        # Verify interview belongs to user
        interview = MockInterview.query.filter_by(id=interview_id, user_id=user_id).first()
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Check if audio file is provided
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('uploads', 'audio')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save audio file
        filename = f"interview_{interview_id}_{datetime.utcnow().timestamp()}.wav"
        file_path = os.path.join(upload_dir, filename)
        audio_file.save(file_path)
        
        # Validate audio quality
        quality_check = speech_service.validate_audio_quality(file_path)
        if not quality_check['suitable_for_recognition']:
            return jsonify({
                'error': 'Audio quality too low for recognition',
                'quality_issues': quality_check['issues']
            }), 400
        
        # Transcribe audio
        transcription_result = speech_service.transcribe_audio_file(
            file_path, 
            interview.language
        )
        
        if transcription_result['success']:
            return jsonify({
                'message': 'Audio uploaded and transcribed successfully',
                'transcription': transcription_result['text'],
                'confidence': transcription_result['confidence'],
                'audio_url': file_path,
                'quality_score': quality_check['quality_score']
            }), 200
        else:
            return jsonify({
                'error': f"Transcription failed: {transcription_result['error']}"
            }), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<int:interview_id>/complete', methods=['POST'])
@jwt_required()
def complete_interview():
    """Complete an interview session"""
    try:
        user_id = get_jwt_identity()
        interview_id = request.view_args['interview_id']
        
        # Verify interview belongs to user
        interview = MockInterview.query.filter_by(id=interview_id, user_id=user_id).first()
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Update interview status
        interview.end_time = datetime.utcnow()
        interview.status = 'completed'
        
        # Calculate overall score
        responses = InterviewResponse.query.join(InterviewQuestion).filter(
            InterviewQuestion.interview_id == interview_id
        ).all()
        
        if responses:
            total_score = sum([
                (r.clarity_score or 0) + (r.relevance_score or 0) + (r.sentiment_score or 0)
                for r in responses
            ])
            interview.overall_score = total_score / (len(responses) * 3)  # Average out of 5
        
        db.session.commit()
        
        return jsonify({
            'message': 'Interview completed successfully',
            'interview': interview.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/history', methods=['GET'])
@jwt_required()
def get_interview_history():
    """Get user's interview history"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get paginated interviews
        interviews = MockInterview.query.filter_by(user_id=user_id)\
            .order_by(MockInterview.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'interviews': [interview.to_dict() for interview in interviews.items],
            'total': interviews.total,
            'pages': interviews.pages,
            'current_page': page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/<int:interview_id>/report', methods=['GET'])
@jwt_required()
def get_interview_report():
    """Get detailed interview report"""
    try:
        user_id = get_jwt_identity()
        interview_id = request.view_args['interview_id']
        
        # Verify interview belongs to user
        interview = MockInterview.query.filter_by(id=interview_id, user_id=user_id).first()
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Get questions and responses
        questions_with_responses = []
        for question in interview.questions:
            question_data = question.to_dict()
            question_data['responses'] = [r.to_dict() for r in question.responses]
            questions_with_responses.append(question_data)
        
        # Generate comprehensive report using AI service
        interview_data = {
            'questions': questions_with_responses,
            'language': interview.language,
            'major': interview.major
        }
        
        report = ai_service.generate_interview_report(interview_data)
        report['interview'] = interview.to_dict()
        
        return jsonify({'report': report}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/majors', methods=['GET'])
def get_available_majors():
    """Get list of available majors for interviews"""
    majors = [
        {'id': 'it', 'name': 'Information Technology', 'name_ar': 'تكنولوجيا المعلومات'},
        {'id': 'business', 'name': 'Business', 'name_ar': 'الأعمال'},
        {'id': 'engineering', 'name': 'Engineering', 'name_ar': 'الهندسة'},
        {'id': 'medicine', 'name': 'Medicine', 'name_ar': 'الطب'},
        {'id': 'pharmacy', 'name': 'Pharmacy', 'name_ar': 'الصيدلة'},
        {'id': 'law', 'name': 'Law', 'name_ar': 'القانون'}
    ]
    
    return jsonify({'majors': majors}), 200

