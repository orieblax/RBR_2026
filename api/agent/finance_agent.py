import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from api.queries.finance_queries import FinanceQueryService
from api.commands.finance_commands import FinanceCommandService
from api.domain.calculator import FinancialCalculator

# In-memory store for pending staged actions (2-Step Safety Confirmation)
pending_voice_actions_store: Dict[str, Dict[str, Any]] = {}
audit_logs_store: List[Dict[str, Any]] = []

SPANISH_SYSTEM_PROMPT = """Eres el Agente Financiero de RBR Finance Manager, experto en finanzas personales y optimización de excedentes invertibles en Colombia (es-CO).
Te riges estrictamente por las fórmulas de EXCEL_SPEC.md y Gastos Albeiro.xlsx:
- Tu KPI principal es 'Incl Pend' (Disponible para Invertir Este Mes = Restante + Pend - Total Gastos = $1,999,733.33).
- Las cuentas de liquidez tienen micro-ledgers inline (como Daviplata y Caja social).
- Los egresos pueden ser recurrentes o pendientes (*1 activo, *0 pagado).
- NUNCA ejecutes modificaciones directamente sin pasar por la herramienta de propuesta staged (propose_*) para que el usuario confirme el cambio."""

class FinanceAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.query_service = FinanceQueryService(user_id)
        self.command_service = FinanceCommandService(user_id)

    # --- Read Tools ---
    def get_investment_capacity(self, period: str = "month") -> Dict[str, Any]:
        return self.query_service.get_investment_capacity(period=period)

    def get_account_details(self, name: str) -> Optional[Dict[str, Any]]:
        return self.query_service.get_account_details(name)

    def get_expenses_breakdown(self) -> Dict[str, Any]:
        return self.query_service.get_expenses_breakdown()

    def search_financial_history(self, query: str) -> List[Dict[str, Any]]:
        return self.query_service.search_financial_history(query)

    # --- Write Proposal Tools (Staged Execution) ---
    def propose_ledger_adjustment(self, target_name: str, amount_delta: float, reason: str = "") -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "parent_type": "liquid_account",
            "target_name": target_name,
            "amount": float(amount_delta),
            "note": reason or "Ajuste propuesto por voz"
        }
        preview = self.command_service.preview_mutation("add_ledger_adjustment", payload)
        sign = "+" if amount_delta >= 0 else ""
        preview_summary = f"Agregar movimiento de {sign}${amount_delta:,.0f} COP en cuenta {target_name} ({reason or 'Ajuste'})"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_ledger_adjustment",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_toggle_pending_status(self, item_name: str, is_paid: bool = True) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "category": "recurring_expenses",
            "item_name": item_name,
            "is_paid": is_paid
        }
        preview = self.command_service.preview_mutation("toggle_pending_status", payload)
        state_text = "marcar como pagado (*0)" if is_paid else "marcar como pendiente (*1)"
        preview_summary = f"{state_text.capitalize()} el gasto {item_name}"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_toggle_pending_status",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_update_item(self, category: str, name: str, new_amount: float) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "category": category,
            "name": name,
            "new_amount": float(new_amount)
        }
        preview = self.command_service.preview_mutation("update_item_amount", payload)
        preview_summary = f"Actualizar monto de {name} a ${new_amount:,.0f} COP"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_update_item",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    # --- Confirmation & Cancel Handlers ---
    @classmethod
    def confirm_action(cls, action_id: str) -> Dict[str, Any]:
        action = pending_voice_actions_store.get(action_id)
        if not action or action.get("status") != "pending":
            return {"status": "error", "message": "Acción no encontrada o ya procesada"}

        cmd_svc = FinanceCommandService(action["user_id"])
        tool = action["tool_name"]
        payload = action["action_payload"]
        exec_result = {}

        if tool == "propose_ledger_adjustment":
            exec_result = cmd_svc.execute_add_adjustment(
                payload["parent_type"], payload["target_name"], payload["amount"], payload["note"]
            )
        elif tool == "propose_toggle_pending_status":
            exec_result = cmd_svc.execute_toggle_pending(
                payload["category"], payload["item_name"], payload["is_paid"]
            )
        elif tool == "propose_update_item":
            exec_result = cmd_svc.execute_update_item(
                payload["category"], payload["name"], payload["new_amount"]
            )

        action["status"] = "confirmed"
        action["confirmed_at"] = datetime.utcnow().isoformat()

        # Audit log entry
        audit_logs_store.append({
            "id": str(uuid.uuid4()),
            "user_id": action["user_id"],
            "action": tool,
            "preview_summary": action["preview_summary"],
            "impact_delta": action["impact_delta"],
            "source": "voice",
            "created_at": datetime.utcnow().isoformat()
        })

        return {
            "status": "success",
            "message": f"¡Acción confirmada! {action['preview_summary']}",
            "execution": exec_result
        }

    @classmethod
    def cancel_action(cls, action_id: str) -> Dict[str, Any]:
        action = pending_voice_actions_store.get(action_id)
        if action:
            action["status"] = "cancelled"
            action["cancelled_at"] = datetime.utcnow().isoformat()
        return {"status": "success", "message": "Acción cancelada"}

    # --- Spanish Voice Intent Engine ---
    def process_voice_command(self, text: str) -> Dict[str, Any]:
        clean = text.strip().lower()

        # Check for immediate "confirmar" voice word if there is an active pending action
        if clean in ("confirmar", "sí confirmar", "confirmo", "dale", "sí", "aprobar"):
            for act_id, act in reversed(list(pending_voice_actions_store.items())):
                if act.get("user_id") == self.user_id and act.get("status") == "pending":
                    res = self.confirm_action(act_id)
                    return {"type": "confirmed", "reply": res["message"], "needs_refresh": True}

        if clean in ("cancelar", "no", "descartar", "cancela"):
            for act_id, act in reversed(list(pending_voice_actions_store.items())):
                if act.get("user_id") == self.user_id and act.get("status") == "pending":
                    res = self.cancel_action(act_id)
                    return {"type": "cancelled", "reply": "Acción descartada", "needs_refresh": False}

        # 1. Intent: Toggle Paid Expense (*0)
        # e.g.: "marcar pagado energía 20", "pagué movistar", "marcar pagado gas 15"
        if "marcar pagado" in clean or "pagado" in clean or "pague" in clean or "pagó" in clean:
            # find expense match
            expenses = self.query_service.repo.get_recurring_expenses()
            for exp in expenses:
                name_clean = exp["name"].lower()
                # Check tokens
                tokens = name_clean.split()
                if any(t in clean for t in tokens if len(t) > 2):
                    staged = self.propose_toggle_pending_status(exp["name"], is_paid=True)
                    return {
                        "type": "stage_action",
                        "staged_action": staged,
                        "reply": f"Propuesta: {staged['preview_summary']}. ¿Confirmas el cambio?"
                    }

        # 2. Intent: Add Ledger Adjustment
        # e.g. "agregar gasto en daviplata de 50000 por mercado", "abono a camila 20 de 100000", "ajuste en caja social 20000"
        amount_match = re.search(r"(\d+[\.\d+]*)", clean.replace(",", ""))
        if amount_match and ("agregar" in clean or "gasto" in clean or "abono" in clean or "ajuste" in clean or "ingreso" in clean):
            amount = float(amount_match.group(1))
            if "gasto" in clean or "retiro" in clean or "descuento" in clean:
                amount = -abs(amount)
            else:
                amount = abs(amount)

            # Check account
            account_name = "Daviplata"
            if "caja social" in clean:
                account_name = "Caja social"
            elif "nequi" in clean:
                account_name = "Nequi"
            elif "bolsillo" in clean:
                account_name = "Bolsillo"
            elif "camila" in clean:
                account_name = "Camila 20"
            elif "ana" in clean:
                account_name = "Ana 26"
            elif "marisol" in clean:
                account_name = "Marisol 23"

            staged = self.propose_ledger_adjustment(account_name, amount, "Movimiento por comando de voz")
            return {
                "type": "stage_action",
                "staged_action": staged,
                "reply": f"Propuesta: {staged['preview_summary']}. ¿Confirmas el cambio?"
            }

        # 3. Intent: Read Investment Capacity
        # e.g.: "¿cuánto puedo invertir este mes?", "capacidad de inversión", "cuánto me queda para invertir"
        if "invertir" in clean or "capacidad" in clean or "excedente" in clean or "incl pend" in clean:
            cap = self.get_investment_capacity("month")
            val = cap["capacidad_invertible"]
            return {
                "type": "read",
                "reply": f"Tu capacidad disponible para invertir este mes (Incl Pend) es de ${val:,.0f} COP. (Fórmula: Restante + Pend - Egresos).",
                "data": cap
            }

        # 4. Intent: Read Account details / balance
        # e.g.: "¿cuánto tengo en daviplata?", "saldo caja social"
        if "cuánto" in clean or "saldo" in clean or "estado" in clean:
            summary = self.query_service.get_dashboard_summary()
            for acc in summary["liquid_accounts"]:
                if acc["name"].lower() in clean:
                    return {
                        "type": "read",
                        "reply": f"El saldo actual en {acc['name']} es de ${acc['calculated_total']:,.0f} COP con {len(acc.get('adjustments', []))} movimientos inline.",
                        "data": acc
                    }

        # Default fallback: general summary
        kpis = self.query_service.get_dashboard_summary()["kpis"]
        return {
            "type": "read",
            "reply": f"Actualmente tienes ${kpis['total_actual']:,.0f} COP en liquidez actual, ${kpis['restante']:,.0f} COP de liquidez restante y ${kpis['incl_pend']:,.0f} COP disponible para invertir este mes.",
            "data": kpis
        }
