"""
DeepSeek AI integration for signal reasoning, analysis, and self-correction.
Uses OpenAI-compatible API.
"""

import json
from openai import AsyncOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class DeepSeekClient:
    def __init__(self):
        import httpx
        self._client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            http_client=httpx.AsyncClient(
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                timeout=httpx.Timeout(60.0),
            ),
        )
        self.model = settings.DEEPSEEK_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: dict | None = None,
    ) -> str:
        """Send chat completion request to DeepSeek."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def analyze_signal_context(
        self,
        coin_symbol: str,
        indicators: dict,
        patterns: list[str],
        trend_direction: str,
        news_context: list[str],
        btc_correlation: float | None,
        fear_greed: int | None,
    ) -> dict:
        """AI analysis of signal quality with comprehensive reasoning."""
        system_prompt = (
            "You are a strict crypto trading risk analyst. Your job is to critically evaluate trading signals "
            "and assign a precise confidence adjustment. DO NOT default to small positive adjustments. "
            "Use the FULL range from -0.20 to +0.20. Be decisive:\n"
            "  +0.10 to +0.20: Strong setup — aligned trend, healthy RSI (40-65 for longs), good volume, ADX>25, "
            "clean patterns, no divergences.\n"
            "  +0.01 to +0.09: Decent setup with minor concerns.\n"
            "   0.00: Mixed — equal bull and bear factors.\n"
            "  -0.01 to -0.09: Weak setup — overbought RSI, low volume, weak ADX, or divergences.\n"
            "  -0.10 to -0.20: Bad setup — RSI extreme (>75 or <25), ADX<15, contrary patterns, "
            "MACD divergence, volume dying, multiple red flags.\n\n"
            "CRITICAL: Analyze EACH indicator individually. A signal with RSI>70, Stoch>90, and CCI>200 "
            "is OVERBOUGHT — that deserves NEGATIVE adjustment for longs, not +0.05."
        )

        user_prompt = f"""Critically analyze this {trend_direction.upper()} signal for {coin_symbol}:

**Key Indicators:**
{json.dumps(indicators, indent=2, default=str)}

**Detected Patterns:** {', '.join(patterns) if patterns else 'None'}
**BTC Correlation:** {btc_correlation if btc_correlation is not None else 'N/A'}
**Fear & Greed Index:** {fear_greed if fear_greed is not None else 'N/A'}
**Recent News:** {chr(10).join(f'- {n}' for n in news_context[:5]) if news_context else 'None'}

CHECKLIST for {trend_direction.upper()}:
1. RSI_14: Is it overbought (>70 for long) or oversold (<30 for short)? RSI_7?
2. Stochastic K: Extreme (>90 for long = bad, <10 for short = bad)?
3. MACD histogram: Positive for long, negative for short? Any divergence?
4. ADX: >25 = trending (good), <20 = no trend (bad)?
5. Volume ratio: >1.0 = good, <0.7 = low conviction?
6. CCI: >200 or <-200 = extreme, potential reversal?
7. Bollinger Bands: Price at upper band for long = resistance risk?
8. Pattern quality: Aligned or contrary patterns on multiple TFs?

Give a PRECISE adjustment. DO NOT default to +0.05.

Respond in JSON:
{{
    "confidence_adjustment": <float between -0.20 and +0.20 — be precise, use full range>,
    "reasoning_en": "<2-3 sentences analyzing the key factors>",
    "reasoning_uk": "<2-3 речення аналізу ключових факторів>",
    "reasoning_ru": "<2-3 предложения анализа ключевых факторов>",
    "risk_factors": ["<list specific risks with numbers, e.g. 'RSI_14 at 72 overbought'>"],
    "key_levels": ["<important S/R levels>"],
    "recommended_timeframe": "<how long to hold>",
    "invalidation": "<what invalidates this trade>"
}}"""

        try:
            response = await self.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("DeepSeek returned non-JSON response for signal analysis")
            return {
                "confidence_adjustment": 0.0,
                "reasoning_en": "AI analysis unavailable",
                "reasoning_uk": "AI аналіз недоступний",
                "reasoning_ru": "AI анализ недоступен",
                "risk_factors": [],
                "key_levels": [],
                "recommended_timeframe": "unknown",
                "invalidation": "unknown",
            }
        except Exception as e:
            logger.error(f"DeepSeek signal analysis failed: {e}")
            return {
                "confidence_adjustment": 0.0,
                "reasoning_en": "AI analysis unavailable",
                "reasoning_uk": "AI аналіз недоступний",
                "reasoning_ru": "AI анализ недоступен",
                "risk_factors": [],
                "key_levels": [],
                "recommended_timeframe": "unknown",
                "invalidation": "unknown",
            }

    async def generate_signal_reasoning(
        self,
        coin_symbol: str,
        direction: str,
        entry: float,
        tp1: float,
        stop_loss: float,
        confidence: float,
        factors: dict,
        lang: str = "en",
    ) -> str:
        """Generate human-readable signal reasoning in the specified language."""
        lang_instruction = {
            "uk": "Respond in Ukrainian (Українська).",
            "ru": "Respond in Russian (Русский).",
        }.get(lang, "Respond in English.")

        prompt = f"""Write a concise 2-3 sentence reasoning for this crypto signal:
Coin: {coin_symbol}, Direction: {direction.upper()}, Entry: {entry}, TP1: {tp1}, SL: {stop_loss}
Confidence: {confidence:.0f}%
Key factors: {json.dumps(factors.get('trend', {}), default=str)}
Patterns: {json.dumps(factors.get('patterns', {}), default=str)}
{lang_instruction}
Be professional, mention the key technical reason for the trade."""

        return await self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=300,
        )

    async def analyze_news_sentiment(self, title: str, summary: str | None) -> dict:
        """Analyze news article sentiment and extract relevant coins."""
        prompt = f"""Analyze this crypto news article and respond in JSON:

Title: {title}
Summary: {summary or 'N/A'}

{{
    "sentiment": <float from -1.0 (very bearish) to 1.0 (very bullish)>,
    "importance": <float from 0.0 to 1.0>,
    "coins_mentioned": ["<list of coin symbols>"],
    "category": "<regulatory|adoption|hack|partnership|market|defi|nft|other>"
}}"""

        try:
            response = await self.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except (json.JSONDecodeError, Exception):
            return {"sentiment": 0.0, "importance": 0.3, "coins_mentioned": [], "category": "other"}

    async def self_correct_signal(
        self, signal_data: dict, outcome_data: dict, historical_feedback: list[dict]
    ) -> dict:
        """Self-correction: analyze what went wrong/right and suggest parameter adjustments."""
        prompt = f"""As a trading system AI, analyze this signal's outcome and suggest corrections:

**Signal:**
{json.dumps(signal_data, indent=2, default=str)}

**Outcome:**
{json.dumps(outcome_data, indent=2, default=str)}

**Recent feedback history (last 10 signals):**
{json.dumps(historical_feedback[-10:], indent=2, default=str)}

Provide adjustment recommendations in JSON:
{{
    "lesson": "<what can be learned>",
    "confidence_bias": <float adjustment to future confidence, -0.1 to +0.1>,
    "sl_adjustment_factor": <multiplier for SL distance, 0.8 to 1.2>,
    "tp_adjustment_factor": <multiplier for TP distance, 0.8 to 1.2>,
    "min_volume_ratio_adjustment": <new minimum volume ratio, 0.5 to 2.0>,
    "avoid_patterns": ["<patterns that correlate with losses>"],
    "prefer_patterns": ["<patterns that correlate with wins>"],
    "parameter_changes": {{}}
}}"""

        try:
            response = await self.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Self-correction analysis failed: {e}")
            return {}


deepseek = DeepSeekClient()
