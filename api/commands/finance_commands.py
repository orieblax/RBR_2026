import copy
from typing import Dict, Any, Optional
from api.repositories.finance_repo import FinanceRepository
from api.domain.calculator import FinancialCalculator

class FinanceCommandService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.repo = FinanceRepository(user_id)

    def preview_mutation(self, mutation_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the exact before/after impact on Restante and Incl Pend
        without persisting changes yet (2-step safety workflow).
        """
        original_dataset = self.repo.get_dataset()
        temp_dataset = copy.deepcopy(original_dataset)

        kpis_before = FinancialCalculator.calculate_full_kpis(temp_dataset)

        # Apply mutation onto deepcopy
        if mutation_type == "add_ledger_adjustment":
            parent_type = payload.get("parent_type", "liquid_account")
            target_name = payload.get("target_name", "")
            amount = float(payload.get("amount", 0.0))
            note = payload.get("note", "")

            adj = {
                "amount": amount,
                "factor": 1.0,
                "is_active": True,
                "note": note
            }
            target_list = temp_dataset.get("liquid_accounts" if parent_type == "liquid_account" else "receivables", [])
            for item in target_list:
                if item.get("name", "").lower() == target_name.lower():
                    item.setdefault("adjustments", []).append(adj)
                    break

        elif mutation_type == "toggle_pending_status":
            item_name = payload.get("item_name", "")
            is_paid = payload.get("is_paid", True)
            for exp in temp_dataset.get("recurring_expenses", []):
                if exp.get("name", "").lower() == item_name.lower():
                    exp["is_pending"] = not is_paid
                    break

        elif mutation_type == "update_item_amount":
            category = payload.get("category", "recurring_expenses")
            item_name = payload.get("name", "")
            new_amount = float(payload.get("new_amount", 0.0))
            for item in temp_dataset.get(category, []):
                if item.get("name", "").lower() == item_name.lower():
                    if category == "recurring_expenses":
                        item["recurrent_base"] = new_amount
                    else:
                        item["base_amount"] = new_amount
                    break

        kpis_after = FinancialCalculator.calculate_full_kpis(temp_dataset)

        delta_restante = kpis_after.restante - kpis_before.restante
        delta_incl_pend = kpis_after.incl_pend - kpis_before.incl_pend

        return {
            "mutation_type": mutation_type,
            "payload": payload,
            "kpis_before": {
                "restante": kpis_before.restante,
                "incl_pend": kpis_before.incl_pend,
                "total_actual": kpis_before.total_actual,
                "gastos_mes": kpis_before.gastos_mes
            },
            "kpis_after": {
                "restante": kpis_after.restante,
                "incl_pend": kpis_after.incl_pend,
                "total_actual": kpis_after.total_actual,
                "gastos_mes": kpis_after.gastos_mes
            },
            "impact_delta": {
                "delta_restante": delta_restante,
                "delta_incl_pend": delta_incl_pend
            }
        }

    def execute_add_adjustment(self, parent_type: str, target_name: str, amount: float, note: str = "") -> Dict[str, Any]:
        result = self.repo.add_adjustment(parent_type, target_name, amount, note)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": "success",
            "message": f"Ajuste de ${amount:,.2f} aplicado a {result['target_name']}",
            "adjustment": result["adjustment"],
            "kpis": kpis.model_dump()
        }

    def execute_remove_adjustment(self, adjustment_id: str) -> Dict[str, Any]:
        success = self.repo.remove_adjustment(adjustment_id)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": "success" if success else "error",
            "message": "Movimiento eliminado exitosamente" if success else "Movimiento no encontrado",
            "kpis": kpis.model_dump()
        }

    def execute_toggle_pending(self, category: str, item_name: str, is_paid: bool) -> Dict[str, Any]:
        if category == "recurring_expenses":
            updated = self.repo.toggle_expense_pending(item_name, is_paid)
            action_desc = "marcado como pagado (*0)" if is_paid else "marcado como pendiente (*1)"
        else:
            updated = self.repo.toggle_receivable_pending(item_name, is_paid)
            action_desc = "marcado como cobrado" if is_paid else "marcado como pendiente"

        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": "success" if updated else "error",
            "message": f"{item_name} {action_desc}",
            "updated_item": updated,
            "kpis": kpis.model_dump()
        }

    def execute_update_item(self, category: str, item_name: str, new_amount: float) -> Dict[str, Any]:
        updated = self.repo.update_item_amount(category, item_name, new_amount)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": "success" if updated else "error",
            "message": f"{item_name} actualizado a ${new_amount:,.2f}",
            "updated_item": updated,
            "kpis": kpis.model_dump()
        }

    def execute_update_goal(self, goal_name: str, allocated_delta: float) -> Dict[str, Any]:
        updated = self.repo.update_financial_goal(goal_name, allocated_delta)
        return {
            "status": "success" if updated else "error",
            "message": f"Meta {goal_name} actualizada",
            "updated_goal": updated
        }
