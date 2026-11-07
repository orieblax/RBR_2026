import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    ENV: str = "development"
    MASTER_ENCRYPTION_KEY: str = "Wk93Qkx4Y01XbmFqM19vRkV3c05mRE90TmlhSWl5d0hWZEtNYVhzQ0xYWT0="
    SUPABASE_URL: str = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://dummy.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "dummy-anon-key")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "dummy-service-role-key")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-key-for-local-dev-min-32-chars-long")
    API_SECRET_KEY: str = "dev-secret-key-change-in-production"

    class Config:
        env_file = ".env.local"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
