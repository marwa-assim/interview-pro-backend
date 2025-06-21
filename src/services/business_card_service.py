import os
import json
import qrcode
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, List
import base64
from io import BytesIO

class BusinessCardGeneratorService:
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'business_cards')
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'business_cards')
        self.qr_codes_dir = os.path.join(self.output_dir, 'qr_codes')
        
        # Create directories if they don't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.qr_codes_dir, exist_ok=True)
        
        # Standard business card dimensions (in pixels at 300 DPI)
        self.card_dimensions = {
            'width': 1050,  # 3.5 inches * 300 DPI
            'height': 600   # 2 inches * 300 DPI
        }

    def generate_business_card(self, card_data: Dict[str, Any], template_id: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generate digital business card with QR code
        
        Args:
            card_data: Dictionary containing all business card information
            template_id: Template identifier
            language: Language code ('en' or 'ar')
            
        Returns:
            Dictionary with generation result and file paths
        """
        try:
            # Generate timestamp for unique filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Generate QR code first
            qr_result = self.generate_qr_code(card_data, timestamp)
            if not qr_result['success']:
                return qr_result
            
            # Generate business card image
            card_filename = f"business_card_{template_id}_{timestamp}.png"
            card_path = os.path.join(self.output_dir, card_filename)
            
            card_result = self._generate_card_image(card_data, template_id, language, card_path, qr_result['qr_path'])
            
            if card_result['success']:
                return {
                    'success': True,
                    'message': 'Business card generated successfully',
                    'card_path': card_path,
                    'card_url': f"/uploads/business_cards/{card_filename}",
                    'qr_code_path': qr_result['qr_path'],
                    'qr_code_url': qr_result['qr_url'],
                    'vcard_data': qr_result['vcard_data']
                }
            else:
                return card_result
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Business card generation failed: {str(e)}",
                'card_path': None,
                'qr_code_path': None
            }

    def generate_qr_code(self, card_data: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        """Generate QR code with vCard data"""
        try:
            # Create vCard data
            vcard_data = self._create_vcard(card_data)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(vcard_data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code
            qr_filename = f"qr_code_{timestamp}.png"
            qr_path = os.path.join(self.qr_codes_dir, qr_filename)
            qr_image.save(qr_path)
            
            return {
                'success': True,
                'qr_path': qr_path,
                'qr_url': f"/uploads/business_cards/qr_codes/{qr_filename}",
                'vcard_data': vcard_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"QR code generation failed: {str(e)}",
                'qr_path': None
            }

    def _create_vcard(self, card_data: Dict[str, Any]) -> str:
        """Create vCard format string from business card data"""
        vcard_lines = [
            "BEGIN:VCARD",
            "VERSION:3.0"
        ]
        
        # Name
        full_name = card_data.get('full_name', '')
        if full_name:
            # Split name for proper vCard format
            name_parts = full_name.split(' ')
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            vcard_lines.append(f"FN:{full_name}")
            vcard_lines.append(f"N:{last_name};{first_name};;;")
        
        # Organization and title
        company = card_data.get('company', '')
        job_title = card_data.get('job_title', '')
        if company:
            vcard_lines.append(f"ORG:{company}")
        if job_title:
            vcard_lines.append(f"TITLE:{job_title}")
        
        # Contact information
        phone = card_data.get('phone', '')
        if phone:
            vcard_lines.append(f"TEL:{phone}")
        
        email = card_data.get('email', '')
        if email:
            vcard_lines.append(f"EMAIL:{email}")
        
        website = card_data.get('website', '')
        if website:
            vcard_lines.append(f"URL:{website}")
        
        # Address
        address = card_data.get('address', '')
        if address:
            vcard_lines.append(f"ADR:;;{address};;;;")
        
        # Social media
        linkedin = card_data.get('linkedin', '')
        if linkedin:
            vcard_lines.append(f"URL;TYPE=LinkedIn:{linkedin}")
        
        twitter = card_data.get('twitter', '')
        if twitter:
            vcard_lines.append(f"URL;TYPE=Twitter:{twitter}")
        
        # Notes
        notes = card_data.get('notes', '')
        if notes:
            vcard_lines.append(f"NOTE:{notes}")
        
        vcard_lines.append("END:VCARD")
        
        return '\n'.join(vcard_lines)

    def _generate_card_image(self, card_data: Dict[str, Any], template_id: str, language: str, output_path: str, qr_path: str) -> Dict[str, Any]:
        """Generate business card image using PIL"""
        try:
            # Create new image with white background
            img = Image.new('RGB', (self.card_dimensions['width'], self.card_dimensions['height']), 'white')
            draw = ImageDraw.Draw(img)
            
            # Load QR code image
            qr_img = Image.open(qr_path)
            qr_size = 150  # QR code size in pixels
            qr_img = qr_img.resize((qr_size, qr_size))
            
            # Apply template-specific styling
            if template_id == 'modern':
                self._apply_modern_template(img, draw, card_data, language, qr_img)
            elif template_id == 'professional':
                self._apply_professional_template(img, draw, card_data, language, qr_img)
            elif template_id == 'creative':
                self._apply_creative_template(img, draw, card_data, language, qr_img)
            else:  # simple template
                self._apply_simple_template(img, draw, card_data, language, qr_img)
            
            # Save the image
            img.save(output_path, 'PNG', quality=95)
            
            return {
                'success': True,
                'message': 'Business card image generated successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Card image generation failed: {str(e)}"
            }

    def _apply_modern_template(self, img: Image.Image, draw: ImageDraw.Draw, card_data: Dict[str, Any], language: str, qr_img: Image.Image):
        """Apply modern template styling"""
        width, height = img.size
        
        # Gradient background (simulate with rectangles)
        for i in range(height):
            color_intensity = int(255 - (i / height) * 50)
            color = (color_intensity, color_intensity, 255)
            draw.line([(0, i), (width, i)], fill=color)
        
        # Try to load fonts, fallback to default if not available
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Position QR code
        qr_x = width - 170
        qr_y = height - 170
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add text content
        y_offset = 50
        
        # Name
        full_name = card_data.get('full_name', '')
        if full_name:
            draw.text((50, y_offset), full_name, fill='white', font=title_font)
            y_offset += 50
        
        # Job title
        job_title = card_data.get('job_title', '')
        if job_title:
            draw.text((50, y_offset), job_title, fill='white', font=subtitle_font)
            y_offset += 35
        
        # Company
        company = card_data.get('company', '')
        if company:
            draw.text((50, y_offset), company, fill='white', font=text_font)
            y_offset += 30
        
        # Contact info
        contact_info = []
        if card_data.get('phone'):
            contact_info.append(f"📞 {card_data['phone']}")
        if card_data.get('email'):
            contact_info.append(f"✉️ {card_data['email']}")
        if card_data.get('website'):
            contact_info.append(f"🌐 {card_data['website']}")
        
        for info in contact_info:
            draw.text((50, y_offset), info, fill='white', font=text_font)
            y_offset += 25

    def _apply_professional_template(self, img: Image.Image, draw: ImageDraw.Draw, card_data: Dict[str, Any], language: str, qr_img: Image.Image):
        """Apply professional template styling"""
        width, height = img.size
        
        # White background with dark blue header
        draw.rectangle([(0, 0), (width, 120)], fill=(25, 25, 112))  # Dark blue header
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Position QR code
        qr_x = width - 170
        qr_y = height - 170
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add text content
        y_offset = 30
        
        # Name in header
        full_name = card_data.get('full_name', '')
        if full_name:
            draw.text((30, y_offset), full_name, fill='white', font=title_font)
        
        # Job title in header
        job_title = card_data.get('job_title', '')
        if job_title:
            draw.text((30, y_offset + 40), job_title, fill='white', font=subtitle_font)
        
        # Body content
        y_offset = 150
        
        # Company
        company = card_data.get('company', '')
        if company:
            draw.text((30, y_offset), company, fill='black', font=subtitle_font)
            y_offset += 35
        
        # Contact information
        contact_info = []
        if card_data.get('phone'):
            contact_info.append(f"Phone: {card_data['phone']}")
        if card_data.get('email'):
            contact_info.append(f"Email: {card_data['email']}")
        if card_data.get('website'):
            contact_info.append(f"Website: {card_data['website']}")
        if card_data.get('address'):
            contact_info.append(f"Address: {card_data['address']}")
        
        for info in contact_info:
            draw.text((30, y_offset), info, fill='black', font=text_font)
            y_offset += 25

    def _apply_creative_template(self, img: Image.Image, draw: ImageDraw.Draw, card_data: Dict[str, Any], language: str, qr_img: Image.Image):
        """Apply creative template styling"""
        width, height = img.size
        
        # Colorful background with geometric shapes
        draw.rectangle([(0, 0), (width, height)], fill=(240, 248, 255))  # Light blue background
        
        # Add some geometric shapes
        draw.ellipse([(width-200, -50), (width+50, 200)], fill=(255, 182, 193))  # Light pink circle
        draw.rectangle([(0, height-100), (150, height)], fill=(144, 238, 144))  # Light green rectangle
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Position QR code
        qr_x = width - 170
        qr_y = height - 170
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add text content with creative positioning
        y_offset = 60
        
        # Name
        full_name = card_data.get('full_name', '')
        if full_name:
            draw.text((40, y_offset), full_name, fill=(75, 0, 130), font=title_font)  # Indigo
            y_offset += 50
        
        # Job title
        job_title = card_data.get('job_title', '')
        if job_title:
            draw.text((40, y_offset), job_title, fill=(220, 20, 60), font=subtitle_font)  # Crimson
            y_offset += 40
        
        # Company
        company = card_data.get('company', '')
        if company:
            draw.text((40, y_offset), company, fill=(0, 100, 0), font=text_font)  # Dark green
            y_offset += 35
        
        # Contact info with icons
        contact_info = []
        if card_data.get('phone'):
            contact_info.append(f"📱 {card_data['phone']}")
        if card_data.get('email'):
            contact_info.append(f"📧 {card_data['email']}")
        if card_data.get('website'):
            contact_info.append(f"🌍 {card_data['website']}")
        
        for info in contact_info:
            draw.text((40, y_offset), info, fill=(25, 25, 112), font=text_font)
            y_offset += 28

    def _apply_simple_template(self, img: Image.Image, draw: ImageDraw.Draw, card_data: Dict[str, Any], language: str, qr_img: Image.Image):
        """Apply simple template styling"""
        width, height = img.size
        
        # Simple white background with black border
        draw.rectangle([(5, 5), (width-5, height-5)], outline='black', width=3)
        
        # Try to load fonts
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Position QR code
        qr_x = width - 170
        qr_y = height - 170
        img.paste(qr_img, (qr_x, qr_y))
        
        # Add text content
        y_offset = 40
        
        # Name
        full_name = card_data.get('full_name', '')
        if full_name:
            draw.text((30, y_offset), full_name, fill='black', font=title_font)
            y_offset += 45
        
        # Job title
        job_title = card_data.get('job_title', '')
        if job_title:
            draw.text((30, y_offset), job_title, fill='black', font=subtitle_font)
            y_offset += 35
        
        # Company
        company = card_data.get('company', '')
        if company:
            draw.text((30, y_offset), company, fill='black', font=subtitle_font)
            y_offset += 35
        
        # Separator line
        draw.line([(30, y_offset + 10), (width - 200, y_offset + 10)], fill='gray', width=1)
        y_offset += 25
        
        # Contact information
        contact_info = []
        if card_data.get('phone'):
            contact_info.append(f"Phone: {card_data['phone']}")
        if card_data.get('email'):
            contact_info.append(f"Email: {card_data['email']}")
        if card_data.get('website'):
            contact_info.append(f"Web: {card_data['website']}")
        if card_data.get('address'):
            contact_info.append(f"Address: {card_data['address']}")
        
        for info in contact_info:
            draw.text((30, y_offset), info, fill='black', font=text_font)
            y_offset += 22

    def get_available_templates(self, language: str = 'en') -> List[Dict[str, Any]]:
        """Get list of available business card templates"""
        if language == 'ar':
            templates = [
                {
                    'id': 'modern',
                    'name': 'عصري',
                    'description': 'تصميم عصري مع خلفية متدرجة',
                    'preview_url': '/static/templates/business_card_modern_preview.png'
                },
                {
                    'id': 'professional',
                    'name': 'مهني',
                    'description': 'تصميم مهني كلاسيكي',
                    'preview_url': '/static/templates/business_card_professional_preview.png'
                },
                {
                    'id': 'creative',
                    'name': 'إبداعي',
                    'description': 'تصميم إبداعي ملون',
                    'preview_url': '/static/templates/business_card_creative_preview.png'
                },
                {
                    'id': 'simple',
                    'name': 'بسيط',
                    'description': 'تصميم بسيط ونظيف',
                    'preview_url': '/static/templates/business_card_simple_preview.png'
                }
            ]
        else:
            templates = [
                {
                    'id': 'modern',
                    'name': 'Modern',
                    'description': 'Modern design with gradient background',
                    'preview_url': '/static/templates/business_card_modern_preview.png'
                },
                {
                    'id': 'professional',
                    'name': 'Professional',
                    'description': 'Classic professional design',
                    'preview_url': '/static/templates/business_card_professional_preview.png'
                },
                {
                    'id': 'creative',
                    'name': 'Creative',
                    'description': 'Colorful creative design',
                    'preview_url': '/static/templates/business_card_creative_preview.png'
                },
                {
                    'id': 'simple',
                    'name': 'Simple',
                    'description': 'Clean and simple design',
                    'preview_url': '/static/templates/business_card_simple_preview.png'
                }
            ]
        
        return templates

    def get_sample_card_data(self, language: str = 'en') -> Dict[str, Any]:
        """Get sample business card data for testing and demonstration"""
        if language == 'ar':
            return {
                'full_name': 'أحمد محمد علي',
                'job_title': 'مطور برمجيات أول',
                'company': 'شركة التقنية المتقدمة',
                'phone': '+966 50 123 4567',
                'email': 'ahmed.ali@techcompany.com',
                'website': 'www.ahmed-portfolio.com',
                'address': 'الرياض، المملكة العربية السعودية',
                'linkedin': 'linkedin.com/in/ahmed-ali',
                'twitter': '@ahmed_dev',
                'notes': 'متخصص في تطوير تطبيقات الويب والهاتف المحمول'
            }
        else:
            return {
                'full_name': 'John Smith',
                'job_title': 'Senior Software Developer',
                'company': 'Tech Solutions Inc.',
                'phone': '+1 (555) 123-4567',
                'email': 'john.smith@techsolutions.com',
                'website': 'www.johnsmith-portfolio.com',
                'address': 'New York, NY, USA',
                'linkedin': 'linkedin.com/in/johnsmith',
                'twitter': '@johnsmith_dev',
                'notes': 'Specializing in web and mobile application development'
            }

    def validate_card_data(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business card data"""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['full_name', 'phone', 'email']
        for field in required_fields:
            if not card_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Email validation (basic)
        email = card_data.get('email', '')
        if email and '@' not in email:
            errors.append("Invalid email format")
        
        # Phone validation (basic)
        phone = card_data.get('phone', '')
        if phone and len(phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')) < 10:
            warnings.append("Phone number seems too short")
        
        # URL validation (basic)
        website = card_data.get('website', '')
        if website and not (website.startswith('http://') or website.startswith('https://') or website.startswith('www.')):
            warnings.append("Website URL should include protocol (http:// or https://) or start with www.")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

