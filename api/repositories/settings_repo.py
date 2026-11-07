import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

DEFAULT_AI_MODEL = "claude-3-7-sonnet-latest"
DEFAULT_ADMIN_USER_ID = "00000000-0000-0000-0000-000000000001"


def _default_users_store() -> Dict[str, Dict[str, Any]]:
    return {
        DEFAULT_ADMIN_USER_ID: {
            "id": DEFAULT_ADMIN_USER_ID,
            "email": "albeiro@rbrfinance.com",
            "full_name": "Albeiro Yaime",
            "is_admin": True,
            "is_active": True,
            "default_ai_model": DEFAULT_AI_MODEL,
            "created_at": "2026-01-01T00:00:00Z",
        }
    }


def _default_system_settings() -> Dict[str, Any]:
    return {
        "default_ai_model": DEFAULT_AI_MODEL,
    }


class SettingsRepository:
    """
    Persistent repository for global system settings (Modelo Predeterminado Global),
    per-user AI credentials & preferred models (Modelo Preferido), and RBAC user store.
    Persists to `.rbr_settings_store.json` on disk with automatic in-memory fallback
    for read-only serverless environments (e.g., Vercel).
    """

    _store_path: Path = Path(__file__).resolve().parent.parent.parent / ".rbr_settings_store.json"
    _memory_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def set_store_path(cls, path: Path) -> None:
        cls._store_path = path
        cls._memory_cache = None

    @classmethod
    def load_state(cls, force_reload: bool = False) -> Dict[str, Any]:
        if cls._memory_cache is not None and not force_reload:
            return cls._memory_cache

        if cls._store_path.exists():
            try:
                raw = cls._store_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    data.setdefault("system_settings", _default_system_settings())
                    data.setdefault("user_credentials_store", {})
                    data.setdefault("users_store", _default_users_store())
                    cls._memory_cache = data
                    return cls._memory_cache
            except Exception:
                pass

        cls._memory_cache = {
            "system_settings": _default_system_settings(),
            "user_credentials_store": {},
            "users_store": _default_users_store(),
        }
        return cls._memory_cache

    @classmethod
    def save_state(cls) -> None:
        state = cls.load_state()
        try:
            cls._store_path.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            # Read-only filesystem in serverless production; keep _memory_cache active
            pass

    @classmethod
    def get_default_ai_model(cls) -> str:
        state = cls.load_state()
        return state["system_settings"].get("default_ai_model") or DEFAULT_AI_MODEL

    @classmethod
    def set_default_ai_model(cls, model: str, user_id: Optional[str] = None) -> str:
        clean_model = (model or "").strip() or DEFAULT_AI_MODEL
        state = cls.load_state()
        state["system_settings"]["default_ai_model"] = clean_model

        # Keep admin user record in sync
        for uid, udata in state["users_store"].items():
            if user_id is None or uid == user_id:
                udata["default_ai_model"] = clean_model

        # If a user has a preference entry without an explicit custom override, keep in sync
        if user_id and user_id in state["user_credentials_store"]:
            cred = state["user_credentials_store"][user_id]
            if not cred.get("custom_preferred_model"):
                cred["preferred_model"] = clean_model

        cls.save_state()
        return clean_model

    @classmethod
    def get_user_ai_settings(cls, user_id: str) -> Dict[str, Any]:
        state = cls.load_state()
        cred = state["user_credentials_store"].get(user_id)
        global_default = cls.get_default_ai_model()

        if not cred:
            return {
                "has_credential": False,
                "provider": "anthropic",
                "auth_mode": "oauth_token",
                "masked_token": None,
                "preferred_model": global_default,
                "default_ai_model": global_default,
                "last_tested_at": None,
            }

        has_token = bool(cred.get("encrypted_token"))
        return {
            "has_credential": has_token,
            "provider": cred.get("provider") or "anthropic",
            "auth_mode": cred.get("auth_mode") or "oauth_token",
            "masked_token": cred.get("masked_token") if has_token else None,
            "preferred_model": cred.get("preferred_model") or global_default,
            "default_ai_model": global_default,
            "last_tested_at": cred.get("last_tested_at"),
        }

    @classmethod
    def get_raw_user_credential(cls, user_id: str) -> Optional[Dict[str, Any]]:
        state = cls.load_state()
        return state["user_credentials_store"].get(user_id)

    @classmethod
    def save_user_ai_settings(
        cls,
        user_id: str,
        provider: Optional[str],
        preferred_model: Optional[str],
        encrypted_token: Optional[str] = None,
        masked_token: Optional[str] = None,
        auth_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = cls.load_state()
        existing = state["user_credentials_store"].get(user_id, {})
        global_default = cls.get_default_ai_model()

        clean_model = (preferred_model or "").strip() or existing.get("preferred_model") or global_default
        clean_provider = (provider or "").strip() or existing.get("provider") or "anthropic"
        now_iso = datetime.utcnow().isoformat()

        updated: Dict[str, Any] = {
            "user_id": user_id,
            "provider": clean_provider,
            "auth_mode": auth_mode or existing.get("auth_mode") or "oauth_token",
            "encrypted_token": encrypted_token if encrypted_token is not None else existing.get("encrypted_token"),
            "masked_token": masked_token if masked_token is not None else existing.get("masked_token"),
            "preferred_model": clean_model,
            "custom_preferred_model": True,
            "last_tested_at": now_iso if encrypted_token is not None else existing.get("last_tested_at"),
            "updated_at": now_iso,
        }
        state["user_credentials_store"][user_id] = updated

        if user_id in state["users_store"]:
            state["users_store"][user_id]["default_ai_model"] = clean_model

        cls.save_state()
        return updated

    @classmethod
    def update_last_tested(cls, user_id: str) -> None:
        state = cls.load_state()
        if user_id in state["user_credentials_store"]:
            state["user_credentials_store"][user_id]["last_tested_at"] = datetime.utcnow().isoformat()
            cls.save_state()

    @classmethod
    def get_users(cls) -> List[Dict[str, Any]]:
        state = cls.load_state()
        return list(state["users_store"].values())

    @classmethod
    def get_user(cls, user_id: str) -> Optional[Dict[str, Any]]:
        state = cls.load_state()
        return state["users_store"].get(user_id)

    @classmethod
    def toggle_user_role(cls, user_id: str) -> Optional[Dict[str, Any]]:
        state = cls.load_state()
        user = state["users_store"].get(user_id)
        if not user:
            return None
        user["is_admin"] = not user.get("is_admin", False)
        cls.save_state()
        return user

    @classmethod
    def toggle_user_status(cls, user_id: str) -> Optional[Dict[str, Any]]:
        state = cls.load_state()
        user = state["users_store"].get(user_id)
        if not user:
            return None
        user["is_active"] = not user.get("is_active", True)
        cls.save_state()
        return user

    @classmethod
    def count_active_credentials(cls) -> int:
        state = cls.load_state()
        return sum(1 for c in state["user_credentials_store"].values() if c.get("encrypted_token"))
