import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from api.core.config import get_settings
from api.seed import generate_seed_data

settings = get_settings()

class FinanceRepository:
    """
    Repository pattern encapsulating persistence for all financial entities.
    Supports Supabase PostgreSQL + RLS, and includes an in-memory/JSON store
    for development, testing, and offline modes.
    """
    _local_store: Dict[str, Dict[str, Any]] = {}

    def __init__(self, user_id: str):
        self.user_id = user_id
        if self.user_id not in self._local_store:
            # Seed default Excel 2026 data
            self._local_store[self.user_id] = generate_seed_data(self.user_id)

    def get_dataset(self) -> Dict[str, Any]:
        return self._local_store[self.user_id]

    def get_liquid_accounts(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("liquid_accounts", [])

    def get_receivables(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("receivables", [])

    def get_income_sources(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("income_sources", [])

    def get_recurring_expenses(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("recurring_expenses", [])

    def get_monthly_extras(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("monthly_extras", [])

    def get_investment_assets(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("investment_assets", [])

    def get_financial_goals(self) -> List[Dict[str, Any]]:
        return self._local_store[self.user_id].get("financial_goals", [])

    def add_adjustment(
        self, 
        parent_type: str, 
        parent_identifier: str, 
        amount: float, 
        note: str = ""
    ) -> Dict[str, Any]:
        dataset = self._local_store[self.user_id]
        adj = {
            "id": str(uuid.uuid4()),
            "user_id": self.user_id,
            "parent_type": parent_type,
            "amount": float(amount),
            "factor": 1.0,
            "is_active": True,
            "note": note,
            "created_at": datetime.utcnow().isoformat()
        }

        # Target list
        target_list = []
        if parent_type == "liquid_account":
            target_list = dataset.get("liquid_accounts", [])
        elif parent_type == "receivable":
            target_list = dataset.get("receivables", [])
        
        found = False
        target_name = parent_identifier
        for item in target_list:
            if item.get("id") == parent_identifier or item.get("name", "").lower() == parent_identifier.lower():
                if "adjustments" not in item:
                    item["adjustments"] = []
                item["adjustments"].append(adj)
                target_name = item.get("name", "")
                found = True
                break
        
        if not found and target_list:
            # Fallback to first matching or default
            target_list[0].setdefault("adjustments", []).append(adj)
            target_name = target_list[0].get("name", "")

        return {"adjustment": adj, "target_name": target_name}

    def remove_adjustment(self, adjustment_id: str) -> bool:
        dataset = self._local_store[self.user_id]
        for category in ["liquid_accounts", "receivables"]:
            for item in dataset.get(category, []):
                adjs = item.get("adjustments", [])
                for i, adj in enumerate(adjs):
                    if adj.get("id") == adjustment_id:
                        adjs.pop(i)
                        return True
        return False

    def toggle_expense_pending(self, identifier: str, is_paid: bool) -> Optional[Dict[str, Any]]:
        dataset = self._local_store[self.user_id]
        for exp in dataset.get("recurring_expenses", []):
            if exp.get("id") == identifier or exp.get("name", "").lower() == identifier.lower():
                # In Excel: paid means is_pending is False (*0)
                exp["is_pending"] = not is_paid
                return exp
        return None

    def toggle_receivable_pending(self, identifier: str, is_collected: bool) -> Optional[Dict[str, Any]]:
        dataset = self._local_store[self.user_id]
        for rec in dataset.get("receivables", []):
            if rec.get("id") == identifier or rec.get("name", "").lower() == identifier.lower():
                rec["is_pending"] = not is_collected
                return rec
        return None

    def update_item_amount(self, category: str, identifier: str, new_amount: float) -> Optional[Dict[str, Any]]:
        dataset = self._local_store[self.user_id]
        items = dataset.get(category, [])
        for item in items:
            if item.get("id") == identifier or item.get("name", "").lower() == identifier.lower():
                if category == "recurring_expenses":
                    item["recurrent_base"] = float(new_amount)
                else:
                    item["base_amount"] = float(new_amount)
                return item
        return None

    def update_financial_goal(self, identifier: str, allocated_delta: float) -> Optional[Dict[str, Any]]:
        dataset = self._local_store[self.user_id]
        for goal in dataset.get("financial_goals", []):
            if goal.get("id") == identifier or goal.get("name", "").lower() == identifier.lower():
                goal["allocated_amount"] = max(0.0, float(goal.get("allocated_amount", 0.0)) + float(allocated_delta))
                return goal
        return None

    def set_account_balance(
        self,
        parent_type: str,
        parent_identifier: str,
        new_balance: float,
        note: str = ""
    ) -> Dict[str, Any]:
        dataset = self._local_store[self.user_id]
        target_list = dataset.get("liquid_accounts" if parent_type == "liquid_account" else "receivables", [])

        target_item = None
        for item in target_list:
            if item.get("id") == parent_identifier or item.get("name", "").lower() == parent_identifier.lower():
                target_item = item
                break

        if not target_item and target_list:
            # Fallback search by token
            clean_id = parent_identifier.lower()
            for item in target_list:
                if clean_id in item.get("name", "").lower() or item.get("name", "").lower() in clean_id:
                    target_item = item
                    break

        if not target_item:
            return {"status": "error", "message": f"Cuenta {parent_identifier} no encontrada", "target_name": parent_identifier}

        from api.domain.calculator import FinancialCalculator
        current_val = FinancialCalculator.calculate_liquid_account_total(target_item)
        target_balance = float(new_balance)
        delta = target_balance - current_val

        # If account has no adjustments and base_amount is used, set base_amount directly
        if len(target_item.get("adjustments", [])) == 0 and float(target_item.get("base_amount", 0.0)) > 0:
            target_item["base_amount"] = target_balance
        else:
            # Add inline reconciliation adjustment
            adj = {
                "id": str(uuid.uuid4()),
                "user_id": self.user_id,
                "parent_type": parent_type,
                "amount": delta,
                "factor": 1.0,
                "is_active": True,
                "note": note or "Actualización de saldo",
                "created_at": datetime.utcnow().isoformat()
            }
            target_item.setdefault("adjustments", []).append(adj)

        return {
            "status": "success",
            "target_name": target_item.get("name", parent_identifier),
            "delta": delta,
            "new_balance": target_balance,
            "item": target_item
        }

    def collect_receivable(
        self,
        identifier: str,
        is_collected: bool = True,
        dest_account: Optional[str] = None
    ) -> Dict[str, Any]:
        from api.domain.calculator import FinancialCalculator
        dataset = self._local_store[self.user_id]
        fiducia_cap = 32560000.0
        for inv in dataset.get("investment_assets", []):
            if inv.get("asset_type") == "fiducia":
                fiducia_cap = float(inv.get("base_amount", 32560000.0))
        fiducia_yield = FinancialCalculator.calculate_fiducia_monthly_yield(fiducia_cap)
        sum_extras = sum(FinancialCalculator.calculate_monthly_extra_value(e) for e in dataset.get("monthly_extras", []))

        target_rec = None
        for rec in dataset.get("receivables", []):
            if rec.get("id") == identifier or rec.get("name", "").lower() == identifier.lower() or identifier.lower() in rec.get("name", "").lower():
                target_rec = rec
                break

        if not target_rec:
            return {"status": "error", "message": f"Cuenta por cobrar {identifier} no encontrada"}

        # Calculate value while active/pending
        was_pending = target_rec.get("is_pending", True)
        target_rec["is_pending"] = True
        amount = FinancialCalculator.calculate_receivable_value(target_rec, fiducia_yield, sum_extras)
        target_rec["is_pending"] = not is_collected

        adj_res = None
        if is_collected and dest_account and amount > 0:
            adj_res = self.add_adjustment("liquid_account", dest_account, amount, f"Cobro {target_rec['name']}")

        return {
            "status": "success",
            "receivable": target_rec,
            "was_pending": was_pending,
            "collected_amount": amount,
            "dest_account": adj_res["target_name"] if adj_res else None
        }

    def pay_expense_from_account(
        self,
        expense_identifier: str,
        source_account: str
    ) -> Dict[str, Any]:
        dataset = self._local_store[self.user_id]
        target_exp = None
        for exp in dataset.get("recurring_expenses", []):
            if exp.get("id") == expense_identifier or exp.get("name", "").lower() == expense_identifier.lower() or expense_identifier.lower() in exp.get("name", "").lower():
                target_exp = exp
                break

        if not target_exp:
            return {"status": "error", "message": f"Gasto {expense_identifier} no encontrado"}

        amount = float(target_exp.get("pending_base") or target_exp.get("recurrent_base", 0.0))
        target_exp["is_pending"] = False

        adj_res = self.add_adjustment("liquid_account", source_account, -abs(amount), f"Pago {target_exp['name']}")
        return {
            "status": "success",
            "expense": target_exp,
            "paid_amount": amount,
            "source_account": adj_res["target_name"]
        }

    def transfer_between_accounts(
        self,
        from_account: str,
        to_account: str,
        amount: float,
        note: str = ""
    ) -> Dict[str, Any]:
        transfer_val = abs(float(amount))
        out_res = self.add_adjustment(
            "liquid_account",
            from_account,
            -transfer_val,
            note or f"Transferencia a {to_account}"
        )
        in_res = self.add_adjustment(
            "liquid_account",
            to_account,
            transfer_val,
            note or f"Transferencia desde {out_res['target_name']}"
        )
        return {
            "status": "success",
            "from_account": out_res["target_name"],
            "to_account": in_res["target_name"],
            "amount": transfer_val
        }

    def pop_last_adjustment(self, account_identifier: Optional[str] = None) -> Dict[str, Any]:
        dataset = self._local_store[self.user_id]
        accounts = dataset.get("liquid_accounts", [])

        target_acc = None
        if account_identifier:
            for acc in accounts:
                if acc.get("name", "").lower() == account_identifier.lower() or account_identifier.lower() in acc.get("name", "").lower():
                    target_acc = acc
                    break

        if target_acc:
            adjs = target_acc.get("adjustments", [])
            if adjs:
                removed = adjs.pop()
                return {"status": "success", "account_name": target_acc["name"], "removed_adjustment": removed}
            return {"status": "error", "message": f"No hay movimientos para deshacer en {target_acc['name']}"}

        # Fallback: find first account with adjustments
        for acc in accounts:
            adjs = acc.get("adjustments", [])
            if adjs:
                removed = adjs.pop()
                return {"status": "success", "account_name": acc["name"], "removed_adjustment": removed}

        return {"status": "error", "message": "No se encontraron movimientos recientes para deshacer"}
