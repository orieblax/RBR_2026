from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class LedgerAdjustmentModel(BaseModel):
    id: Optional[str] = None
    parent_type: str = "liquid_account" # liquid_account, receivable, recurring_expense
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    amount: float
    factor: float = 1.0
    is_active: bool = True
    note: str = ""
    created_at: Optional[datetime] = None

class LiquidAccountModel(BaseModel):
    id: Optional[str] = None
    name: str
    base_amount: float = 0.0
    factor: float = 1.0
    is_active: bool = True
    display_order: int = 0
    adjustments: List[LedgerAdjustmentModel] = Field(default_factory=list)

class ReceivableModel(BaseModel):
    id: Optional[str] = None
    name: str
    linked_source: Optional[str] = None
    due_day: Optional[int] = 1
    base_amount: float = 0.0
    factor: float = 1.0
    is_active: bool = True
    is_pending: bool = True
    formula_type: str = "standard" # standard, fiducia_yield, sum_extras
    display_order: int = 0
    adjustments: List[LedgerAdjustmentModel] = Field(default_factory=list)

class IncomeSourceModel(BaseModel):
    id: Optional[str] = None
    name: str
    base_amount: float = 0.0
    factor: float = 1.0
    is_active: bool = True
    formula_type: str = "standard"
    display_order: int = 0

class RecurringExpenseModel(BaseModel):
    id: Optional[str] = None
    name: str
    due_days: str = "1"
    recurrent_base: float = 0.0
    recurrent_factor: float = 1.0
    recurrent_is_active: bool = True
    pending_base: float = 0.0
    pending_factor: float = 1.0
    is_pending: bool = False
    display_order: int = 0

class MonthlyExtraModel(BaseModel):
    id: Optional[str] = None
    name: str
    base_amount: float = 0.0
    factor: float = 1.0
    is_active: bool = True
    display_order: int = 0

class InvestmentAssetModel(BaseModel):
    id: Optional[str] = None
    name: str
    asset_type: str # cesantias, crypto, fiducia
    base_amount: float = 0.0
    units: float = 0.0
    exchange_rate: float = 1.0
    annual_yield_rate: float = 0.07
    is_active: bool = True
    display_order: int = 0

class FinancialGoalModel(BaseModel):
    id: Optional[str] = None
    name: str
    target_amount: float = 0.0
    allocated_amount: float = 0.0
    priority: int = 1
    status: str = "active"
    display_order: int = 0

class KPISummaryModel(BaseModel):
    total_actual: float
    gastos_mes: float
    restante: float
    ingresos: float
    total_gastos: float
    ahorro: float
    ahorro_sin_sueldo: float
    pend: float
    incl_pend: float # Primary Monthly Investable KPI
    proyeccion_invertible_anual: float
    rendimiento_mensual_fiducia: float
    patrimonio_total: float
