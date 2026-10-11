"""Fixed provider destinations; user settings never supply a request URL."""
from dataclasses import dataclass, field
from typing import Literal

ProviderId = Literal['openai', 'gemini', 'openrouter', 'groq', 'aimlapi']

@dataclass(frozen=True)
class ProviderSpec:
    id: str
    name: str
    default_model: str
    endpoint: str
    help: str

    @property
    def key_env(self): return self.id.upper() + '_API_KEY'

    @property
    def model_env(self): return self.id.upper() + '_MODEL'

PROVIDERS = {p.id: p for p in (
    ProviderSpec('openai', 'OpenAI', 'gpt-5-mini', 'https://api.openai.com/v1/responses',
                 'Responses API ve yapılandırılmış çıktı destekleyen bir model seçin.'),
    ProviderSpec('gemini', 'Gemini', 'gemini-3.5-flash', 'https://generativelanguage.googleapis.com/v1beta/models/',
                 'Google AI Studio anahtarınızı ve yapılandırılmış çıktı destekleyen bir Gemini modelini kullanın.'),
    ProviderSpec('openrouter', 'OpenRouter', 'openai/gpt-5-mini', 'https://openrouter.ai/api/v1/chat/completions',
                 'Yapılandırılmış çıktı destekleyen modelin tam adını yazın; örneğin openai/gpt-5-mini. İstek OpenRouter üzerinden model sağlayıcısına iletilir.'),
    ProviderSpec('groq', 'Groq', 'openai/gpt-oss-20b', 'https://api.groq.com/openai/v1/chat/completions',
                 'Strict Structured Outputs destekleyen bir model seçin; örneğin openai/gpt-oss-20b veya openai/gpt-oss-120b.'),
    ProviderSpec('aimlapi', 'AIMLAPI', 'openai/gpt-5-mini-2025-08-07', 'https://api.aimlapi.com/v1/chat/completions',
                 'Chat Completions ve JSON Schema destekleyen modelin tam adını yazın. İstek AIMLAPI üzerinden model sağlayıcısına iletilir.'),
)}

@dataclass(frozen=True)
class AIConnection:
    provider_id: str
    key: str = field(repr=False)
    model: str

    @property
    def provider(self): return PROVIDERS[self.provider_id]
