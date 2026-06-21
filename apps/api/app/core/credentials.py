from app.core.exceptions import APIKeyMissingError
from app.core.context import active_provider_var, gemini_key_var, openai_key_var, groq_key_var

class CredentialValidator:
    """Validates key configuration for active LLM provider."""

    async def ensure_llm_available(self) -> None:
        """
        Check if LLM keys are configured for active provider.
        Raises APIKeyMissingError if the key is missing or is set to placeholders.
        """
        provider = active_provider_var.get() or "gemini"
        if provider == "mock":
            return
        key = None
        if provider == "gemini":
            key = gemini_key_var.get()
        elif provider == "openai":
            key = openai_key_var.get()
        elif provider == "groq":
            key = groq_key_var.get()

        if not key or key in ("••••••••", "********", ""):
            raise APIKeyMissingError(provider=provider)
