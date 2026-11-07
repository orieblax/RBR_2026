import os
import base64
import jwt
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.core.config import get_settings

settings = get_settings()
security_bearer = HTTPBearer(auto_error=False)

class TokenVault:
    """
    AES-256 / Fernet Encryption Vault for user AI tokens (sk-ant-oat01-*, sk-ant-api03-*, OpenAI, Groq)
    """
    def __init__(self, key: Optional[str] = None):
        raw_key = key or settings.MASTER_ENCRYPTION_KEY
        if len(raw_key.encode()) == 44 and raw_key.endswith("="):
            self._fernet = Fernet(raw_key.encode())
        else:
            b64_key = base64.urlsafe_b64encode(raw_key.encode().ljust(32)[:32])
            self._fernet = Fernet(b64_key)

    def encrypt(self, raw_token: str) -> str:
        if not raw_token:
            raise ValueError("Token cannot be empty")
        return self._fernet.encrypt(raw_token.strip().encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")
        return self._fernet.decrypt(encrypted_token.strip().encode()).decode()

    @staticmethod
    def mask_token(raw_token: str) -> str:
        if not raw_token:
            return ""
        clean = raw_token.strip()
        if len(clean) <= 12:
            return clean[:3] + "..." + clean[-2:]
        return clean[:10] + "..." + clean[-4:]

    @staticmethod
    def classify_token(token: str) -> Dict[str, str]:
        t = token.strip()
        if t.startswith("sk-ant-oat"):
            return {
                "provider": "anthropic",
                "auth_mode": "oauth_token",
                "beta_header": "oauth-2025-04-20",
                "label": "Anthropic Claude Setup-Token"
            }
        elif t.startswith("sk-ant-api"):
            return {
                "provider": "anthropic",
                "auth_mode": "api_key",
                "beta_header": "",
                "label": "Anthropic API Key"
            }
        elif t.startswith("gsk_"):
            return {
                "provider": "groq",
                "auth_mode": "api_key",
                "beta_header": "",
                "label": "Groq API Key"
            }
        elif t.startswith("sk-"):
            return {
                "provider": "openai",
                "auth_mode": "api_key",
                "beta_header": "",
                "label": "OpenAI API Key"
            }
        else:
            return {
                "provider": "unknown",
                "auth_mode": "api_key",
                "beta_header": "",
                "label": "Custom API Key"
            }

vault = TokenVault()

# Demo/Dev constant user ID for local parity testing and offline dashboard runs
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
DEMO_USER_EMAIL = "albeiro@rbrfinance.com"

def is_supabase_cloud_active() -> bool:
    return bool(
        settings.SUPABASE_URL
        and not settings.SUPABASE_URL.startswith("https://dummy")
        and settings.SUPABASE_JWT_SECRET
        and not settings.SUPABASE_JWT_SECRET.startswith("super-secret-jwt")
    )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> Dict[str, Any]:
    """
    Validates Supabase Bearer JWT and extracts user_id, email, and is_admin.
    Supports seamless demo access and offline operation on Vercel and localhost.
    """
    # 1. Fallback to demo user if no credentials provided
    if not credentials:
        return {
            "user_id": DEMO_USER_ID,
            "email": DEMO_USER_EMAIL,
            "is_admin": True,
            "role": "authenticated"
        }

    token = credentials.credentials.strip() if credentials.credentials else ""

    # 2. Allow demo-token in all environments (localhost & Vercel production)
    if token in ("demo-token", "dev-token") or token.startswith("demo-"):
        return {
            "user_id": DEMO_USER_ID,
            "email": DEMO_USER_EMAIL,
            "is_admin": True,
            "role": "authenticated"
        }

    # 3. Decode Supabase JWT
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub") or payload.get("id")
        if not user_id:
            # Fallback to demo user if identifier missing
            return {
                "user_id": DEMO_USER_ID,
                "email": DEMO_USER_EMAIL,
                "is_admin": True,
                "role": "authenticated"
            }
        
        app_metadata = payload.get("app_metadata", {})
        user_metadata = payload.get("user_metadata", {})
        is_admin = bool(
            app_metadata.get("is_admin") 
            or user_metadata.get("is_admin") 
            or payload.get("role") == "service_role"
            or payload.get("email") == DEMO_USER_EMAIL
        )

        return {
            "user_id": user_id,
            "email": payload.get("email", ""),
            "is_admin": is_admin,
            "role": payload.get("role", "authenticated")
        }
    except jwt.PyJWTError:
        # Fallback to demo user when Supabase is not configured or in dev/demo mode
        if not is_supabase_cloud_active() or settings.ENV == "development":
            return {
                "user_id": DEMO_USER_ID,
                "email": DEMO_USER_EMAIL,
                "is_admin": True,
                "role": "authenticated"
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación expirado o inválido"
        )

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: requiere privilegios de administrador"
        )
    return current_user
