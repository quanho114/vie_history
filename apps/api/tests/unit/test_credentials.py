import pytest
from app.core.exceptions import APIKeyMissingError
from app.core.credentials import CredentialValidator
from app.core.context import gemini_key_var

@pytest.mark.asyncio
async def test_credential_validator_missing_key():
    validator = CredentialValidator()
    token = gemini_key_var.set("••••••••")
    try:
        with pytest.raises(APIKeyMissingError):
            await validator.ensure_llm_available()
    finally:
        gemini_key_var.reset(token)

@pytest.mark.asyncio
async def test_credential_validator_valid_key():
    validator = CredentialValidator()
    token = gemini_key_var.set("valid_key_123")
    try:
        # Should not raise any exception
        await validator.ensure_llm_available()
    finally:
        gemini_key_var.reset(token)
