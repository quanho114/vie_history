import contextvars

# Context variables for LLM configuration sent from frontend headers
active_provider_var = contextvars.ContextVar("active_provider", default=None)

# Gemini config
gemini_key_var = contextvars.ContextVar("gemini_key", default=None)
gemini_model_var = contextvars.ContextVar("gemini_model", default=None)

# Groq config
groq_key_var = contextvars.ContextVar("groq_key", default=None)
groq_model_var = contextvars.ContextVar("groq_model", default=None)

# OpenAI config
openai_key_var = contextvars.ContextVar("openai_key", default=None)
openai_model_var = contextvars.ContextVar("openai_model", default=None)
openai_base_url_var = contextvars.ContextVar("openai_base_url", default=None)

# Ollama config
ollama_url_var = contextvars.ContextVar("ollama_url", default=None)
ollama_model_var = contextvars.ContextVar("ollama_model", default=None)

# RAG & LLM parameter config
rag_mode_var = contextvars.ContextVar("rag_mode", default=None)
chunk_limit_var = contextvars.ContextVar("chunk_limit", default=None)
llm_temperature_var = contextvars.ContextVar("llm_temperature", default=None)

