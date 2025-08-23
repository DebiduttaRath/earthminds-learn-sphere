import openai
from typing import List, Dict, Any, Optional
from config import settings
from utils.prompts import get_tutor_prompt, get_quiz_generation_prompt, get_grading_prompt
import logging

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = settings.openai_api_key


class AIService:
    """AI service for tutoring, quiz generation, and grading"""
    
    def __init__(self):
        self.model = settings.openai_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    async def generate_tutor_response(
        self,
        student_message: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate AI tutor response with context"""
        try:
            # Prepare context from retrieved documents
            context = "\n\n".join([
                f"Document: {doc.get('title', 'Unknown')}\n{doc.get('content', '')}"
                for doc in context_documents
            ])
            
            # Get tutor prompt
            system_prompt = get_tutor_prompt(
                context=context,
                student_profile=student_profile
            )
            
            # Prepare conversation
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append(msg)
            
            # Add current student message
            messages.append({"role": "user", "content": student_message})
            
            # Generate response
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            assistant_message = response.choices[0].message.content
            
            return {
                "response": assistant_message,
                "context_used": len(context_documents),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error generating tutor response: {e}")
            return {
                "response": "I apologize, but I'm having trouble processing your question right now. Please try again.",
                "error": str(e)
            }
    
    async def generate_quiz(
        self,
        topic: str,
        subject: str,
        grade_level: str,
        difficulty: str,
        num_questions: int,
        context_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate quiz questions based on topic and context"""
        try:
            # Prepare context
            context = "\n\n".join([
                f"Document: {doc.get('title', 'Unknown')}\n{doc.get('content', '')}"
                for doc in context_documents
            ])
            
            prompt = get_quiz_generation_prompt(
                topic=topic,
                subject=subject,
                grade_level=grade_level,
                difficulty=difficulty,
                num_questions=num_questions,
                context=context
            )
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for more consistent quiz generation
            )
            
            # Parse the response (expecting JSON format)
            import json
            quiz_data = json.loads(response.choices[0].message.content)
            
            return {
                "quiz_data": quiz_data,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return {
                "error": str(e),
                "quiz_data": None
            }
    
    async def grade_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_type: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Grade student answer using AI"""
        try:
            prompt = get_grading_prompt(
                question=question,
                student_answer=student_answer,
                correct_answer=correct_answer,
                question_type=question_type,
                context=context
            )
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2  # Lower temperature for consistent grading
            )
            
            # Parse grading response
            import json
            grading_result = json.loads(response.choices[0].message.content)
            
            return {
                "score": grading_result.get("score", 0),
                "feedback": grading_result.get("feedback", ""),
                "explanation": grading_result.get("explanation", ""),
                "is_correct": grading_result.get("is_correct", False),
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error grading answer: {e}")
            return {
                "score": 0,
                "feedback": "Unable to grade this answer automatically. Please review manually.",
                "error": str(e)
            }
    
    async def analyze_student_performance(
        self,
        quiz_attempts: List[Dict[str, Any]],
        student_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze student performance and provide learning recommendations"""
        try:
            # Prepare performance data summary
            performance_summary = {
                "total_attempts": len(quiz_attempts),
                "average_score": sum(attempt.get("score", 0) for attempt in quiz_attempts) / len(quiz_attempts) if quiz_attempts else 0,
                "subjects": list(set(attempt.get("subject") for attempt in quiz_attempts)),
                "strengths": [],
                "weaknesses": []
            }
            
            prompt = f"""
            Analyze the following student performance data and provide learning recommendations:
            
            Performance Summary: {performance_summary}
            Student Profile: {student_profile or 'No profile available'}
            
            Provide recommendations in Indian English that are:
            1. Encouraging and supportive
            2. Specific and actionable
            3. Aligned with Indian educational standards
            4. Culturally appropriate
            
            Format your response as JSON with keys: recommendations, strengths, areas_for_improvement, next_steps
            """
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.5
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing student performance: {e}")
            return {
                "error": str(e),
                "recommendations": ["Continue practicing regularly to improve your performance."]
            }


# Global AI service instance
ai_service = AIService()
