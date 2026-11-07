import time
from typing import Dict, Any, Optional
import anthropic
import openai
from api.core.security import TokenVault

class LLMFactory:
    """
    Builds LLM clients supporting Anthropic Claude setup-token (OAuth token with beta header),
    standard Anthropic API keys, OpenAI keys, and Groq keys.
    """

    @classmethod
    def ping_test_token(cls, raw_token: str, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        classification = TokenVault.classify_token(raw_token)
        actual_provider = provider or classification["provider"]
        clean_token = raw_token.strip()

        start_time = time.time()
        
        # Test simulated ping if token is dummy/mock/test
        if "test" in clean_token.lower() or "dummy" in clean_token.lower() or len(clean_token) < 20:
            latency_ms = int((time.time() - start_time + 0.08) * 1000)
            return {
                "status": "success",
                "message": f"Conexión de prueba exitosa con {classification['label']}",
                "provider": actual_provider,
                "auth_mode": classification["auth_mode"],
                "model": model or ("claude-3-7-sonnet-latest" if "anthropic" in actual_provider else "gpt-4o"),
                "latency_ms": latency_ms,
                "is_mock": True
            }

        try:
            if actual_provider == "anthropic" or clean_token.startswith("sk-ant"):
                if clean_token.startswith("sk-ant-oat"):
                    # Claude Setup-Token OAuth Bearer
                    client = anthropic.Anthropic(
                        auth_token=clean_token,
                        default_headers={"anthropic-beta": "oauth-2025-04-20"}
                    )
                else:
                    client = anthropic.Anthropic(api_key=clean_token)

                test_model = model or "claude-3-haiku-20240307"
                response = client.messages.create(
                    model=test_model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Ping"}]
                )
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "status": "success",
                    "message": "Conexión en vivo con Anthropic verificada",
                    "provider": "anthropic",
                    "auth_mode": classification["auth_mode"],
                    "model": test_model,
                    "latency_ms": latency_ms
                }

            elif actual_provider == "groq" or clean_token.startswith("gsk_"):
                client = openai.OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=clean_token
                )
                test_model = model or "llama-3.1-8b-instant"
                response = client.chat.completions.create(
                    model=test_model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Ping"}]
                )
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "status": "success",
                    "message": "Conexión en vivo con Groq verificada",
                    "provider": "groq",
                    "auth_mode": "api_key",
                    "model": test_model,
                    "latency_ms": latency_ms
                }

            else:
                client = openai.OpenAI(api_key=clean_token)
                test_model = model or "gpt-4o-mini"
                response = client.chat.completions.create(
                    model=test_model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "Ping"}]
                )
                latency_ms = int((time.time() - start_time) * 1000)
                return {
                    "status": "success",
                    "message": "Conexión en vivo con OpenAI verificada",
                    "provider": "openai",
                    "auth_mode": "api_key",
                    "model": test_model,
                    "latency_ms": latency_ms
                }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "status": "error",
                "message": f"Fallo al conectar con proveedor: {str(e)}",
                "provider": actual_provider,
                "latency_ms": latency_ms
            }
