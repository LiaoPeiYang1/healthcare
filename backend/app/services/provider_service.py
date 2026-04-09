import re

import httpx

from app.config import settings


SUPPORTED_LANGUAGES = {
    'zh': '中文',
    'en': '英文',
    'ja': '日文',
    'ko': '韩文',
    'de': '德文',
    'fr': '法文',
}


class ProviderService:
    async def detect_language(self, text: str) -> tuple[str, float]:
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh', 0.95
        if re.search(r'[\u3040-\u30ff]', text):
            return 'ja', 0.94
        if re.search(r'[\uac00-\ud7af]', text):
            return 'ko', 0.94
        lowered = text.lower()
        if any(token in lowered for token in [' der ', ' die ', ' das ', ' und ']):
            return 'de', 0.85
        if any(token in lowered for token in [' le ', ' la ', ' les ', ' des ']):
            return 'fr', 0.85
        return 'en', 0.8

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if settings.dashscope_api_key:
            try:
                return await self._translate_with_dashscope(text, source_lang, target_lang)
            except Exception:
                pass
        return self._fallback_translation(text, source_lang, target_lang)

    async def _translate_with_dashscope(self, text: str, source_lang: str, target_lang: str) -> str:
        url = f"{settings.dashscope_base_url.rstrip('/')}/chat/completions"
        headers = {
            'Authorization': f'Bearer {settings.dashscope_api_key}',
            'Content-Type': 'application/json',
        }
        payload = {
            'model': settings.dashscope_model,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是专业医药翻译引擎，请仅返回译文。',
                },
                {
                    'role': 'user',
                    'content': f'请将以下{SUPPORTED_LANGUAGES[source_lang]}文本翻译为{SUPPORTED_LANGUAGES[target_lang]}：\n\n{text}',
                },
            ],
            'temperature': 0.1,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data['choices'][0]['message']['content'].strip()

    def _fallback_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        return (
            f"【{SUPPORTED_LANGUAGES[source_lang]} -> {SUPPORTED_LANGUAGES[target_lang]}】\n"
            f"{text}\n\n"
            '当前为本地开发占位译文。接入通义千问配置后可替换为真实模型翻译结果。'
        )


provider_service = ProviderService()
