from typing import Dict, Any, List
from api.domain.models import (
    LiquidAccountModel,
    ReceivableModel,
    IncomeSourceModel,
    RecurringExpenseModel,
    MonthlyExtraModel,
    InvestmentAssetModel,
    FinancialGoalModel,
    KPISummaryModel
)

class FinancialCalculator:
    """
    Pure Python domain calculator reproducing exact formulas from EXCEL_SPEC.md (Gastos Albeiro.xlsx).
    """

    @staticmethod
    def calculate_liquid_account_total(account: Dict[str, Any]) -> float:
        """
        Evaluates base_amount * factor + sum of active ledger adjustments.
        Returns 0 if account is inactive (e.g. Colchon 100000 * 0).
        """
        if not account.get("is_active", True):
            return 0.0
        
        base = float(account.get("base_amount", 0.0)) * float(account.get("factor", 1.0))
        adjustments_sum = 0.0
        for adj in account.get("adjustments", []):
            if adj.get("is_active", True):
                adjustments_sum += float(adj.get("amount", 0.0)) * float(adj.get("factor", 1.0))
        return base + adjustments_sum

    @staticmethod
    def calculate_investment_asset_value(asset: Dict[str, Any]) -> float:
        if not asset.get("is_active", True):
            return 0.0
        asset_type = asset.get("asset_type", "")
        if asset_type == "crypto":
            return float(asset.get("units", 0.0)) * float(asset.get("exchange_rate", 1.0))
        elif asset_type == "fiducia":
            return float(asset.get("base_amount", 0.0))
        else:
            return float(asset.get("base_amount", 0.0))

    @staticmethod
    def calculate_monthly_extra_value(extra: Dict[str, Any]) -> float:
        if not extra.get("is_active", True):
            return 0.0
        return float(extra.get("base_amount", 0.0)) * float(extra.get("factor", 1.0))

    @staticmethod
    def calculate_fiducia_monthly_yield(fiducia_capital: float, annual_yield: float = 0.07, days: int = 30) -> float:
        """
        Fiducia formula: Capital * (0.07 / 12) * (days / 30)
        For 32,560,000 COP at 7% E.A. -> 189,933.33333333334 COP
        """
        return float(fiducia_capital) * (annual_yield / 12.0) * (days / 30.0)

    @classmethod
    def calculate_receivable_value(
        cls, 
        rec: Dict[str, Any], 
        fiducia_yield: float, 
        sum_extras: float
    ) -> float:
        if not rec.get("is_active", True) or not rec.get("is_pending", True):
            return 0.0

        formula_type = rec.get("formula_type", "standard")
        if formula_type == "fiducia_yield":
            return fiducia_yield * float(rec.get("factor", 1.0))
        elif formula_type == "sum_extras":
            return sum_extras * float(rec.get("factor", 1.0))
        
        base = float(rec.get("base_amount", 0.0)) * float(rec.get("factor", 1.0))
        adjustments_sum = 0.0
        for adj in rec.get("adjustments", []):
            if adj.get("is_active", True):
                adjustments_sum += float(adj.get("amount", 0.0)) * float(adj.get("factor", 1.0))
        return base + adjustments_sum

    @classmethod
    def calculate_income_value(cls, inc: Dict[str, Any], fiducia_yield: float) -> float:
        if not inc.get("is_active", True):
            return 0.0
        if inc.get("formula_type") == "fiducia_yield":
            return fiducia_yield * float(inc.get("factor", 1.0))
        return float(inc.get("base_amount", 0.0)) * float(inc.get("factor", 1.0))

    @staticmethod
    def calculate_expense_recurrent(exp: Dict[str, Any]) -> float:
        if not exp.get("recurrent_is_active", True):
            return 0.0
        return float(exp.get("recurrent_base", 0.0)) * float(exp.get("recurrent_factor", 1.0))

    @staticmethod
    def calculate_expense_pending(exp: Dict[str, Any]) -> float:
        if not exp.get("is_pending", True):
            return 0.0
        return float(exp.get("pending_base", 0.0)) * float(exp.get("pending_factor", 1.0))

    @classmethod
    def calculate_full_kpis(cls, dataset: Dict[str, Any], remaining_months: int = 11) -> KPISummaryModel:
        """
        Executes exact Excel parity calculation across all 7 blocks.
        """
        # 1. Total actual (Block A: SUM(B2:B6))
        total_actual = sum(
            cls.calculate_liquid_account_total(acc)
            for acc in dataset.get("liquid_accounts", [])
        )

        # 2. Fiducia Capital and Yield (Block C & D)
        fiducia_capital = 0.0
        patrimonio_total = 0.0
        for asset in dataset.get("investment_assets", []):
            val = cls.calculate_investment_asset_value(asset)
            patrimonio_total += val
            if asset.get("asset_type") == "fiducia" or "fiducia" in asset.get("name", "").lower():
                fiducia_capital = float(asset.get("base_amount", 0.0))

        rendimiento_mensual_fiducia = cls.calculate_fiducia_monthly_yield(fiducia_capital)

        # 3. Monthly Extras sum (Block F)
        sum_extras = sum(
            cls.calculate_monthly_extra_value(extra)
            for extra in dataset.get("monthly_extras", [])
        )

        # 4. Receivables / Pend (Block B: SUM(B8:B14))
        pend = sum(
            cls.calculate_receivable_value(rec, rendimiento_mensual_fiducia, sum_extras)
            for rec in dataset.get("receivables", [])
        )

        # 5. Incomes (Block D: SUM(D4:D15))
        sueldo_amount = 0.0
        ingresos = 0.0
        for inc in dataset.get("income_sources", []):
            val = cls.calculate_income_value(inc, rendimiento_mensual_fiducia)
            ingresos += val
            if "sueldo" in inc.get("name", "").lower():
                sueldo_amount = val

        # 6. Expenses Recurrent & Pending (Block E: F18 & G18)
        total_gastos = sum(
            cls.calculate_expense_recurrent(exp)
            for exp in dataset.get("recurring_expenses", [])
        )

        gastos_mes = sum(
            cls.calculate_expense_pending(exp)
            for exp in dataset.get("recurring_expenses", [])
        )

        # 7. Master Formulas from EXCEL_SPEC.md
        # Cell B20: Restante = Total actual - Gastos mes
        restante = total_actual - gastos_mes

        # Cell D20: Ahorro = Ingresos - Total gastos
        ahorro = ingresos - total_gastos

        # Cell D21: Ahorro sin sueldo
        ahorro_sin_sueldo = ahorro - sueldo_amount

        # Cell B22: Incl Pend (Invertible) = Restante + Pend - Total gastos
        incl_pend = restante + pend - total_gastos

        # Proyeccion invertible anual
        proyeccion_invertible_anual = (
            (ahorro * remaining_months) 
            + incl_pend 
            + (rendimiento_mensual_fiducia * remaining_months)
        )

        return KPISummaryModel(
            total_actual=round(total_actual, 2),
            gastos_mes=round(gastos_mes, 2),
            restante=round(restante, 2),
            ingresos=round(ingresos, 2),
            total_gastos=round(total_gastos, 2),
            ahorro=round(ahorro, 2),
            ahorro_sin_sueldo=round(ahorro_sin_sueldo, 2),
            pend=round(pend, 2),
            incl_pend=round(incl_pend, 2),
            proyeccion_invertible_anual=round(proyeccion_invertible_anual, 2),
            rendimiento_mensual_fiducia=round(rendimiento_mensual_fiducia, 2),
            patrimonio_total=round(patrimonio_total, 2)
        )
