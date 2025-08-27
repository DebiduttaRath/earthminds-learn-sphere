from typing import List, Dict, Any, Optional, Iterable
import logging
import json
import os

from openai import AsyncOpenAI
from openai import APIError, RateLimitError

from config import settings
from utils.prompts import (
    get_tutor_prompt,
    get_quiz_generation_prompt,
    get_grading_prompt,
)

logger = logging.getLogger(__name__)

def _mk_openai_client() -> AsyncOpenAI:
    # Standard OpenAI (no base_url override)
    return AsyncOpenAI(api_key=settings.openai_api_key)

def _mk_xai_client() -> AsyncOpenAI:
    # xAI Grok via OpenAI-compatible API
    # Docs: set base_url to https://api.x.ai/v1 and use your xAI API key.
    base_url = getattr(settings, "xai_base_url", None) or "https://api.x.ai/v1"
    xai_key = getattr(settings, "xai_api_key", None) or os.getenv("XAI_API_KEY")
    return AsyncOpenAI(api_key=xai_key, base_url=base_url)

def _provider_plan() -> Iterable[str]:
    # You can control order via settings, default: try OpenAI then xAI
    order = getattr(settings, "provider_order", None)
    if isinstance(order, (list, tuple)) and order:
        return [p.lower() for p in order]
    return ["openai", "xai"]

class AIService:
    """AI service with provider fallback: OpenAI ↔ xAI (Grok)"""

    def __init__(self):
        # Model choices per provider (override in settings)
        self.oa_model = getattr(settings, "openai_model", "gpt-4o-mini")
        self.xai_model = getattr(settings, "xai_model", "grok-4")
        self.max_tokens = getattr(settings, "max_tokens", 1500)
        self.temperature = getattr(settings, "temperature", 0.7)

        # Lazy init clients so missing keys don't crash import
        self._clients: Dict[str, AsyncOpenAI] = {}

    def _get_client_and_model(self, provider: str) -> tuple[AsyncOpenAI, str]:
        provider = provider.lower()
        if provider == "openai":
            if "openai" not in self._clients:
                self._clients["openai"] = _mk_openai_client()
            return self._clients["openai"], self.oa_model
        elif provider in ("xai", "grok", "xai_grok"):
            if "xai" not in self._clients:
                self._clients["xai"] = _mk_xai_client()
            return self._clients["xai"], self.xai_model
        else:
            raise ValueError(f"Unknown provider '{provider}'")

    async def _chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Try providers in configured order. Falls back on 429/insufficient_quota or transport errors.
        Returns a dict with keys: response, tokens_used, provider.
        """
        last_err: Optional[Exception] = None

        for provider in _provider_plan():
            try:
                client, model = self._get_client_and_model(provider)

                resp = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                assistant_message = resp.choices[0].message.content or ""
                tokens_used = (resp.usage.total_tokens if resp.usage else None)
                return {
                    "response": assistant_message,
                    "tokens_used": tokens_used,
                    "provider": provider,
                    "model": model,
                }

            except RateLimitError as e:
                # OpenAI/xAI both use 429 for quota/rate issues — try next provider
                logger.warning("Rate/quota error on %s: %s", provider, e)
                last_err = e
                continue
            except APIError as e:
                # If it's an explicit insufficient_quota or 5xx, try next
                code = getattr(e, "code", None) or getattr(e, "status_code", None)
                if code in (429, 500, 502, 503, 504) or "insufficient_quota" in str(e):
                    logger.warning("API error on %s (code=%s): %s", provider, code, e)
                    last_err = e
                    continue
                # Otherwise, fail fast
                logger.exception("Non-retryable API error on %s", provider)
                raise
            except Exception as e:
                # Network issues, timeouts, etc — try next provider
                logger.warning("General error on %s: %s", provider, e)
                last_err = e
                continue

        # If all providers failed:
        raise last_err or RuntimeError("All AI providers failed")

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

            out = await self._chat(messages, self.max_tokens, self.temperature)

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

            out = await self._chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.3,
            )

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

            out = await self._chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2,
            )

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
