# app/services/llm_service.py
"""
Dual-Model LLM Service
=======================
Routes requests to either NVIDIA NIM (Nemotron 550B) or Google Gemini
depending on the use case.

Usage:
    from app.services.llm_service import llm

    # Use Nemotron for policy parsing (complex reasoning)
    result = await llm.nemotron("Parse this rule: Never email EU leads on weekends")

    # Use Gemini for data analysis / insights (large context)
    result = await llm.gemini("Analyze these leads and find anomalies", data=rows)

    # Use Gemini with strict JSON output
    result = await llm.gemini_json("Extract the company name and score", schema=MySchema)
"""

import json
import logging
import os
import warnings
from typing import Any, Optional

import google.generativeai as genai
from openai import OpenAI

# Suppress FutureWarning from google-generativeai
warnings.filterwarnings('ignore', category=FutureWarning, module='google.generativeai')

log = logging.getLogger(__name__)


class LLMService:
    """Unified LLM service that routes to Nemotron or Gemini."""

    def __init__(self):
        # -----------------------------------------------------------------
        # NVIDIA NIM (Nemotron 550B) — via OpenAI-compatible client
        # -----------------------------------------------------------------
        self._nvidia_api_key = os.getenv("NVIDIA_NIM_API_KEY", "")
        self._nvidia_model = os.getenv("NVIDIA_NIM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

        if self._nvidia_api_key:
            self._nvidia_client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=self._nvidia_api_key,
            )
            log.info(f"NVIDIA NIM initialized with model: {self._nvidia_model}")
        else:
            self._nvidia_client = None
            log.warning("NVIDIA_NIM_API_KEY not set — Nemotron will not be available")

        # -----------------------------------------------------------------
        # Google Gemini — via google-generativeai SDK
        # -----------------------------------------------------------------
        self._gemini_api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

        if self._gemini_api_key:
            genai.configure(api_key=self._gemini_api_key)
            self._gemini_model = genai.GenerativeModel("gemini-3.6-flash")
            log.info("Google Gemini initialized with model: gemini-3.6-flash")
        else:
            self._gemini_model = None
            log.warning("GEMINI_API_KEY not set — Gemini will not be available")

    # =====================================================================
    # NVIDIA NIM — Nemotron 550B (AI Policies, complex reasoning)
    # =====================================================================

    def nemotron(
        self,
        prompt: str,
        system_prompt: str = "You are an enterprise AI policy engine. Always respond with valid JSON only.",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict | str:
        """
        Send a prompt to NVIDIA Nemotron 550B.
        Best for: AI Policies, complex rule parsing, structured reasoning.
        Returns parsed JSON dict if response is valid JSON, otherwise raw string.
        """
        if not self._nvidia_client:
            raise RuntimeError("NVIDIA NIM is not configured. Set NVIDIA_NIM_API_KEY in .env")

        try:
            completion = self._nvidia_client.chat.completions.create(
                model=self._nvidia_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = completion.choices[0].message.content.strip()
            log.info(f"Nemotron response received ({len(content)} chars)")

            # Attempt to parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content

        except Exception as e:
            log.error(f"Nemotron API error: {e}")
            raise

    def nemotron_stream(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful AI assistant.",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Stream a response from NVIDIA Nemotron 550B.
        Best for: AI Manager chat interface (real-time responses).
        Yields text chunks as they arrive.
        """
        if not self._nvidia_client:
            raise RuntimeError("NVIDIA NIM is not configured. Set NVIDIA_NIM_API_KEY in .env")

        completion = self._nvidia_client.chat.completions.create(
            model=self._nvidia_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in completion:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content is not None:
                yield delta.content

    # =====================================================================
    # Google Gemini (AI Insights, data analytics, large context)
    # =====================================================================

    def gemini(
        self,
        prompt: str,
        data: Optional[Any] = None,
    ) -> str:
        """
        Send a prompt to Google Gemini.
        Best for: AI Insights, analyzing large datasets, finding patterns.
        Optionally pass `data` (list of dicts, string, etc.) to include as context.
        Returns raw text response.
        """
        if not self._gemini_model:
            raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in .env")

        try:
            # Build the full prompt with data context
            full_prompt = prompt
            if data is not None:
                if isinstance(data, (list, dict)):
                    data_str = json.dumps(data, indent=2, default=str)
                else:
                    data_str = str(data)
                full_prompt = f"{prompt}\n\n--- DATA ---\n{data_str}"

            response = self._gemini_model.generate_content(full_prompt)
            result = response.text
            log.info(f"Gemini response received ({len(result)} chars)")
            return result

        except Exception as e:
            log.error(f"Gemini API error: {e}")
            raise

    def gemini_json(
        self,
        prompt: str,
        data: Optional[Any] = None,
    ) -> dict | list:
        """
        Send a prompt to Google Gemini with strict JSON output mode.
        Best for: Structured data extraction, AI Insights in parseable format.
        Returns parsed JSON (dict or list).
        """
        if not self._gemini_model:
            raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY in .env")

        try:
            full_prompt = prompt
            if data is not None:
                if isinstance(data, (list, dict)):
                    data_str = json.dumps(data, indent=2, default=str)
                else:
                    data_str = str(data)
                full_prompt = f"{prompt}\n\n--- DATA ---\n{data_str}"

            response = self._gemini_model.generate_content(
                full_prompt,
                generation_config={"response_mime_type": "application/json"},
            )

            result = json.loads(response.text)
            log.info(f"Gemini JSON response received")
            return result

        except json.JSONDecodeError as e:
            log.error(f"Gemini returned invalid JSON: {e}")
            raise
        except Exception as e:
            log.error(f"Gemini API error: {e}")
            raise

    # =====================================================================
    # Smart routing with fallback (Gemini primary -> NVIDIA NIM fallback)
    # =====================================================================

    def _fallback_notice(self, error: Exception) -> str:
        """Build a human-readable notice describing why we fell back to NIM."""
        err_text = str(error)
        if "429" in err_text or "quota" in err_text.lower():
            return "Gemini quota is out — this response was generated by NVIDIA NIM (Nemotron) as a fallback."
        return "Gemini is unavailable — this response was generated by NVIDIA NIM (Nemotron) as a fallback."

    def smart_text(
        self,
        prompt: str,
        data: Optional[Any] = None,
    ) -> tuple[str, dict]:
        """
        Text generation with automatic fallback: try Gemini first, and if it
        fails (e.g. quota exceeded) fall back to NVIDIA NIM (Nemotron).

        Returns (text, meta) where meta = {"model_used": ..., "llm_notice": str | None}.
        """
        try:
            result = self.gemini(prompt, data=data)
            return result, {"model_used": "gemini", "llm_notice": None}
        except Exception as gemini_err:
            log.warning(f"Gemini failed ({gemini_err}); falling back to Nemotron")
            if not self._nvidia_client:
                raise
            full_prompt = prompt
            if data is not None:
                data_str = json.dumps(data, indent=2, default=str) if isinstance(data, (list, dict)) else str(data)
                full_prompt = f"{prompt}\n\n--- DATA ---\n{data_str}"
            result = self.nemotron(
                full_prompt,
                system_prompt="You are a helpful enterprise AI assistant. Respond with plain text only.",
            )
            if isinstance(result, (dict, list)):
                result = json.dumps(result, default=str)
            return result, {"model_used": "nemotron", "llm_notice": self._fallback_notice(gemini_err)}

    def smart_json(
        self,
        prompt: str,
        data: Optional[Any] = None,
    ) -> tuple[dict | list, dict]:
        """
        JSON generation with automatic fallback: try Gemini JSON mode first,
        and if it fails (e.g. quota exceeded) fall back to NVIDIA NIM (Nemotron).

        Returns (parsed_json, meta) where meta = {"model_used": ..., "llm_notice": str | None}.
        """
        try:
            result = self.gemini_json(prompt, data=data)
            return result, {"model_used": "gemini", "llm_notice": None}
        except Exception as gemini_err:
            log.warning(f"Gemini JSON failed ({gemini_err}); falling back to Nemotron")
            if not self._nvidia_client:
                raise
            full_prompt = prompt
            if data is not None:
                data_str = json.dumps(data, indent=2, default=str) if isinstance(data, (list, dict)) else str(data)
                full_prompt = f"{prompt}\n\n--- DATA ---\n{data_str}"
            result = self.nemotron(full_prompt)
            if isinstance(result, str):
                # Try to salvage JSON from a fenced code block
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    # Split by lines and remove the first and last line (which are the backticks)
                    lines = cleaned.split("\n")
                    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
                        cleaned = "\n".join(lines[1:-1])
                try:
                    result = json.loads(cleaned.strip())
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse Nemotron JSON: {e}. Raw response: {result}")
                    result = []
            return result, {"model_used": "nemotron", "llm_notice": self._fallback_notice(gemini_err)}

    # =====================================================================
    # Health Check
    # =====================================================================

    def status(self) -> dict:
        """Returns the status of both LLM backends."""
        return {
            "nvidia_nim": {
                "available": self._nvidia_client is not None,
                "model": self._nvidia_model if self._nvidia_client else None,
            },
            "gemini": {
                "available": self._gemini_model is not None,
                "model": "gemini-3.6-flash" if self._gemini_model else None,
            },
        }


# =========================================================================
# Singleton instance — import this in your routers
# =========================================================================
llm = LLMService()
