from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from api.core.config import get_settings
from api.core.security import get_current_user, require_admin, vault, TokenVault
from api.seed import generate_seed_data
from api.queries.finance_queries import FinanceQueryService
from api.commands.finance_commands import FinanceCommandService
from api.agent.llm_factory import LLMFactory
from api.agent.finance_agent import FinanceAgent
from api.core.rate_limit import RateLimiterMiddleware

settings = get_settings()

app = FastAPI(
    title="RBR Finance Manager API",
    version="1.0.0",
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json"
)

# Rate Limiter Middleware
app.add_middleware(RateLimiterMiddleware, max_requests=120, window_seconds=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for AI credentials and admin user management (fallback/dev mode)
user_credentials_store: Dict[str, Dict[str, Any]] = {}
users_store: Dict[str, Dict[str, Any]] = {
    "00000000-0000-0000-0000-000000000001": {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "albeiro@rbrfinance.com",
        "full_name": "Albeiro Yaime",
        "is_admin": True,
        "is_active": True,
        "default_ai_model": "claude-3-7-sonnet-latest",
        "created_at": "2026-01-01T00:00:00Z"
    }
}
system_settings = {
    "default_ai_model": "claude-3-7-sonnet-latest",
}

@app.get("/api/py/health")
def health_check():
    return {
        "status": "ok",
        "service": "rbr-finance-api",
        "env": settings.ENV,
        "supabase_configured": not settings.SUPABASE_URL.startswith("https://dummy")
    }

class SeedRequest(BaseModel):
    user_id: Optional[str] = None

@app.post("/api/py/seed")
def seed_endpoint(payload: Optional[SeedRequest] = None, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = (payload and payload.user_id) or current_user["user_id"]
    data = generate_seed_data(user_id)
    return {
        "status": "success",
        "message": "Datos iniciales de Excel 2026 generados exitosamente",
        "user_id": user_id,
        "counts": {
            "liquid_accounts": len(data["liquid_accounts"]),
            "investment_assets": len(data["investment_assets"]),
            "monthly_extras": len(data["monthly_extras"]),
            "receivables": len(data["receivables"]),
            "income_sources": len(data["income_sources"]),
            "recurring_expenses": len(data["recurring_expenses"]),
            "financial_goals": len(data["financial_goals"]),
        }
    }

# --- CQRS Queries ---

@app.get("/api/py/dashboard/summary")
def get_dashboard_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceQueryService(current_user["user_id"])
    return service.get_dashboard_summary()

@app.get("/api/py/finance/investment-capacity")
def get_investment_capacity(
    period: str = Query("month", regex="^(month|year)$"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    service = FinanceQueryService(current_user["user_id"])
    return service.get_investment_capacity(period=period)

@app.get("/api/py/finance/expenses")
def get_expenses_breakdown(current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceQueryService(current_user["user_id"])
    return service.get_expenses_breakdown()

@app.get("/api/py/finance/search")
def search_history(
    q: str = Query(..., min_length=1),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    service = FinanceQueryService(current_user["user_id"])
    return service.search_financial_history(q)

# --- CQRS Commands ---

class AddAdjustmentRequest(BaseModel):
    parent_type: str = "liquid_account"
    target_name: str
    amount: float
    note: str = ""

@app.post("/api/py/finance/adjustment")
def add_adjustment(payload: AddAdjustmentRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.execute_add_adjustment(
        payload.parent_type, payload.target_name, payload.amount, payload.note
    )

@app.delete("/api/py/finance/adjustment/{adjustment_id}")
def delete_adjustment(adjustment_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.execute_remove_adjustment(adjustment_id)

class TogglePendingRequest(BaseModel):
    category: str = "recurring_expenses"
    item_name: str
    is_paid: bool

@app.post("/api/py/finance/toggle-pending")
def toggle_pending(payload: TogglePendingRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.execute_toggle_pending(payload.category, payload.item_name, payload.is_paid)

class UpdateAmountRequest(BaseModel):
    category: str
    item_name: str
    new_amount: float

@app.post("/api/py/finance/update-amount")
def update_amount(payload: UpdateAmountRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.execute_update_item(payload.category, payload.item_name, payload.new_amount)

class UpdateGoalRequest(BaseModel):
    goal_name: str
    allocated_delta: float

@app.post("/api/py/finance/goal")
def update_goal(payload: UpdateGoalRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.execute_update_goal(payload.goal_name, payload.allocated_delta)

class PreviewMutationRequest(BaseModel):
    mutation_type: str
    payload: Dict[str, Any]

@app.post("/api/py/finance/preview")
def preview_mutation(payload: PreviewMutationRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    service = FinanceCommandService(current_user["user_id"])
    return service.preview_mutation(payload.mutation_type, payload.payload)

# --- Phase 3: AI Credentials Setup-Token Module ---

class SaveAICredentialRequest(BaseModel):
    provider: str
    token: str
    preferred_model: Optional[str] = "claude-3-7-sonnet-latest"

@app.get("/api/py/settings/ai")
def get_ai_credentials(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["user_id"]
    cred = user_credentials_store.get(user_id)
    if not cred:
        return {
            "has_credential": False,
            "provider": None,
            "auth_mode": None,
            "masked_token": None,
            "preferred_model": system_settings["default_ai_model"],
            "last_tested_at": None
        }
    return {
        "has_credential": True,
        "provider": cred.get("provider"),
        "auth_mode": cred.get("auth_mode"),
        "masked_token": cred.get("masked_token"),
        "preferred_model": cred.get("preferred_model"),
        "last_tested_at": cred.get("last_tested_at")
    }

@app.post("/api/py/settings/ai")
def save_ai_credentials(payload: SaveAICredentialRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["user_id"]
    raw_token = payload.token.strip()
    classification = TokenVault.classify_token(raw_token)
    
    encrypted = vault.encrypt(raw_token)
    masked = TokenVault.mask_token(raw_token)

    cred = {
        "user_id": user_id,
        "provider": payload.provider or classification["provider"],
        "auth_mode": classification["auth_mode"],
        "encrypted_token": encrypted,
        "masked_token": masked,
        "preferred_model": payload.preferred_model or "claude-3-7-sonnet-latest",
        "last_tested_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    user_credentials_store[user_id] = cred

    return {
        "status": "success",
        "message": f"Credencial {classification['label']} cifrada y almacenada exitosamente",
        "provider": cred["provider"],
        "auth_mode": cred["auth_mode"],
        "masked_token": masked,
        "preferred_model": cred["preferred_model"]
    }

class TestAICredentialRequest(BaseModel):
    provider: Optional[str] = None
    token: Optional[str] = None
    model: Optional[str] = None

@app.post("/api/py/settings/ai/test")
def test_ai_connection(payload: TestAICredentialRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = current_user["user_id"]
    token_to_test = payload.token

    if not token_to_test:
        stored = user_credentials_store.get(user_id)
        if stored and stored.get("encrypted_token"):
            token_to_test = vault.decrypt(stored["encrypted_token"])
        else:
            raise HTTPException(status_code=400, detail="No hay credenciales registradas para probar.")

    result = LLMFactory.ping_test_token(token_to_test, provider=payload.provider, model=payload.model)
    if result["status"] == "success" and user_id in user_credentials_store:
        user_credentials_store[user_id]["last_tested_at"] = datetime.utcnow().isoformat()
    return result

# --- Phase 3: Admin Module ---

@app.get("/api/py/admin/users")
def get_admin_users(admin: Dict[str, Any] = Depends(require_admin)):
    return list(users_store.values())

@app.post("/api/py/admin/users/{target_user_id}/toggle-role")
def toggle_user_role(target_user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    if target_user_id not in users_store:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    users_store[target_user_id]["is_admin"] = not users_store[target_user_id]["is_admin"]
    return {
        "status": "success",
        "message": f"Rol de administrador actualizado",
        "user": users_store[target_user_id]
    }

@app.post("/api/py/admin/users/{target_user_id}/toggle-status")
def toggle_user_status(target_user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    if target_user_id not in users_store:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    users_store[target_user_id]["is_active"] = not users_store[target_user_id]["is_active"]
    return {
        "status": "success",
        "message": f"Estado de usuario actualizado",
        "user": users_store[target_user_id]
    }

@app.get("/api/py/admin/diagnostics")
def get_admin_diagnostics(admin: Dict[str, Any] = Depends(require_admin)):
    return {
        "status": "healthy",
        "system": {
            "environment": settings.ENV,
            "supabase_connected": not settings.SUPABASE_URL.startswith("https://dummy"),
            "encryption_vault_active": True,
            "total_users": len(users_store),
            "stored_ai_credentials": len(user_credentials_store),
            "default_ai_model": system_settings["default_ai_model"]
        }
    }

class UpdateDefaultModelRequest(BaseModel):
    model: str

@app.post("/api/py/admin/default-model")
def update_default_ai_model(payload: UpdateDefaultModelRequest, admin: Dict[str, Any] = Depends(require_admin)):
    system_settings["default_ai_model"] = payload.model
    return {
        "status": "success",
        "message": f"Modelo por defecto actualizado a {payload.model}",
        "default_ai_model": payload.model
    }

# --- Phase 4: Agno Voice Agent & 2-Step Confirmation ---

class VoiceCommandRequest(BaseModel):
    command: str

@app.post("/api/py/voice/command")
def process_voice_command(payload: VoiceCommandRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    agent = FinanceAgent(current_user["user_id"])
    return agent.process_voice_command(payload.command)

class ActionActionRequest(BaseModel):
    action_id: str

@app.post("/api/py/voice/confirm")
def confirm_voice_action(payload: ActionActionRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    return FinanceAgent.confirm_action(payload.action_id)

@app.post("/api/py/voice/cancel")
def cancel_voice_action(payload: ActionActionRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    return FinanceAgent.cancel_action(payload.action_id)
