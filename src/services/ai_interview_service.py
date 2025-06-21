import os
import openai
import json
import random
from typing import Dict, List, Any

class AIInterviewService:
    def __init__(self):
        # In production, this would be set via environment variable
        # For demo purposes, we'll use a placeholder
        self.openai_api_key = os.getenv('OPENAI_API_KEY', 'your-openai-api-key-here')
        if self.openai_api_key != 'your-openai-api-key-here':
            openai.api_key = self.openai_api_key
        
        # Question templates for different majors
        self.question_templates = {
            'it': {
                'en': [
                    "Tell me about your experience with programming languages.",
                    "How do you approach debugging a complex software issue?",
                    "Describe a challenging project you've worked on and how you overcame obstacles.",
                    "What's your experience with database design and optimization?",
                    "How do you stay updated with the latest technology trends?",
                    "Explain the difference between object-oriented and functional programming.",
                    "How would you handle a situation where your code is not performing as expected?",
                    "Describe your experience with version control systems like Git.",
                    "What methodologies do you prefer for software development and why?",
                    "How do you ensure code quality and maintainability?"
                ],
                'ar': [
                    "أخبرني عن خبرتك في لغات البرمجة.",
                    "كيف تتعامل مع تصحيح مشكلة برمجية معقدة؟",
                    "صف مشروعاً صعباً عملت عليه وكيف تغلبت على العقبات.",
                    "ما هي خبرتك في تصميم وتحسين قواعد البيانات؟",
                    "كيف تبقى محدثاً بأحدث اتجاهات التكنولوجيا؟",
                    "اشرح الفرق بين البرمجة الكائنية والبرمجة الوظيفية.",
                    "كيف تتعامل مع موقف لا يعمل فيه الكود كما هو متوقع؟",
                    "صف خبرتك مع أنظمة التحكم في الإصدارات مثل Git.",
                    "ما هي المنهجيات التي تفضلها لتطوير البرمجيات ولماذا؟",
                    "كيف تضمن جودة الكود وقابليته للصيانة؟"
                ]
            },
            'business': {
                'en': [
                    "Tell me about your leadership experience.",
                    "How do you handle conflict resolution in a team?",
                    "Describe a time when you had to make a difficult business decision.",
                    "What's your approach to strategic planning?",
                    "How do you motivate underperforming team members?",
                    "Explain your experience with budget management.",
                    "How do you stay informed about market trends?",
                    "Describe a successful project you led from start to finish.",
                    "What's your approach to risk management?",
                    "How do you measure success in business operations?"
                ],
                'ar': [
                    "أخبرني عن خبرتك في القيادة.",
                    "كيف تتعامل مع حل النزاعات في الفريق؟",
                    "صف وقتاً اضطررت فيه لاتخاذ قرار تجاري صعب.",
                    "ما هو نهجك في التخطيط الاستراتيجي؟",
                    "كيف تحفز أعضاء الفريق ضعيفي الأداء؟",
                    "اشرح خبرتك في إدارة الميزانية.",
                    "كيف تبقى مطلعاً على اتجاهات السوق؟",
                    "صف مشروعاً ناجحاً قدته من البداية إلى النهاية.",
                    "ما هو نهجك في إدارة المخاطر؟",
                    "كيف تقيس النجاح في العمليات التجارية؟"
                ]
            },
            'engineering': {
                'en': [
                    "Describe your experience with engineering design principles.",
                    "How do you approach problem-solving in engineering projects?",
                    "Tell me about a time you had to work within strict safety regulations.",
                    "What's your experience with CAD software and technical drawings?",
                    "How do you ensure quality control in your engineering work?",
                    "Describe a challenging technical problem you solved.",
                    "What's your approach to project management in engineering?",
                    "How do you stay updated with engineering standards and codes?",
                    "Explain your experience with testing and validation procedures.",
                    "How do you handle budget constraints in engineering projects?"
                ],
                'ar': [
                    "صف خبرتك في مبادئ التصميم الهندسي.",
                    "كيف تتعامل مع حل المشاكل في المشاريع الهندسية؟",
                    "أخبرني عن وقت اضطررت فيه للعمل ضمن لوائح أمان صارمة.",
                    "ما هي خبرتك مع برامج CAD والرسوم التقنية؟",
                    "كيف تضمن مراقبة الجودة في عملك الهندسي؟",
                    "صف مشكلة تقنية صعبة حللتها.",
                    "ما هو نهجك في إدارة المشاريع الهندسية؟",
                    "كيف تبقى محدثاً بالمعايير والأكواد الهندسية؟",
                    "اشرح خبرتك في إجراءات الاختبار والتحقق.",
                    "كيف تتعامل مع قيود الميزانية في المشاريع الهندسية؟"
                ]
            },
            'medicine': {
                'en': [
                    "Describe your clinical experience and patient care approach.",
                    "How do you handle high-pressure medical situations?",
                    "Tell me about a challenging case you've encountered.",
                    "What's your approach to continuing medical education?",
                    "How do you communicate complex medical information to patients?",
                    "Describe your experience with medical technology and equipment.",
                    "How do you ensure patient safety and quality care?",
                    "What's your approach to working in multidisciplinary teams?",
                    "How do you handle ethical dilemmas in medical practice?",
                    "Describe your experience with medical research or evidence-based practice."
                ],
                'ar': [
                    "صف خبرتك السريرية ونهجك في رعاية المرضى.",
                    "كيف تتعامل مع المواقف الطبية عالية الضغط؟",
                    "أخبرني عن حالة صعبة واجهتها.",
                    "ما هو نهجك في التعليم الطبي المستمر؟",
                    "كيف تتواصل مع المرضى حول المعلومات الطبية المعقدة؟",
                    "صف خبرتك مع التكنولوجيا والمعدات الطبية.",
                    "كيف تضمن سلامة المرضى وجودة الرعاية؟",
                    "ما هو نهجك في العمل ضمن فرق متعددة التخصصات؟",
                    "كيف تتعامل مع المعضلات الأخلاقية في الممارسة الطبية؟",
                    "صف خبرتك في البحث الطبي أو الممارسة القائمة على الأدلة."
                ]
            },
            'pharmacy': {
                'en': [
                    "Describe your experience with pharmaceutical care and patient counseling.",
                    "How do you ensure medication safety and prevent drug interactions?",
                    "Tell me about your knowledge of pharmacokinetics and pharmacodynamics.",
                    "What's your approach to staying updated with new medications?",
                    "How do you handle prescription verification and quality control?",
                    "Describe your experience with clinical pharmacy services.",
                    "How do you communicate with healthcare providers about drug therapy?",
                    "What's your approach to managing pharmacy operations?",
                    "How do you handle adverse drug reaction reporting?",
                    "Describe your experience with pharmaceutical regulations and compliance."
                ],
                'ar': [
                    "صف خبرتك في الرعاية الصيدلانية وإرشاد المرضى.",
                    "كيف تضمن سلامة الأدوية وتمنع التفاعلات الدوائية؟",
                    "أخبرني عن معرفتك بالحرائك الدوائية والديناميكا الدوائية.",
                    "ما هو نهجك في البقاء محدثاً بالأدوية الجديدة؟",
                    "كيف تتعامل مع التحقق من الوصفات ومراقبة الجودة؟",
                    "صف خبرتك في خدمات الصيدلة السريرية.",
                    "كيف تتواصل مع مقدمي الرعاية الصحية حول العلاج الدوائي؟",
                    "ما هو نهجك في إدارة عمليات الصيدلية؟",
                    "كيف تتعامل مع الإبلاغ عن ردود الفعل السلبية للأدوية؟",
                    "صف خبرتك في اللوائح الصيدلانية والامتثال."
                ]
            },
            'law': {
                'en': [
                    "Describe your experience with legal research and case analysis.",
                    "How do you approach client consultation and legal advice?",
                    "Tell me about a complex legal case you've worked on.",
                    "What's your experience with courtroom procedures and litigation?",
                    "How do you stay updated with changes in legislation?",
                    "Describe your approach to contract drafting and review.",
                    "How do you handle ethical considerations in legal practice?",
                    "What's your experience with alternative dispute resolution?",
                    "How do you manage multiple cases and deadlines?",
                    "Describe your experience with legal documentation and filing."
                ],
                'ar': [
                    "صف خبرتك في البحث القانوني وتحليل القضايا.",
                    "كيف تتعامل مع استشارة العملاء والمشورة القانونية؟",
                    "أخبرني عن قضية قانونية معقدة عملت عليها.",
                    "ما هي خبرتك في إجراءات المحكمة والتقاضي؟",
                    "كيف تبقى محدثاً بالتغييرات في التشريع؟",
                    "صف نهجك في صياغة ومراجعة العقود.",
                    "كيف تتعامل مع الاعتبارات الأخلاقية في الممارسة القانونية؟",
                    "ما هي خبرتك في الوسائل البديلة لحل النزاعات؟",
                    "كيف تدير قضايا ومواعيد نهائية متعددة؟",
                    "صف خبرتك في التوثيق والإيداع القانوني."
                ]
            }
        }

    def generate_questions(self, major: str, language: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate interview questions for a specific major and language"""
        try:
            if major.lower() in self.question_templates and language in self.question_templates[major.lower()]:
                available_questions = self.question_templates[major.lower()][language]
                selected_questions = random.sample(available_questions, min(num_questions, len(available_questions)))
                
                questions = []
                for i, question_text in enumerate(selected_questions):
                    questions.append({
                        'question_text': question_text,
                        'question_language': language,
                        'ai_generated': True,
                        'order_in_interview': i + 1
                    })
                
                return questions
            else:
                # Fallback to generic questions if major not found
                return self._generate_generic_questions(language, num_questions)
                
        except Exception as e:
            print(f"Error generating questions: {e}")
            return self._generate_generic_questions(language, num_questions)

    def _generate_generic_questions(self, language: str, num_questions: int) -> List[Dict[str, Any]]:
        """Generate generic interview questions as fallback"""
        generic_questions = {
            'en': [
                "Tell me about yourself and your background.",
                "What are your greatest strengths?",
                "What are your areas for improvement?",
                "Why are you interested in this field?",
                "Where do you see yourself in 5 years?",
                "Describe a challenge you've overcome.",
                "What motivates you in your work?",
                "How do you handle stress and pressure?",
                "What are your career goals?",
                "Why should we hire you?"
            ],
            'ar': [
                "أخبرني عن نفسك وخلفيتك.",
                "ما هي نقاط قوتك الأعظم؟",
                "ما هي مجالات التحسين لديك؟",
                "لماذا أنت مهتم بهذا المجال؟",
                "أين ترى نفسك خلال 5 سنوات؟",
                "صف تحدياً تغلبت عليه.",
                "ما الذي يحفزك في عملك؟",
                "كيف تتعامل مع التوتر والضغط؟",
                "ما هي أهدافك المهنية؟",
                "لماذا يجب أن نوظفك؟"
            ]
        }
        
        available_questions = generic_questions.get(language, generic_questions['en'])
        selected_questions = random.sample(available_questions, min(num_questions, len(available_questions)))
        
        questions = []
        for i, question_text in enumerate(selected_questions):
            questions.append({
                'question_text': question_text,
                'question_language': language,
                'ai_generated': True,
                'order_in_interview': i + 1
            })
        
        return questions

    def analyze_response(self, question: str, response: str, language: str) -> Dict[str, Any]:
        """Analyze user response and provide feedback"""
        try:
            # If OpenAI API key is available, use it for advanced analysis
            if self.openai_api_key != 'your-openai-api-key-here':
                return self._analyze_with_openai(question, response, language)
            else:
                return self._analyze_basic(question, response, language)
        except Exception as e:
            print(f"Error analyzing response: {e}")
            return self._analyze_basic(question, response, language)

    def _analyze_with_openai(self, question: str, response: str, language: str) -> Dict[str, Any]:
        """Advanced analysis using OpenAI API"""
        try:
            prompt = f"""
            Analyze this interview response and provide feedback:
            
            Question: {question}
            Response: {response}
            Language: {language}
            
            Please provide:
            1. Overall feedback (in {language})
            2. Clarity score (1-5)
            3. Relevance score (1-5)
            4. Sentiment score (1-5, where 5 is most positive/confident)
            
            Format your response as JSON with keys: feedback, clarity_score, relevance_score, sentiment_score
            """
            
            response_obj = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            result = json.loads(response_obj.choices[0].message.content)
            return {
                'ai_feedback_text': result.get('feedback', 'Good response!'),
                'clarity_score': float(result.get('clarity_score', 3.5)),
                'relevance_score': float(result.get('relevance_score', 3.5)),
                'sentiment_score': float(result.get('sentiment_score', 3.5))
            }
        except Exception as e:
            print(f"OpenAI analysis failed: {e}")
            return self._analyze_basic(question, response, language)

    def _analyze_basic(self, question: str, response: str, language: str) -> Dict[str, Any]:
        """Basic analysis without external API"""
        response_length = len(response.split())
        
        # Basic scoring based on response characteristics
        clarity_score = min(5.0, max(1.0, response_length / 20))  # Based on length
        relevance_score = 4.0 if len(response) > 50 else 2.5  # Basic relevance check
        sentiment_score = 3.5  # Neutral sentiment as default
        
        # Generate feedback based on language
        if language == 'ar':
            if response_length < 10:
                feedback = "الإجابة قصيرة جداً. حاول تقديم المزيد من التفاصيل والأمثلة."
            elif response_length > 100:
                feedback = "إجابة شاملة! حاول التركيز على النقاط الأساسية لتكون أكثر إيجازاً."
            else:
                feedback = "إجابة جيدة! تحتوي على تفاصيل مناسبة ومفهومة."
        else:
            if response_length < 10:
                feedback = "Your response is quite brief. Try to provide more details and examples."
            elif response_length > 100:
                feedback = "Comprehensive answer! Try to focus on key points to be more concise."
            else:
                feedback = "Good response! Contains appropriate details and is well-structured."
        
        return {
            'ai_feedback_text': feedback,
            'clarity_score': clarity_score,
            'relevance_score': relevance_score,
            'sentiment_score': sentiment_score
        }

    def generate_interview_report(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive interview report"""
        questions = interview_data.get('questions', [])
        overall_scores = []
        
        # Calculate overall performance
        for question in questions:
            if question.get('responses'):
                response = question['responses'][0]
                clarity = response.get('clarity_score', 0)
                relevance = response.get('relevance_score', 0)
                sentiment = response.get('sentiment_score', 0)
                overall_scores.append((clarity + relevance + sentiment) / 3)
        
        overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
        
        # Generate strengths and areas for improvement
        language = interview_data.get('language', 'en')
        
        if language == 'ar':
            strengths = [
                "إجابات واضحة ومفهومة",
                "ثقة في التعبير",
                "استخدام أمثلة مناسبة"
            ]
            areas_for_improvement = [
                "تطوير الإجابات بمزيد من التفاصيل",
                "تحسين التنظيم في الإجابات",
                "زيادة الثقة في التعبير"
            ]
        else:
            strengths = [
                "Clear and articulate responses",
                "Confident delivery",
                "Good use of examples"
            ]
            areas_for_improvement = [
                "Develop responses with more detail",
                "Improve organization of answers",
                "Increase confidence in delivery"
            ]
        
        return {
            'summary': {
                'overall_score': overall_score,
                'strengths': strengths[:2],  # Top 2 strengths
                'areas_for_improvement': areas_for_improvement[:2]  # Top 2 areas
            },
            'questions': questions
        }

