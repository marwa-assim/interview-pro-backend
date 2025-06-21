import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from weasyprint import HTML, CSS
from typing import Dict, Any, List

class CVGeneratorService:
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'cv')
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'cvs')
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # ATS compliance rules
        self.ats_rules = {
            'max_file_size_mb': 2,
            'preferred_formats': ['pdf', 'docx'],
            'avoid_graphics': True,
            'use_standard_fonts': True,
            'standard_fonts': ['Arial', 'Helvetica', 'Times New Roman', 'Calibri'],
            'max_columns': 2,
            'use_standard_headings': True,
            'standard_headings': [
                'Personal Information', 'Professional Summary', 'Experience', 
                'Education', 'Skills', 'Certifications', 'Projects'
            ]
        }

    def generate_cv_pdf(self, cv_data: Dict[str, Any], template_id: str, language: str = 'en') -> Dict[str, Any]:
        """
        Generate CV PDF from data and template
        
        Args:
            cv_data: Dictionary containing all CV information
            template_id: Template identifier
            language: Language code ('en' or 'ar')
            
        Returns:
            Dictionary with generation result and file path
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"cv_{template_id}_{timestamp}.pdf"
            file_path = os.path.join(self.output_dir, filename)
            
            # Choose generation method based on template
            if template_id in ['modern', 'professional', 'creative']:
                result = self._generate_html_cv(cv_data, template_id, language, file_path)
            else:
                result = self._generate_reportlab_cv(cv_data, template_id, language, file_path)
            
            if result['success']:
                # Check ATS compliance
                compliance_check = self.check_ats_compliance(cv_data, file_path)
                result['ats_compliant'] = compliance_check['compliant']
                result['ats_issues'] = compliance_check['issues']
                result['file_path'] = file_path
                result['file_url'] = f"/uploads/cvs/{filename}"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"CV generation failed: {str(e)}",
                'file_path': None,
                'ats_compliant': False
            }

    def _generate_html_cv(self, cv_data: Dict[str, Any], template_id: str, language: str, output_path: str) -> Dict[str, Any]:
        """Generate CV using HTML/CSS template and WeasyPrint"""
        try:
            # Generate HTML content
            html_content = self._create_html_template(cv_data, template_id, language)
            
            # Generate CSS styles
            css_content = self._create_css_styles(template_id, language)
            
            # Convert to PDF using WeasyPrint
            HTML(string=html_content).write_pdf(
                output_path,
                stylesheets=[CSS(string=css_content)]
            )
            
            return {
                'success': True,
                'message': 'CV generated successfully using HTML template'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"HTML CV generation failed: {str(e)}"
            }

    def _generate_reportlab_cv(self, cv_data: Dict[str, Any], template_id: str, language: str, output_path: str) -> Dict[str, Any]:
        """Generate CV using ReportLab (for simple templates)"""
        try:
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=12,
                alignment=TA_CENTER if language == 'ar' else TA_LEFT
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=6,
                spaceBefore=12,
                textColor=colors.darkblue
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )
            
            # Add content sections
            self._add_personal_info(story, cv_data.get('personal_info', {}), title_style, normal_style, language)
            self._add_professional_summary(story, cv_data.get('professional_summary', ''), heading_style, normal_style, language)
            self._add_experience(story, cv_data.get('experience', []), heading_style, normal_style, language)
            self._add_education(story, cv_data.get('education', []), heading_style, normal_style, language)
            self._add_skills(story, cv_data.get('skills', {}), heading_style, normal_style, language)
            self._add_certifications(story, cv_data.get('certifications', []), heading_style, normal_style, language)
            self._add_projects(story, cv_data.get('projects', []), heading_style, normal_style, language)
            
            # Build PDF
            doc.build(story)
            
            return {
                'success': True,
                'message': 'CV generated successfully using ReportLab'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"ReportLab CV generation failed: {str(e)}"
            }

    def _create_html_template(self, cv_data: Dict[str, Any], template_id: str, language: str) -> str:
        """Create HTML template for CV"""
        personal_info = cv_data.get('personal_info', {})
        
        html = f"""
        <!DOCTYPE html>
        <html lang="{language}" dir="{'rtl' if language == 'ar' else 'ltr'}">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CV - {personal_info.get('full_name', 'Professional Resume')}</title>
        </head>
        <body>
            <div class="cv-container">
                {self._generate_header_html(personal_info, language)}
                {self._generate_summary_html(cv_data.get('professional_summary', ''), language)}
                {self._generate_experience_html(cv_data.get('experience', []), language)}
                {self._generate_education_html(cv_data.get('education', []), language)}
                {self._generate_skills_html(cv_data.get('skills', {}), language)}
                {self._generate_certifications_html(cv_data.get('certifications', []), language)}
                {self._generate_projects_html(cv_data.get('projects', []), language)}
            </div>
        </body>
        </html>
        """
        
        return html

    def _create_css_styles(self, template_id: str, language: str) -> str:
        """Create CSS styles for CV template"""
        base_css = """
        @page {
            size: A4;
            margin: 1cm;
        }
        
        body {
            font-family: 'Arial', sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #333;
            margin: 0;
            padding: 0;
        }
        
        .cv-container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 15px;
        }
        
        .name {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .contact-info {
            font-size: 10px;
            color: #666;
        }
        
        .section {
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 3px;
            margin-bottom: 10px;
        }
        
        .experience-item, .education-item, .project-item {
            margin-bottom: 12px;
        }
        
        .item-title {
            font-weight: bold;
            color: #34495e;
        }
        
        .item-subtitle {
            font-style: italic;
            color: #666;
            font-size: 10px;
        }
        
        .item-description {
            margin-top: 5px;
            text-align: justify;
        }
        
        .skills-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .skill-category {
            margin-bottom: 8px;
        }
        
        .skill-category-title {
            font-weight: bold;
            color: #2c3e50;
            font-size: 11px;
        }
        
        .skill-list {
            font-size: 10px;
            color: #555;
        }
        """
        
        # Add template-specific styles
        if template_id == 'modern':
            base_css += """
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                border: none;
            }
            
            .name {
                color: white;
            }
            
            .contact-info {
                color: #f8f9fa;
            }
            
            .section-title {
                background: #667eea;
                color: white;
                padding: 8px 12px;
                border-radius: 5px;
                border: none;
            }
            """
        elif template_id == 'professional':
            base_css += """
            .header {
                background: #f8f9fa;
                border: 2px solid #dee2e6;
            }
            
            .section-title {
                background: #343a40;
                color: white;
                padding: 6px 10px;
                border: none;
            }
            """
        
        # Add RTL support for Arabic
        if language == 'ar':
            base_css += """
            body {
                direction: rtl;
                text-align: right;
            }
            
            .header {
                text-align: center;
            }
            """
        
        return base_css

    def _generate_header_html(self, personal_info: Dict[str, Any], language: str) -> str:
        """Generate header HTML section"""
        name = personal_info.get('full_name', '')
        email = personal_info.get('email', '')
        phone = personal_info.get('phone', '')
        address = personal_info.get('address', '')
        linkedin = personal_info.get('linkedin', '')
        website = personal_info.get('website', '')
        
        contact_parts = []
        if email:
            contact_parts.append(email)
        if phone:
            contact_parts.append(phone)
        if address:
            contact_parts.append(address)
        if linkedin:
            contact_parts.append(linkedin)
        if website:
            contact_parts.append(website)
        
        contact_info = ' | '.join(contact_parts)
        
        return f"""
        <div class="header">
            <div class="name">{name}</div>
            <div class="contact-info">{contact_info}</div>
        </div>
        """

    def _generate_summary_html(self, summary: str, language: str) -> str:
        """Generate professional summary HTML section"""
        if not summary:
            return ""
        
        title = "الملخص المهني" if language == 'ar' else "Professional Summary"
        
        return f"""
        <div class="section">
            <div class="section-title">{title}</div>
            <div class="item-description">{summary}</div>
        </div>
        """

    def _generate_experience_html(self, experience: List[Dict[str, Any]], language: str) -> str:
        """Generate experience HTML section"""
        if not experience:
            return ""
        
        title = "الخبرة المهنية" if language == 'ar' else "Professional Experience"
        
        html = f'<div class="section"><div class="section-title">{title}</div>'
        
        for exp in experience:
            job_title = exp.get('job_title', '')
            company = exp.get('company', '')
            location = exp.get('location', '')
            start_date = exp.get('start_date', '')
            end_date = exp.get('end_date', '') or ('الحالي' if language == 'ar' else 'Present')
            description = exp.get('description', '')
            
            html += f"""
            <div class="experience-item">
                <div class="item-title">{job_title}</div>
                <div class="item-subtitle">{company} | {location} | {start_date} - {end_date}</div>
                <div class="item-description">{description}</div>
            </div>
            """
        
        html += '</div>'
        return html

    def _generate_education_html(self, education: List[Dict[str, Any]], language: str) -> str:
        """Generate education HTML section"""
        if not education:
            return ""
        
        title = "التعليم" if language == 'ar' else "Education"
        
        html = f'<div class="section"><div class="section-title">{title}</div>'
        
        for edu in education:
            degree = edu.get('degree', '')
            institution = edu.get('institution', '')
            location = edu.get('location', '')
            graduation_date = edu.get('graduation_date', '')
            gpa = edu.get('gpa', '')
            
            gpa_text = f" | GPA: {gpa}" if gpa else ""
            
            html += f"""
            <div class="education-item">
                <div class="item-title">{degree}</div>
                <div class="item-subtitle">{institution} | {location} | {graduation_date}{gpa_text}</div>
            </div>
            """
        
        html += '</div>'
        return html

    def _generate_skills_html(self, skills: Dict[str, List[str]], language: str) -> str:
        """Generate skills HTML section"""
        if not skills:
            return ""
        
        title = "المهارات" if language == 'ar' else "Skills"
        
        html = f'<div class="section"><div class="section-title">{title}</div><div class="skills-grid">'
        
        skill_categories = {
            'technical': 'المهارات التقنية' if language == 'ar' else 'Technical Skills',
            'soft': 'المهارات الشخصية' if language == 'ar' else 'Soft Skills',
            'languages': 'اللغات' if language == 'ar' else 'Languages'
        }
        
        for category, skill_list in skills.items():
            if skill_list:
                category_title = skill_categories.get(category, category.title())
                skills_text = ', '.join(skill_list)
                
                html += f"""
                <div class="skill-category">
                    <div class="skill-category-title">{category_title}</div>
                    <div class="skill-list">{skills_text}</div>
                </div>
                """
        
        html += '</div></div>'
        return html

    def _generate_certifications_html(self, certifications: List[Dict[str, Any]], language: str) -> str:
        """Generate certifications HTML section"""
        if not certifications:
            return ""
        
        title = "الشهادات" if language == 'ar' else "Certifications"
        
        html = f'<div class="section"><div class="section-title">{title}</div>'
        
        for cert in certifications:
            name = cert.get('name', '')
            issuer = cert.get('issuer', '')
            date = cert.get('date', '')
            credential_id = cert.get('credential_id', '')
            
            credential_text = f" | ID: {credential_id}" if credential_id else ""
            
            html += f"""
            <div class="education-item">
                <div class="item-title">{name}</div>
                <div class="item-subtitle">{issuer} | {date}{credential_text}</div>
            </div>
            """
        
        html += '</div>'
        return html

    def _generate_projects_html(self, projects: List[Dict[str, Any]], language: str) -> str:
        """Generate projects HTML section"""
        if not projects:
            return ""
        
        title = "المشاريع" if language == 'ar' else "Projects"
        
        html = f'<div class="section"><div class="section-title">{title}</div>'
        
        for project in projects:
            name = project.get('name', '')
            description = project.get('description', '')
            technologies = project.get('technologies', [])
            url = project.get('url', '')
            
            tech_text = f"Technologies: {', '.join(technologies)}" if technologies else ""
            url_text = f" | URL: {url}" if url else ""
            
            html += f"""
            <div class="project-item">
                <div class="item-title">{name}</div>
                <div class="item-subtitle">{tech_text}{url_text}</div>
                <div class="item-description">{description}</div>
            </div>
            """
        
        html += '</div>'
        return html

    def check_ats_compliance(self, cv_data: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Check ATS compliance of generated CV"""
        issues = []
        compliant = True
        
        try:
            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.ats_rules['max_file_size_mb']:
                issues.append(f"File size ({file_size_mb:.1f}MB) exceeds recommended {self.ats_rules['max_file_size_mb']}MB")
                compliant = False
            
            # Check for required sections
            required_sections = ['personal_info', 'experience', 'education', 'skills']
            for section in required_sections:
                if not cv_data.get(section):
                    issues.append(f"Missing required section: {section}")
                    compliant = False
            
            # Check personal info completeness
            personal_info = cv_data.get('personal_info', {})
            required_personal_fields = ['full_name', 'email', 'phone']
            for field in required_personal_fields:
                if not personal_info.get(field):
                    issues.append(f"Missing required personal information: {field}")
                    compliant = False
            
            # Check experience details
            experience = cv_data.get('experience', [])
            for i, exp in enumerate(experience):
                required_exp_fields = ['job_title', 'company', 'start_date']
                for field in required_exp_fields:
                    if not exp.get(field):
                        issues.append(f"Experience entry {i+1} missing: {field}")
                        compliant = False
            
            return {
                'compliant': compliant,
                'issues': issues,
                'score': max(0, 100 - len(issues) * 10)  # Scoring system
            }
            
        except Exception as e:
            return {
                'compliant': False,
                'issues': [f"Error checking compliance: {str(e)}"],
                'score': 0
            }

    def get_sample_cv_data(self, language: str = 'en') -> Dict[str, Any]:
        """Get sample CV data for testing and demonstration"""
        if language == 'ar':
            return {
                'personal_info': {
                    'full_name': 'أحمد محمد علي',
                    'email': 'ahmed.ali@email.com',
                    'phone': '+966 50 123 4567',
                    'address': 'الرياض، المملكة العربية السعودية',
                    'linkedin': 'linkedin.com/in/ahmed-ali',
                    'website': 'www.ahmed-portfolio.com',
                    'photo_url': ''
                },
                'professional_summary': 'مطور برمجيات متمرس مع أكثر من 5 سنوات من الخبرة في تطوير تطبيقات الويب والهاتف المحمول. خبرة واسعة في JavaScript وPython وReact. شغوف بالتكنولوجيا الحديثة وحل المشاكل المعقدة.',
                'experience': [
                    {
                        'job_title': 'مطور برمجيات أول',
                        'company': 'شركة التقنية المتقدمة',
                        'location': 'الرياض، السعودية',
                        'start_date': '2021-01',
                        'end_date': '',
                        'current': True,
                        'description': 'قيادة فريق من 3 مطورين في تطوير تطبيقات ويب متقدمة. تطوير واجهات برمجة التطبيقات وقواعد البيانات. تحسين أداء التطبيقات بنسبة 40%.'
                    }
                ],
                'education': [
                    {
                        'degree': 'بكالوريوس علوم الحاسب',
                        'institution': 'جامعة الملك سعود',
                        'location': 'الرياض، السعودية',
                        'graduation_date': '2019-06',
                        'gpa': '3.8'
                    }
                ],
                'skills': {
                    'technical': ['JavaScript', 'Python', 'React', 'Node.js', 'SQL'],
                    'soft': ['القيادة', 'التواصل', 'حل المشاكل'],
                    'languages': ['العربية (الأم)', 'الإنجليزية (متقدم)']
                },
                'certifications': [
                    {
                        'name': 'AWS Certified Developer',
                        'issuer': 'Amazon Web Services',
                        'date': '2022-03',
                        'credential_id': 'AWS-123456'
                    }
                ],
                'projects': [
                    {
                        'name': 'منصة التجارة الإلكترونية',
                        'description': 'تطوير منصة تجارة إلكترونية شاملة باستخدام React وNode.js',
                        'technologies': ['React', 'Node.js', 'MongoDB'],
                        'url': 'https://github.com/ahmed/ecommerce'
                    }
                ]
            }
        else:
            return {
                'personal_info': {
                    'full_name': 'John Smith',
                    'email': 'john.smith@email.com',
                    'phone': '+1 (555) 123-4567',
                    'address': 'New York, NY, USA',
                    'linkedin': 'linkedin.com/in/johnsmith',
                    'website': 'www.johnsmith-portfolio.com',
                    'photo_url': ''
                },
                'professional_summary': 'Experienced software developer with 5+ years of expertise in web and mobile application development. Proficient in JavaScript, Python, and React. Passionate about modern technology and solving complex problems.',
                'experience': [
                    {
                        'job_title': 'Senior Software Developer',
                        'company': 'Tech Solutions Inc.',
                        'location': 'New York, NY',
                        'start_date': '2021-01',
                        'end_date': '',
                        'current': True,
                        'description': 'Lead a team of 3 developers in building advanced web applications. Develop APIs and database systems. Improved application performance by 40%.'
                    },
                    {
                        'job_title': 'Software Developer',
                        'company': 'StartupXYZ',
                        'location': 'San Francisco, CA',
                        'start_date': '2019-06',
                        'end_date': '2020-12',
                        'current': False,
                        'description': 'Developed responsive web applications using React and Node.js. Collaborated with design team to implement user-friendly interfaces.'
                    }
                ],
                'education': [
                    {
                        'degree': 'Bachelor of Science in Computer Science',
                        'institution': 'University of California, Berkeley',
                        'location': 'Berkeley, CA',
                        'graduation_date': '2019-05',
                        'gpa': '3.8'
                    }
                ],
                'skills': {
                    'technical': ['JavaScript', 'Python', 'React', 'Node.js', 'SQL', 'AWS'],
                    'soft': ['Leadership', 'Communication', 'Problem Solving', 'Team Collaboration'],
                    'languages': ['English (Native)', 'Spanish (Intermediate)']
                },
                'certifications': [
                    {
                        'name': 'AWS Certified Developer',
                        'issuer': 'Amazon Web Services',
                        'date': '2022-03',
                        'credential_id': 'AWS-123456'
                    },
                    {
                        'name': 'React Developer Certification',
                        'issuer': 'Meta',
                        'date': '2021-11',
                        'credential_id': 'META-789012'
                    }
                ],
                'projects': [
                    {
                        'name': 'E-commerce Platform',
                        'description': 'Built a full-stack e-commerce platform with React frontend and Node.js backend, supporting payment processing and inventory management.',
                        'technologies': ['React', 'Node.js', 'MongoDB', 'Stripe API'],
                        'url': 'https://github.com/johnsmith/ecommerce-platform'
                    },
                    {
                        'name': 'Task Management App',
                        'description': 'Developed a collaborative task management application with real-time updates and team collaboration features.',
                        'technologies': ['Vue.js', 'Express.js', 'Socket.io', 'PostgreSQL'],
                        'url': 'https://github.com/johnsmith/task-manager'
                    }
                ]
            }

    # ReportLab helper methods for simple PDF generation
    def _add_personal_info(self, story, personal_info, title_style, normal_style, language):
        """Add personal information section to ReportLab story"""
        name = personal_info.get('full_name', '')
        if name:
            story.append(Paragraph(name, title_style))
        
        contact_parts = []
        for field in ['email', 'phone', 'address', 'linkedin', 'website']:
            if personal_info.get(field):
                contact_parts.append(personal_info[field])
        
        if contact_parts:
            story.append(Paragraph(' | '.join(contact_parts), normal_style))
        
        story.append(Spacer(1, 12))

    def _add_professional_summary(self, story, summary, heading_style, normal_style, language):
        """Add professional summary section to ReportLab story"""
        if summary:
            title = "الملخص المهني" if language == 'ar' else "Professional Summary"
            story.append(Paragraph(title, heading_style))
            story.append(Paragraph(summary, normal_style))

    def _add_experience(self, story, experience, heading_style, normal_style, language):
        """Add experience section to ReportLab story"""
        if experience:
            title = "الخبرة المهنية" if language == 'ar' else "Professional Experience"
            story.append(Paragraph(title, heading_style))
            
            for exp in experience:
                job_title = exp.get('job_title', '')
                company = exp.get('company', '')
                location = exp.get('location', '')
                start_date = exp.get('start_date', '')
                end_date = exp.get('end_date', '') or ('الحالي' if language == 'ar' else 'Present')
                description = exp.get('description', '')
                
                story.append(Paragraph(f"<b>{job_title}</b>", normal_style))
                story.append(Paragraph(f"{company} | {location} | {start_date} - {end_date}", normal_style))
                if description:
                    story.append(Paragraph(description, normal_style))
                story.append(Spacer(1, 6))

    def _add_education(self, story, education, heading_style, normal_style, language):
        """Add education section to ReportLab story"""
        if education:
            title = "التعليم" if language == 'ar' else "Education"
            story.append(Paragraph(title, heading_style))
            
            for edu in education:
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                location = edu.get('location', '')
                graduation_date = edu.get('graduation_date', '')
                gpa = edu.get('gpa', '')
                
                story.append(Paragraph(f"<b>{degree}</b>", normal_style))
                gpa_text = f" | GPA: {gpa}" if gpa else ""
                story.append(Paragraph(f"{institution} | {location} | {graduation_date}{gpa_text}", normal_style))
                story.append(Spacer(1, 6))

    def _add_skills(self, story, skills, heading_style, normal_style, language):
        """Add skills section to ReportLab story"""
        if skills:
            title = "المهارات" if language == 'ar' else "Skills"
            story.append(Paragraph(title, heading_style))
            
            skill_categories = {
                'technical': 'المهارات التقنية' if language == 'ar' else 'Technical Skills',
                'soft': 'المهارات الشخصية' if language == 'ar' else 'Soft Skills',
                'languages': 'اللغات' if language == 'ar' else 'Languages'
            }
            
            for category, skill_list in skills.items():
                if skill_list:
                    category_title = skill_categories.get(category, category.title())
                    skills_text = ', '.join(skill_list)
                    story.append(Paragraph(f"<b>{category_title}:</b> {skills_text}", normal_style))

    def _add_certifications(self, story, certifications, heading_style, normal_style, language):
        """Add certifications section to ReportLab story"""
        if certifications:
            title = "الشهادات" if language == 'ar' else "Certifications"
            story.append(Paragraph(title, heading_style))
            
            for cert in certifications:
                name = cert.get('name', '')
                issuer = cert.get('issuer', '')
                date = cert.get('date', '')
                credential_id = cert.get('credential_id', '')
                
                story.append(Paragraph(f"<b>{name}</b>", normal_style))
                credential_text = f" | ID: {credential_id}" if credential_id else ""
                story.append(Paragraph(f"{issuer} | {date}{credential_text}", normal_style))
                story.append(Spacer(1, 6))

    def _add_projects(self, story, projects, heading_style, normal_style, language):
        """Add projects section to ReportLab story"""
        if projects:
            title = "المشاريع" if language == 'ar' else "Projects"
            story.append(Paragraph(title, heading_style))
            
            for project in projects:
                name = project.get('name', '')
                description = project.get('description', '')
                technologies = project.get('technologies', [])
                url = project.get('url', '')
                
                story.append(Paragraph(f"<b>{name}</b>", normal_style))
                if technologies:
                    tech_text = f"Technologies: {', '.join(technologies)}"
                    story.append(Paragraph(tech_text, normal_style))
                if description:
                    story.append(Paragraph(description, normal_style))
                if url:
                    story.append(Paragraph(f"URL: {url}", normal_style))
                story.append(Spacer(1, 6))

