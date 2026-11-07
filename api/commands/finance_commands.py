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
        target_item: Optional[Dict[str, Any]] = None

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
                if item.get("name", "").lower() == target_name.lower() or target_name.lower() in item.get("name", "").lower():
                    before_val = FinancialCalculator.calculate_liquid_account_total(item)
                    item.setdefault("adjustments", []).append(adj)
                    after_val = FinancialCalculator.calculate_liquid_account_total(item)
                    target_item = {
                        "name": item.get("name", target_name),
                        "category_label": "Cuenta Líquida" if parent_type == "liquid_account" else "Cuenta por Cobrar",
                        "before_value": before_val,
                        "after_value": after_val,
                        "delta": amount,
                        "note": note or ("Gasto" if amount < 0 else "Abono")
                    }
                    break

        elif mutation_type == "set_account_balance":
            parent_type = payload.get("parent_type", "liquid_account")
            target_name = payload.get("target_name", "")
            new_balance = float(payload.get("new_balance", 0.0))
            note = payload.get("note", "")

            target_list = temp_dataset.get("liquid_accounts" if parent_type == "liquid_account" else "receivables", [])
            for item in target_list:
                if item.get("name", "").lower() == target_name.lower() or target_name.lower() in item.get("name", "").lower():
                    before_val = FinancialCalculator.calculate_liquid_account_total(item)
                    delta = new_balance - before_val
                    if len(item.get("adjustments", [])) == 0 and float(item.get("base_amount", 0.0)) > 0:
                        item["base_amount"] = new_balance
                    else:
                        item.setdefault("adjustments", []).append({
                            "amount": delta,
                            "factor": 1.0,
                            "is_active": True,
                            "note": note or "Actualización de saldo"
                        })
                    after_val = new_balance
                    target_item = {
                        "name": item.get("name", target_name),
                        "category_label": "Cuenta Líquida" if parent_type == "liquid_account" else "Cuenta por Cobrar",
                        "before_value": before_val,
                        "after_value": after_val,
                        "delta": delta,
                        "note": note or "Actualización de saldo"
                    }
                    break

        elif mutation_type == "toggle_pending_status":
            item_name = payload.get("item_name", "")
            is_paid = payload.get("is_paid", True)
            for exp in temp_dataset.get("recurring_expenses", []):
                if exp.get("name", "").lower() == item_name.lower() or item_name.lower() in exp.get("name", "").lower():
                    cost = float(exp.get("recurrent_base", 0.0))
                    before_status = "Pendiente" if exp.get("is_pending", True) else "Pagado"
                    exp["is_pending"] = not is_paid
                    after_status = "Pagado" if is_paid else "Pendiente"
                    target_item = {
                        "name": exp.get("name", item_name),
                        "category_label": "Gasto Recurrente",
                        "before_value": cost if before_status == "Pendiente" else 0.0,
                        "after_value": 0.0 if is_paid else cost,
                        "before_status": before_status,
                        "after_status": after_status,
                        "delta": -cost if is_paid else cost,
                        "note": "Marcar como pagado (*0)" if is_paid else "Marcar como pendiente (*1)"
                    }
                    break

        elif mutation_type == "update_item_amount":
            category = payload.get("category", "recurring_expenses")
            item_name = payload.get("name", "")
            new_amount = float(payload.get("new_amount", 0.0))
            for item in temp_dataset.get(category, []):
                if item.get("name", "").lower() == item_name.lower():
                    before_val = float(item.get("recurrent_base", item.get("base_amount", 0.0)))
                    if category == "recurring_expenses":
                        item["recurrent_base"] = new_amount
                    else:
                        item["base_amount"] = new_amount
                    target_item = {
                        "name": item.get("name", item_name),
                        "category_label": category,
                        "before_value": before_val,
                        "after_value": new_amount,
                        "delta": new_amount - before_val,
                        "note": "Actualizar monto"
                    }
                    break

        elif mutation_type == "collect_receivable":
            item_name = payload.get("item_name", "")
            is_collected = payload.get("is_collected", True)
            dest_account = payload.get("dest_account")

            fiducia_cap = 32560000.0
            for inv in temp_dataset.get("investment_assets", []):
                if inv.get("asset_type") == "fiducia":
                    fiducia_cap = float(inv.get("base_amount", 32560000.0))
            fiducia_yield = FinancialCalculator.calculate_fiducia_monthly_yield(fiducia_cap)
            sum_extras = sum(FinancialCalculator.calculate_monthly_extra_value(e) for e in temp_dataset.get("monthly_extras", []))

            for rec in temp_dataset.get("receivables", []):
                if rec.get("name", "").lower() == item_name.lower() or item_name.lower() in rec.get("name", "").lower():
                    before_status = "Pendiente" if rec.get("is_pending", True) else "Cobrado"
                    rec["is_pending"] = True
                    amount = FinancialCalculator.calculate_receivable_value(rec, fiducia_yield, sum_extras)
                    rec["is_pending"] = not is_collected
                    after_status = "Cobrado" if is_collected else "Pendiente"

                    secondary_item = None
                    if is_collected and dest_account and amount > 0:
                        for acc in temp_dataset.get("liquid_accounts", []):
                            if acc.get("name", "").lower() == dest_account.lower() or dest_account.lower() in acc.get("name", "").lower():
                                before_acc = FinancialCalculator.calculate_liquid_account_total(acc)
                                acc.setdefault("adjustments", []).append({
                                    "amount": amount,
                                    "factor": 1.0,
                                    "is_active": True,
                                    "note": f"Cobro {rec['name']}"
                                })
                                after_acc = FinancialCalculator.calculate_liquid_account_total(acc)
                                secondary_item = {
                                    "name": acc["name"],
                                    "category_label": "Depósito en Cuenta Líquida",
                                    "before_value": before_acc,
                                    "after_value": after_acc,
                                    "delta": amount,
                                    "note": f"Ingreso por {rec['name']}"
                                }
                                break

                    target_item = {
                        "name": rec["name"],
                        "category_label": "Cuenta por Cobrar",
                        "before_value": amount if before_status == "Pendiente" else 0.0,
                        "after_value": 0.0 if is_collected else amount,
                        "before_status": before_status,
                        "after_status": after_status,
                        "delta": -amount if is_collected else amount,
                        "note": f"Cobrado en {dest_account}" if dest_account else "Marcar como cobrado",
                        "secondary_item": secondary_item
                    }
                    break

        elif mutation_type == "pay_expense_from_account":
            item_name = payload.get("item_name", "")
            source_account = payload.get("source_account", "Daviplata")

            for exp in temp_dataset.get("recurring_expenses", []):
                if exp.get("name", "").lower() == item_name.lower() or item_name.lower() in exp.get("name", "").lower():
                    cost = float(exp.get("pending_base") or exp.get("recurrent_base", 0.0))
                    before_status = "Pendiente" if exp.get("is_pending", True) else "Pagado"
                    exp["is_pending"] = False

                    secondary_item = None
                    for acc in temp_dataset.get("liquid_accounts", []):
                        if acc.get("name", "").lower() == source_account.lower() or source_account.lower() in acc.get("name", "").lower():
                            before_acc = FinancialCalculator.calculate_liquid_account_total(acc)
                            acc.setdefault("adjustments", []).append({
                                "amount": -abs(cost),
                                "factor": 1.0,
                                "is_active": True,
                                "note": f"Pago {exp['name']}"
                            })
                            after_acc = FinancialCalculator.calculate_liquid_account_total(acc)
                            secondary_item = {
                                "name": acc["name"],
                                "category_label": "Descuento en Cuenta Líquida",
                                "before_value": before_acc,
                                "after_value": after_acc,
                                "delta": -abs(cost),
                                "note": f"Pago {exp['name']}"
                            }
                            break

                    target_item = {
                        "name": exp["name"],
                        "category_label": "Gasto Recurrente",
                        "before_value": cost,
                        "after_value": 0.0,
                        "before_status": before_status,
                        "after_status": "Pagado",
                        "delta": -abs(cost),
                        "note": f"Pagado desde {source_account}",
                        "secondary_item": secondary_item
                    }
                    break

        elif mutation_type == "transfer_between_accounts":
            from_account = payload.get("from_account", "")
            to_account = payload.get("to_account", "")
            amount = abs(float(payload.get("amount", 0.0)))
            note = payload.get("note", "")

            from_item_data = None
            to_item_data = None

            for acc in temp_dataset.get("liquid_accounts", []):
                if acc.get("name", "").lower() == from_account.lower() or from_account.lower() in acc.get("name", "").lower():
                    before_from = FinancialCalculator.calculate_liquid_account_total(acc)
                    acc.setdefault("adjustments", []).append({
                        "amount": -amount,
                        "factor": 1.0,
                        "is_active": True,
                        "note": note or f"Transferencia a {to_account}"
                    })
                    after_from = FinancialCalculator.calculate_liquid_account_total(acc)
                    from_item_data = {
                        "name": acc["name"],
                        "category_label": "Cuenta Origen",
                        "before_value": before_from,
                        "after_value": after_from,
                        "delta": -amount,
                        "note": f"Hacia {to_account}"
                    }
                elif acc.get("name", "").lower() == to_account.lower() or to_account.lower() in acc.get("name", "").lower():
                    before_to = FinancialCalculator.calculate_liquid_account_total(acc)
                    acc.setdefault("adjustments", []).append({
                        "amount": amount,
                        "factor": 1.0,
                        "is_active": True,
                        "note": note or f"Transferencia desde {from_account}"
                    })
                    after_to = FinancialCalculator.calculate_liquid_account_total(acc)
                    to_item_data = {
                        "name": acc["name"],
                        "category_label": "Cuenta Destino",
                        "before_value": before_to,
                        "after_value": after_to,
                        "delta": amount,
                        "note": f"Desde {from_account}"
                    }

            if from_item_data:
                from_item_data["secondary_item"] = to_item_data
                target_item = from_item_data

        elif mutation_type == "allocate_goal":
            goal_name = payload.get("goal_name", "")
            amount = float(payload.get("amount", 0.0))
            for goal in temp_dataset.get("financial_goals", []):
                if goal.get("name", "").lower() == goal_name.lower() or goal_name.lower() in goal.get("name", "").lower():
                    before_val = float(goal.get("allocated_amount", 0.0))
                    target_val = float(goal.get("target_amount", 1.0))
                    after_val = max(0.0, before_val + amount)
                    goal["allocated_amount"] = after_val
                    pct_after = min(100, round((after_val / target_val) * 100, 1))
                    target_item = {
                        "name": goal["name"],
                        "category_label": f"Meta Financiera (Objetivo: ${target_val:,.0f})",
                        "before_value": before_val,
                        "after_value": after_val,
                        "delta": amount,
                        "note": f"Progreso: {pct_after}%"
                    }
                    break

        elif mutation_type == "undo_last_adjustment":
            account_name = payload.get("account_name")
            accounts = temp_dataset.get("liquid_accounts", [])
            target_acc = None
            if account_name:
                for acc in accounts:
                    if acc.get("name", "").lower() == account_name.lower() or account_name.lower() in acc.get("name", "").lower():
                        target_acc = acc
                        break
            if not target_acc:
                for acc in accounts:
                    if acc.get("adjustments"):
                        target_acc = acc
                        break

            if target_acc and target_acc.get("adjustments"):
                before_val = FinancialCalculator.calculate_liquid_account_total(target_acc)
                removed_adj = target_acc["adjustments"].pop()
                after_val = FinancialCalculator.calculate_liquid_account_total(target_acc)
                rev_delta = after_val - before_val
                target_item = {
                    "name": target_acc["name"],
                    "category_label": "Deshacer Último Movimiento",
                    "before_value": before_val,
                    "after_value": after_val,
                    "delta": rev_delta,
                    "note": f"Elimina: {removed_adj.get('note', 'Ajuste')} (${removed_adj.get('amount', 0):,.0f})"
                }

        kpis_after = FinancialCalculator.calculate_full_kpis(temp_dataset)

        delta_restante = kpis_after.restante - kpis_before.restante
        delta_incl_pend = kpis_after.incl_pend - kpis_before.incl_pend

        return {
            "mutation_type": mutation_type,
            "payload": payload,
            "target_item": target_item,
            "candidates": payload.get("candidates", []),
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

    def execute_set_account_balance(self, parent_type: str, target_name: str, new_balance: float, note: str = "") -> Dict[str, Any]:
        result = self.repo.set_account_balance(parent_type, target_name, new_balance, note)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": "success" if result.get("status") == "success" else "error",
            "message": f"Saldo de {result.get('target_name', target_name)} actualizado a ${new_balance:,.2f}",
            "result": result,
            "kpis": kpis.model_dump()
        }

    def execute_collect_receivable(self, item_name: str, is_collected: bool = True, dest_account: Optional[str] = None) -> Dict[str, Any]:
        result = self.repo.collect_receivable(item_name, is_collected=is_collected, dest_account=dest_account)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        dest_msg = f" y depositado en {result['dest_account']}" if result.get("dest_account") else ""
        return {
            "status": result.get("status", "success"),
            "message": f"{item_name} marcado como cobrado{dest_msg}",
            "result": result,
            "kpis": kpis.model_dump()
        }

    def execute_pay_expense_from_account(self, item_name: str, source_account: str) -> Dict[str, Any]:
        result = self.repo.pay_expense_from_account(item_name, source_account)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": result.get("status", "success"),
            "message": f"{item_name} pagado desde {result.get('source_account', source_account)}",
            "result": result,
            "kpis": kpis.model_dump()
        }

    def execute_transfer_between_accounts(self, from_account: str, to_account: str, amount: float, note: str = "") -> Dict[str, Any]:
        result = self.repo.transfer_between_accounts(from_account, to_account, amount, note)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": result.get("status", "success"),
            "message": f"Transferencia de ${amount:,.0f} de {result['from_account']} a {result['to_account']} realizada",
            "result": result,
            "kpis": kpis.model_dump()
        }

    def execute_undo_last_adjustment(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        result = self.repo.pop_last_adjustment(account_name)
        kpis = FinancialCalculator.calculate_full_kpis(self.repo.get_dataset())
        return {
            "status": result.get("status", "success"),
            "message": f"Último movimiento eliminado de {result.get('account_name', 'cuenta')}" if result.get("status") == "success" else result.get("message", "Error"),
            "result": result,
            "kpis": kpis.model_dump()
        }
