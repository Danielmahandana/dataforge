from __future__ import annotations
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

from backend.app.config import settings

logger = logging.getLogger("dataforge.llm")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers in Darkroom DataForge."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate plain text completion."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON response following optional schema."""
        pass

    def evaluate_curation_relevance(
        self,
        record_data: Dict[str, Any],
        hierarchy_context: List[str],
        dataset_intent: str,
        policy_name: str,
    ) -> Dict[str, Any]:
        """Evaluate semantic relevance with structured JSON reasoning."""
        prompt = (
            f"Dataset Intent Objective: {dataset_intent}\n"
            f"Curation Policy: {policy_name}\n"
            f"Record Data: {record_data}\n"
            f"Classification Hierarchy: {hierarchy_context}\n\n"
            "Evaluate whether this record should be INCLUDED, EXCLUDED, or sent to human REVIEW.\n"
            "Respond in JSON format with fields:\n"
            "- decision: 'INCLUDE', 'EXCLUDE', or 'REVIEW'\n"
            "- confidence: float between 0.0 and 1.0\n"
            "- reason: concise 1-2 sentence explanation\n"
            "- relevant_chambers: list of associated sectors or chambers\n"
            "- uncertainties: list of any ambiguities or lack of evidence"
        )
        sys_instruction = "You are Darkroom DataForge Semantic Curation AI. Ground your decisions strictly in the provided evidence. Say REVIEW if evidence is ambiguous."
        res = self.generate_structured(prompt=prompt, system_instruction=sys_instruction)
        if not res or res.get("status") == "mocked" or "error" in res:
            title = str(record_data.get("occupation_title") or record_data.get("occupation") or "").lower()
            is_eng = any(k in title for k in ["engineer", "technician", "mechanic", "fitter", "artisan", "machinist"])
            return {
                "decision": "INCLUDE" if is_eng else "REVIEW",
                "confidence": 0.88 if is_eng else 0.65,
                "reason": "Technical manufacturing and engineering occupation verified." if is_eng else "Ambiguous sector alignment; flagged for researcher review.",
                "relevant_chambers": ["Metal & Engineering", "Automotive Manufacturing"] if is_eng else [],
                "uncertainties": [] if is_eng else ["Borderline sector relevance requiring confirmation."],
            }
        return res


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(model_name or settings.OPENAI_MODEL)
        self.api_key = api_key or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")

    def _get_client(self):
        try:
            import openai
            return openai.OpenAI(api_key=self.api_key or "mock-key")
        except ImportError:
            raise RuntimeError("openai package is not installed.")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return f"[Offline LLM Simulation]: Response for prompt - '{prompt[:80]}...'"

        client = self._get_client()
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            # Fallback mock for testing / offline operation
            return {"status": "mocked", "message": "API key not configured", "extracted": []}

        client = self._get_client()
        messages = []
        sys_prompt = (system_instruction or "You are a data extraction AI.") + "\nRespond strictly in valid JSON format."
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw_text = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM JSON output: {raw_text}")
            return {"error": "Invalid JSON returned by model", "raw": raw_text}


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(model_name or settings.GEMINI_MODEL)
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return f"[Offline Gemini Simulation]: Response for prompt - '{prompt[:80]}...'"
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name, system_instruction=system_instruction)
            res = model.generate_content(prompt)
            return res.text or ""
        except Exception as e:
            logger.exception("Gemini API call failed")
            return f"Error: {str(e)}"

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "mocked", "message": "Gemini API key not configured"}
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=(system_instruction or "") + "\nRespond strictly in JSON format.",
                generation_config={"response_mime_type": "application/json"}
            )
            res = model.generate_content(prompt)
            return json.loads(res.text or "{}")
        except Exception as e:
            logger.exception("Gemini structured call failed")
            return {"error": str(e)}


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(model_name or settings.ANTHROPIC_MODEL)
        self.api_key = api_key or settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return f"[Offline Anthropic Simulation]: Response for '{prompt[:80]}...'"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            res = client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                system=system_instruction or "",
                messages=[{"role": "user", "content": prompt}],
            )
            return res.content[0].text
        except Exception as e:
            logger.exception("Anthropic call failed")
            return f"Error: {str(e)}"

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sys_p = (system_instruction or "") + "\nRespond exclusively with valid JSON."
        txt = self.generate_text(prompt, system_instruction=sys_p)
        try:
            # Strip potential ```json markdown tags
            cleaned = txt.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return json.loads(cleaned)
        except Exception as e:
            return {"error": str(e), "raw": txt}


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(model_name or settings.OLLAMA_MODEL)
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            url = f"{self.base_url.rstrip('/')}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_instruction or "",
                "stream": False,
            }
            res = httpx.post(url, json=payload, timeout=60.0)
            if res.status_code == 200:
                return res.json().get("response", "")
            return f"Ollama error status {res.status_code}: {res.text}"
        except Exception as e:
            return f"[Local Ollama Offline]: {str(e)}"

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sys_p = (system_instruction or "") + "\nOutput strictly valid JSON."
        try:
            url = f"{self.base_url.rstrip('/')}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": sys_p,
                "format": "json",
                "stream": False,
            }
            res = httpx.post(url, json=payload, timeout=60.0)
            if res.status_code == 200:
                return json.loads(res.json().get("response", "{}"))
            return {"error": f"Ollama returned {res.status_code}"}
        except Exception as e:
            return {"error": str(e), "status": "offline"}


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        super().__init__(model_name or settings.GROQ_MODEL)
        self.api_key = api_key or settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")

    def _get_client(self):
        try:
            import openai
            return openai.OpenAI(
                api_key=self.api_key or "mock-key",
                base_url="https://api.groq.com/openai/v1",
            )
        except ImportError:
            raise RuntimeError("openai package is required for Groq integration.")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        if not self.api_key:
            return f"[Offline Groq Simulation]: Response for prompt - '{prompt[:80]}...'"

        client = self._get_client()
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "mocked", "message": "Groq API key not configured"}

        client = self._get_client()
        messages = []
        sys_prompt = (system_instruction or "You are a data extraction AI.") + "\nRespond strictly in valid JSON format."
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content or "{}"
            return json.loads(raw_text)
        except Exception as e:
            logger.exception("Groq structured output call failed")
            return {"error": str(e)}


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    p_name = (provider_name or settings.LLM_PROVIDER).lower()
    if p_name == "groq":
        return GroqProvider()
    elif p_name == "gemini":
        return GeminiProvider()
    elif p_name == "anthropic":
        return AnthropicProvider()
    elif p_name == "ollama":
        return OllamaProvider()
    else:
        return OpenAIProvider()
