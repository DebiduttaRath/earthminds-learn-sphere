from typing import List, Dict, Any, Optional
import logging
import json

from openai import AsyncOpenAI
from config import settings
from utils.prompts import (
    get_tutor_prompt,
    get_quiz_generation_prompt,
    get_grading_prompt,
)

logger = logging.getLogger(__name__)


class AIService:
    """AI service for tutoring, quiz generation, and grading (OpenAI ≥ 1.x)"""

    def __init__(self):
        self.model = settings.openai_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        # Async client (non-blocking inside FastAPI async routes)
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_tutor_response(
        self,
        student_message: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate AI tutor response with context"""
        try:
            context = "\n\n".join(
                [
                    f"Document: {doc.get('title', 'Unknown')}\n{doc.get('content', '')}"
                    for doc in context_documents
                ]
            )

            system_prompt = get_tutor_prompt(
                context=context,
                student_profile=student_profile,
            )

            messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history[-10:])  # last 10 messages
            messages.append({"role": "user", "content": student_message})

            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            assistant_message = resp.choices[0].message.content or ""
            tokens_used = (resp.usage.total_tokens if resp.usage else None)

            return {
                "response": assistant_message,
                "context_used": len(context_documents),
                "tokens_used": tokens_used,
            }

        except Exception as e:
            logger.exception("Error generating tutor response")
            return {
                "response": "I’m having trouble processing your question right now. Please try again.",
                "error": str(e),
            }

    async def generate_quiz(
        self,
        topic: str,
        subject: str,
        grade_level: str,
        difficulty: str,
        num_questions: int,
        context_documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate quiz questions based on topic and context"""
        try:
            context = "\n\n".join(
                [
                    f"Document: {doc.get('title', 'Unknown')}\n{doc.get('content', '')}"
                    for doc in context_documents
                ]
            )

            prompt = get_quiz_generation_prompt(
                topic=topic,
                subject=subject,
                grade_level=grade_level,
                difficulty=difficulty,
                num_questions=num_questions,
                context=context,
            )

            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.3,
            )

            raw = resp.choices[0].message.content or "{}"
            try:
                quiz_data = json.loads(raw)
            except json.JSONDecodeError:
                # If the model returns fenced code or extra text, try to salvage JSON
                quiz_data = json.loads(raw.strip().strip("`").strip())

            tokens_used = (resp.usage.total_tokens if resp.usage else None)
            return {"quiz_data": quiz_data, "tokens_used": tokens_used}

        except Exception as e:
            logger.exception("Error generating quiz")
            return {"error": str(e), "quiz_data": None}

    async def grade_answer(
        self,
        question: str,
        student_answer: str,
        correct_answer: str,
        question_type: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Grade student answer using AI"""
        try:
            prompt = get_grading_prompt(
                question=question,
                student_answer=student_answer,
                correct_answer=correct_answer,
                question_type=question_type,
                context=context,
            )

            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2,
            )

            raw = resp.choices[0].message.content or "{}"
            try:
                grading_result = json.loads(raw)
            except json.JSONDecodeError:
                grading_result = json.loads(raw.strip().strip("`").strip())

            tokens_used = (resp.usage.total_tokens if resp.usage else None)
            return {
                "score": grading_result.get("score", 0),
                "feedback": grading_result.get("feedback", ""),
                "explanation": grading_result.get("explanation", ""),
                "is_correct": grading_result.get("is_correct", False),
                "tokens_used": tokens_used,
            }

        except Exception as e:
            logger.exception("Error grading answer")
            return {
                "score": 0,
                "feedback": "Unable to grade this answer automatically. Please review manually.",
                "error": str(e),
            }


# Global AI service instance
ai_service = AIService()
