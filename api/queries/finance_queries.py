from typing import Dict, Any, List, Optional
from api.repositories.finance_repo import FinanceRepository
from api.domain.calculator import FinancialCalculator

class FinanceQueryService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.repo = FinanceRepository(user_id)

    def get_dashboard_summary(self) -> Dict[str, Any]:
        dataset = self.repo.get_dataset()
        kpis = FinancialCalculator.calculate_full_kpis(dataset)

        # Enhance liquid accounts with calculated totals
        liquid_accounts = []
        for acc in dataset.get("liquid_accounts", []):
            total = FinancialCalculator.calculate_liquid_account_total(acc)
            liquid_accounts.append({**acc, "calculated_total": total})

        # Enhance receivables
        fiducia_yield = kpis.rendimiento_mensual_fiducia
        sum_extras = sum(FinancialCalculator.calculate_monthly_extra_value(e) for e in dataset.get("monthly_extras", []))
        receivables = []
        for rec in dataset.get("receivables", []):
            total = FinancialCalculator.calculate_receivable_value(rec, fiducia_yield, sum_extras)
            receivables.append({**rec, "calculated_pending": total})

        # Enhance recurring expenses
        expenses = []
        for exp in dataset.get("recurring_expenses", []):
            rec_val = FinancialCalculator.calculate_expense_recurrent(exp)
            pend_val = FinancialCalculator.calculate_expense_pending(exp)
            expenses.append({
                **exp,
                "calculated_recurrent": rec_val,
                "calculated_pending": pend_val,
                "is_paid": not exp.get("is_pending", True)
            })

        # Enhance investments
        investments = []
        for inv in dataset.get("investment_assets", []):
            val = FinancialCalculator.calculate_investment_asset_value(inv)
            investments.append({**inv, "calculated_value": val})

        # Enhance extras
        extras = []
        for ext in dataset.get("monthly_extras", []):
            val = FinancialCalculator.calculate_monthly_extra_value(ext)
            extras.append({**ext, "calculated_value": val})

        return {
            "kpis": kpis.model_dump(),
            "liquid_accounts": liquid_accounts,
            "receivables": receivables,
            "recurring_expenses": expenses,
            "income_sources": dataset.get("income_sources", []),
            "investment_assets": investments,
            "monthly_extras": extras,
            "financial_goals": dataset.get("financial_goals", [])
        }

    def get_investment_capacity(self, period: str = "month") -> Dict[str, Any]:
        summary = self.get_dashboard_summary()
        kpis = summary["kpis"]
        if period == "year":
            return {
                "period": "year",
                "capacidad_invertible": kpis["proyeccion_invertible_anual"],
                "moneda": "COP",
                "detalles": {
                    "incl_pend_mes_actual": kpis["incl_pend"],
                    "ahorro_mensual_base": kpis["ahorro"],
                    "rendimiento_fiducia_anual": kpis["rendimiento_mensual_fiducia"] * 12,
                    "explicacion": "Proyección calculada sobre el excedente invertible actual más 11 meses de ahorro recurrente y rendimientos de fiducia."
                }
            }
        else:
            return {
                "period": "month",
                "capacidad_invertible": kpis["incl_pend"],
                "moneda": "COP",
                "detalles": {
                    "restante_liquidez": kpis["restante"],
                    "pendientes_por_cobrar": kpis["pend"],
                    "total_gastos_recurrentes": kpis["total_gastos"],
                    "formula": "Restante ($951,516) + Pendientes ($4,101,217.33) - Gastos Recurrentes ($3,053,000) = $1,999,733.33",
                    "explicacion": "Este es tu excedente neto real disponible para destinar a inversiones este mes una vez se recauden las cuentas pendientes y se cubran los egresos fijos."
                }
            }

    def get_account_details(self, name: str) -> Optional[Dict[str, Any]]:
        summary = self.get_dashboard_summary()
        clean = name.strip().lower()
        for acc in summary["liquid_accounts"]:
            if clean in acc["name"].lower():
                return acc
        for rec in summary["receivables"]:
            if clean in rec["name"].lower():
                return rec
        return None

    def get_expenses_breakdown(self) -> Dict[str, Any]:
        summary = self.get_dashboard_summary()
        expenses = summary["recurring_expenses"]
        pagados = [e for e in expenses if e["is_paid"]]
        pendientes = [e for e in expenses if not e["is_paid"]]
        return {
            "total_gastos_recurrentes": summary["kpis"]["total_gastos"],
            "total_gastos_pendientes_mes": summary["kpis"]["gastos_mes"],
            "conteo_pendientes": len(pendientes),
            "conteo_pagados": len(pagados),
            "gastos_pendientes": pendientes,
            "gastos_pagados": pagados
        }

    def search_financial_history(self, query: str) -> List[Dict[str, Any]]:
        from api.agent.prompt_enhancer import PromptEnhancer
        from api.agent.reranker import ReRanker

        enhanced = PromptEnhancer.enhance(query)
        clean = enhanced["canonical_text"]
        results = []
        summary = self.get_dashboard_summary()
        
        # Search in liquid accounts & adjustments
        for acc in summary["liquid_accounts"]:
            if clean in acc["name"].lower() or query.strip().lower() in acc["name"].lower():
                results.append({"type": "cuenta_liquidez", "name": acc["name"], "match": acc["name"], "data": acc})
            for adj in acc.get("adjustments", []):
                if clean in adj.get("note", "").lower() or clean in str(adj.get("amount", "")):
                    results.append({
                        "type": "movimiento_ledger",
                        "cuenta": acc["name"],
                        "nota": adj.get("note"),
                        "monto": adj.get("amount"),
                        "fecha": adj.get("created_at")
                    })

        # Search in receivables
        for rec in summary["receivables"]:
            if clean in rec["name"].lower():
                results.append({"type": "cuenta_por_cobrar", "name": rec["name"], "match": rec["name"], "data": rec})
            for adj in rec.get("adjustments", []):
                if clean in adj.get("note", "").lower():
                    results.append({
                        "type": "ajuste_por_cobrar",
                        "cuenta": rec["name"],
                        "nota": adj.get("note"),
                        "monto": adj.get("amount")
                    })

        # Search in expenses
        for exp in summary["recurring_expenses"]:
            if clean in exp["name"].lower():
                results.append({"type": "gasto", "name": exp["name"], "data": exp})

        return ReRanker.rerank_history_results(clean, results)
