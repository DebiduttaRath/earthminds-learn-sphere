# ai_service.py  (replace your current file with this)
from typing import List, Dict, Any, Optional
import logging
import json

from config import settings
from utils.prompts import (
    get_tutor_prompt,
    get_quiz_generation_prompt,
    get_grading_prompt,
)

from ai_providers import OpenAIProvider, GrokProvider, RateLimitError, APIError

logger = logging.getLogger(__name__)

class AIService:
    """AI service with separate implementations for OpenAI and Grok (xAI)."""

    def __init__(self):
        # Config
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature

        # Models
        self.oa_model = getattr(settings, "openai_model", "gpt-4o-mini")
        self.grok_model = getattr(settings, "xai_model", "grok-4")

        # Provider order e.g. ["openai","grok"] or ["grok","openai"]
        order = getattr(settings, "provider_order", "openai,grok")
        self.provider_order = [p.strip().lower() for p in order.split(",") if p.strip()]

        # Separate provider instances
        self.openai = OpenAIProvider(api_key=getattr(settings, "openai_api_key", None))
        self.grok = GrokProvider(
            api_key=getattr(settings, "xai_api_key", None),
            base_url=getattr(settings, "xai_base_url", "https://api.x.ai/v1"),
        )

    async def _run_chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        last_err: Optional[Exception] = None

        for provider in self.provider_order:
            try:
                if provider == "openai":
                    result = await self.openai.chat(
                        messages=messages,
                        model=self.oa_model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                elif provider in ("grok", "xai", "xai_grok"):
                    result = await self.grok.chat(
                        messages=messages,
                        model=self.grok_model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                else:
                    raise ValueError(f"Unknown provider '{provider}'")

                return {
                    "response": result.text,
                    "tokens_used": result.tokens_used,
                    "provider": result.provider,
                    "model": result.model,
                }

            except (RateLimitError, APIError) as e:
                # Try next provider on quota/5xx-type errors
                logger.warning("Provider '%s' API error, trying next: %s", provider, e)
                last_err = e
                continue
            except Exception as e:
                logger.warning("Provider '%s' general error, trying next: %s", provider, e)
                last_err = e
                continue

        raise last_err or RuntimeError("All providers failed")

    async def generate_tutor_response(
        self,
        student_message: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        student_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            context = "\n\n".join(
                [f"Document: {d.get('title','Unknown')}\n{d.get('content','')}" for d in context_documents]
            )
            system_prompt = get_tutor_prompt(context=context, student_profile=student_profile)
            messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_history[-10:])
            messages.append({"role": "user", "content": student_message})

            out = await self._run_chat(messages)

            return {
                "response": out["response"],
                "context_used": len(context_documents),
                "tokens_used": out["tokens_used"],
                "provider": out["provider"],
                "model": out["model"],
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
        try:
            context = "\n\n".join(
                [f"Document: {d.get('title','Unknown')}\n{d.get('content','')}" for d in context_documents]
            )
            prompt = get_quiz_generation_prompt(
                topic=topic,
                subject=subject,
                grade_level=grade_level,
                difficulty=difficulty,
                num_questions=num_questions,
                context=context,
            )

            out = await self._run_chat([{"role": "user", "content": prompt}])

            raw = out["response"] or "{}"
            try:
                quiz_data = json.loads(raw)
            except json.JSONDecodeError:
                quiz_data = json.loads(raw.strip().strip("`").strip())

            return {
                "quiz_data": quiz_data,
                "tokens_used": out["tokens_used"],
                "provider": out["provider"],
                "model": out["model"],
            }
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
        try:
            prompt = get_grading_prompt(
                question=question,
                student_answer=student_answer,
                correct_answer=correct_answer,
                question_type=question_type,
                context=context,
            )
            out = await self._run_chat([{"role": "user", "content": prompt}])

            raw = out["response"] or "{}"
            try:
                grading_result = json.loads(raw)
            except json.JSONDecodeError:
                grading_result = json.loads(raw.strip().strip("`").strip())

            return {
                "score": grading_result.get("score", 0),
                "feedback": grading_result.get("feedback", ""),
                "explanation": grading_result.get("explanation", ""),
                "is_correct": grading_result.get("is_correct", False),
                "tokens_used": out["tokens_used"],
                "provider": out["provider"],
                "model": out["model"],
            }
        except Exception as e:
            logger.exception("Error grading answer")
            return {
                "score": 0,
                "feedback": "Unable to grade this answer automatically. Please review manually.",
                "error": str(e),
            }

# Global instance
ai_service = AIService()
