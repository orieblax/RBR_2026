import uuid
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from api.queries.finance_queries import FinanceQueryService
from api.commands.finance_commands import FinanceCommandService
from api.domain.calculator import FinancialCalculator
from api.agent.prompt_enhancer import PromptEnhancer
from api.agent.reranker import ReRanker, fuzzy_similarity

# In-memory store for pending staged actions (2-Step Safety Confirmation)
pending_voice_actions_store: Dict[str, Dict[str, Any]] = {}
audit_logs_store: List[Dict[str, Any]] = []

SPANISH_SYSTEM_PROMPT = """Eres el Agente Financiero de RBR Finance Manager, experto en finanzas personales y optimización de excedentes invertibles en Colombia (es-CO).
Te riges estrictamente por las fórmulas de EXCEL_SPEC.md y Gastos Albeiro.xlsx:
- Tu KPI principal es 'Incl Pend' (Disponible para Invertir Este Mes = Restante + Pend - Total Gastos = $1,999,733.33).
- Las cuentas de liquidez tienen micro-ledgers inline (como Daviplata y Caja social).
- Los egresos pueden ser recurrentes o pendientes (*1 activo, *0 pagado).
- NUNCA ejecutes modificaciones directamente sin pasar por la herramienta de propuesta staged (propose_*) para que el usuario confirme el cambio."""

def _strip_accents(text: str) -> str:
    accents = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u'
    }
    res = text
    for acc, norm in accents.items():
        res = res.replace(acc, norm)
    return res

WORD_NUMBERS = {
    "cincuenta mil": 50000.0,
    "cien mil": 100000.0,
    "doscientos mil": 200000.0,
    "trescientos mil": 300000.0,
    "cuatrocientos mil": 400000.0,
    "quinientos mil": 500000.0,
    "veinte mil": 20000.0,
    "treinta mil": 30000.0,
    "cuarenta mil": 40000.0,
    "diez mil": 10000.0,
    "un millon": 1000000.0,
    "medio millon": 500000.0,
}

LIQUID_ACCOUNTS_MAP = {
    "mi bolsillo": "Bolsillo",
    "bolsillo": "Bolsillo",
    "daviplata": "Daviplata",
    "caja social": "Caja social",
    "cajasocial": "Caja social",
    "nequi": "Nequi",
}

RECEIVABLES_MAP = {
    "camila 20": "Camila 20",
    "camila": "Camila 20",
    "apto 01": "Camila 20",
    "ana 26": "Ana 26",
    "ana": "Ana 26",
    "casa 3p": "Ana 26",
    "marisol 23": "Marisol 23",
    "marisol": "Marisol 23",
    "casa 2p": "Marisol 23",
    "angelica 1": "Angelica 1",
    "angelica": "Angelica 1",
    "apto 03": "Angelica 1",
    "odeth 28": "Odeth 28",
    "odeth": "Odeth 28",
    "apto 02": "Odeth 28",
    "fiducia": "Fiducia",
    "pagos extras": "Pagos Extras",
}

ACCOUNTS_MAP = {**LIQUID_ACCOUNTS_MAP, **RECEIVABLES_MAP}

GOALS_MAP = {
    "english": "English",
    "ingles": "English",
    "maestria": "Maestría",
    "posgrado": "Maestría",
    "visa": "Visa",
    "casa brisas": "Casa brisas",
    "brisas": "Casa brisas",
    "matrimonio": "Matrimonio",
    "boda": "Matrimonio",
    "ortodoncia": "Ortodoncia",
    "odontologia": "Ortodoncia",
}

EXPENSE_ALIASES = {
    "gas": "Gas 15",
    "energia": "Energía 20",
    "luz": "Energía 20",
    "electricidad": "Energía 20",
    "agua": "Agua 25",
    "acueducto": "Agua 25",
    "internet": "Internet 25",
    "wifi": "Internet 25",
    "mercado": "Merc Aseo 1",
    "aseo": "Merc Aseo 1",
    "supermercado": "Merc Aseo 1",
    "movistar": "Movistar 1-26",
    "celular": "Movistar 1-26",
    "telefono": "Movistar 1-26",
    "mama": "Mamá 1",
    "papa": "Papá 1-15",
    "planilla": "Planilla 1",
    "seguridad social": "Planilla 1",
    "servicio": "Servicio 30",
    "servicios": "Servicio 30",
    "moto": "Moto",
    "hija": "Hija",
}

def _extract_amount(text: str, mask_entity: Optional[str] = None) -> Optional[float]:
    clean = _strip_accents(text).lower()

    # 1. Mask out matched entity to avoid extracting due days (like "20" from "Camila 20" or "15" from "Gas 15")
    if mask_entity:
        mask_clean = _strip_accents(mask_entity).lower()
        clean = clean.replace(mask_clean, " ")
        tokens = mask_clean.split()
        for tok in tokens:
            if tok.isdigit():
                clean = re.sub(rf"\b{tok}\b", " ", clean)

    # 2. Check for word numbers
    for phrase, val in WORD_NUMBERS.items():
        if phrase in clean:
            return val

    # 3. Check for pattern: number + "mil" or "k" (e.g. "50 mil", "50mil", "50 k")
    mil_match = re.search(r"\b(\d+(?:[\.,]\d+)?)\s*(?:mil|k)\b", clean)
    if mil_match:
        val_str = mil_match.group(1).replace(",", ".")
        try:
            return float(val_str) * 1000.0
        except ValueError:
            pass

    # 4. Check for pattern: number + "millon(es)" (e.g. "1.5 millones", "2 millones")
    mill_match = re.search(r"\b(\d+(?:[\.,]\d+)?)\s*(?:millones|millon)\b", clean)
    if mill_match:
        val_str = mill_match.group(1).replace(",", ".")
        try:
            return float(val_str) * 1000000.0
        except ValueError:
            pass

    # 5. Check for thousands with space, dot, or comma separators:
    # e.g., "50 000", "50.000", "50,000", "1 250 000", "1.250.000"
    thousands_match = re.search(r"\b(\d{1,3}(?:[\s\.,]\d{3})+)\b", clean)
    if thousands_match:
        raw_num = thousands_match.group(1)
        normalized_num = re.sub(r"[\s\.,]", "", raw_num)
        try:
            return float(normalized_num)
        except ValueError:
            pass

    # 6. Standard standalone number
    std_match = re.search(r"\b(\d+[\.\d+]*)\b", clean)
    if std_match:
        try:
            return float(std_match.group(1))
        except ValueError:
            pass

    return None

def _identify_account(text: str) -> Optional[str]:
    clean = _strip_accents(text).lower()
    for key, name in sorted(ACCOUNTS_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{key}\b", clean):
            return name
    return None

def _identify_liquid_account(text: str) -> Optional[str]:
    clean = _strip_accents(text).lower()
    for key, name in sorted(LIQUID_ACCOUNTS_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{key}\b", clean):
            return name
    return None

def _identify_receivable(text: str) -> Optional[str]:
    clean = _strip_accents(text).lower()
    for key, name in sorted(RECEIVABLES_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{key}\b", clean):
            return name
    return None

def _identify_goal(text: str) -> Optional[str]:
    clean = _strip_accents(text).lower()
    for key, name in sorted(GOALS_MAP.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{key}\b", clean):
            return name
    # Fuzzy fallback for phonetic variants (e.g. "ortodonsia", "maestria")
    words = [w for w in re.findall(r"[a-zñ]+", clean) if len(w) >= 4]
    for w in words:
        for key, name in GOALS_MAP.items():
            if fuzzy_similarity(w, key) >= 0.80:
                return name
    return None

def _identify_expense(clean_text: str, expenses: List[Dict[str, Any]]) -> Optional[str]:
    ranked = ReRanker.rerank_entity_matches(
        clean_text,
        expenses,
        aliases_map=EXPENSE_ALIASES,
        prefer_pending=True,
        threshold=0.70
    )
    if ranked:
        return ranked[0][0]["name"]
    return None

def _identify_transfer_accounts(text: str) -> Optional[Tuple[str, str]]:
    clean = _strip_accents(text).lower()
    # Pattern: de/desde <acc1> ... a/para/hacia <acc2>
    acc_keys = "|".join(sorted(LIQUID_ACCOUNTS_MAP.keys(), key=len, reverse=True))
    m = re.search(
        rf"\b(?:de|desde)\s+(?:mi\s+)?({acc_keys})\b.*?\b(?:a|para|hacia|en)\s+(?:mi\s+)?({acc_keys})\b",
        clean
    )
    if m:
        from_acc = LIQUID_ACCOUNTS_MAP[m.group(1)]
        to_acc = LIQUID_ACCOUNTS_MAP[m.group(2)]
        if from_acc != to_acc:
            return (from_acc, to_acc)
    return None

def _extract_reason(text: str, account_name: Optional[str] = None) -> str:
    clean = _strip_accents(text).lower()

    # 1. Remove account references with prepositions first
    clean = re.sub(r"\b(?:desde|en|de|para|a)\s+(?:mi\s+)?(?:bolsillo|daviplata|nequi|caja\s+social|cajasocial|camila\s+20|ana\s+26|marisol\s+23)\b", " ", clean)
    if account_name:
        clean = clean.replace(_strip_accents(account_name).lower(), " ")

    # 2. Remove digits
    clean = re.sub(r"\b\d+\b", " ", clean)

    # 3. Look for explicit reason prepositions: "por <motivo>", "en <motivo>", "para <motivo>"
    por_match = re.search(r"\bpor\s+([a-zñ\s]+?)(?:\s+(?:desde|con|a|para|en)|$)", clean)
    if por_match:
        cand = por_match.group(1).strip()
        tokens = [t for t in cand.split() if t not in ("mi", "la", "el", "los", "las", "un", "una", "cuenta", "de", "que")]
        if tokens:
            return " ".join(tokens).capitalize()

    en_para_match = re.search(r"\b(?:en|para)\s+([a-zñ\s]+?)(?:\s+(?:desde|con|a|por)|$)", clean)
    if en_para_match:
        cand = en_para_match.group(1).strip()
        tokens = [t for t in cand.split() if t not in ("mi", "la", "el", "los", "las", "un", "una", "cuenta", "de", "que")]
        if tokens:
            return " ".join(tokens).capitalize()

    # 4. Fallback to direct noun after gasto / abono / pago
    m2 = re.search(r"\b(?:gaste|gasto|pague|compre)\s+([a-zñ]+)", clean)
    if m2:
        cand = m2.group(1).strip()
        if cand not in ("de", "en", "por", "para", "desde", "mi", "un", "una", "el", "la"):
            return cand.capitalize()

    return "Movimiento por voz"


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
    def propose_ledger_adjustment(self, target_name: str, amount_delta: float, reason: str = "", parent_type: str = "liquid_account") -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "parent_type": parent_type,
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
            "target_item": preview.get("target_item"),
            "candidates": preview.get("candidates", []),
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_set_account_balance(self, target_name: str, new_balance: float, note: str = "") -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "parent_type": "liquid_account",
            "target_name": target_name,
            "new_balance": float(new_balance),
            "note": note or "Actualización de saldo"
        }
        preview = self.command_service.preview_mutation("set_account_balance", payload)
        target_item = preview.get("target_item") or {}
        before_val = target_item.get("before_value", 0.0)
        preview_summary = f"Actualizar saldo de {target_name} a ${new_balance:,.0f} COP (anterior: ${before_val:,.0f})"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_set_account_balance",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": target_item,
            "candidates": preview.get("candidates", []),
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_toggle_pending_status(self, item_name: str, is_paid: bool = True, candidates: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
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
            "target_item": preview.get("target_item"),
            "candidates": candidates or preview.get("candidates", []),
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_collect_receivable(
        self,
        item_name: str,
        is_collected: bool = True,
        dest_account: Optional[str] = None,
        candidates: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "item_name": item_name,
            "is_collected": is_collected,
            "dest_account": dest_account
        }
        preview = self.command_service.preview_mutation("collect_receivable", payload)
        dest_str = f" y depositar en {dest_account}" if dest_account else ""
        preview_summary = f"Marcar como cobrado {item_name}{dest_str}"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_collect_receivable",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": preview.get("target_item"),
            "candidates": candidates or preview.get("candidates", []),
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_pay_expense_from_account(self, item_name: str, source_account: str) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "item_name": item_name,
            "source_account": source_account
        }
        preview = self.command_service.preview_mutation("pay_expense_from_account", payload)
        cost = abs(preview.get("target_item", {}).get("delta", 0.0))
        preview_summary = f"Pagar {item_name} (${cost:,.0f} COP) descontando de {source_account}"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_pay_expense_from_account",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": preview.get("target_item"),
            "candidates": [],
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_transfer_between_accounts(self, from_account: str, to_account: str, amount: float, note: str = "") -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "from_account": from_account,
            "to_account": to_account,
            "amount": abs(float(amount)),
            "note": note
        }
        preview = self.command_service.preview_mutation("transfer_between_accounts", payload)
        preview_summary = f"Transferir ${abs(amount):,.0f} COP de {from_account} a {to_account}"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_transfer_between_accounts",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": preview.get("target_item"),
            "candidates": [],
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_allocate_goal(self, goal_name: str, amount: float) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "goal_name": goal_name,
            "amount": float(amount)
        }
        preview = self.command_service.preview_mutation("allocate_goal", payload)
        preview_summary = f"Abonar ${amount:,.0f} COP a la meta financiera {goal_name}"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_allocate_goal",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": preview.get("target_item"),
            "candidates": [],
            "impact_delta": preview["impact_delta"],
            "kpis_before": preview["kpis_before"],
            "kpis_after": preview["kpis_after"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        pending_voice_actions_store[action_id] = action
        return action

    def propose_undo_last_adjustment(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        payload = {
            "account_name": account_name
        }
        preview = self.command_service.preview_mutation("undo_last_adjustment", payload)
        target_item = preview.get("target_item") or {}
        acc_label = target_item.get("name", account_name or "cuenta")
        note_label = target_item.get("note", "último ajuste")
        preview_summary = f"Deshacer último movimiento en {acc_label} ({note_label})"

        action = {
            "action_id": action_id,
            "user_id": self.user_id,
            "tool_name": "propose_undo_last_adjustment",
            "action_payload": payload,
            "preview_summary": preview_summary,
            "target_item": target_item,
            "candidates": [],
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
            "target_item": preview.get("target_item"),
            "candidates": preview.get("candidates", []),
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
    def confirm_action(cls, action_id: str, selected_candidate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        action = pending_voice_actions_store.get(action_id)
        if not action or action.get("status") != "pending":
            return {"status": "error", "message": "Acción no encontrada o ya procesada"}

        cmd_svc = FinanceCommandService(action["user_id"])
        tool = action["tool_name"]
        payload = action["action_payload"]

        # If user picked a specific candidate from the modal choices
        if selected_candidate and "item_name" in selected_candidate:
            if tool == "propose_toggle_pending_status":
                payload["item_name"] = selected_candidate["item_name"]
                action["preview_summary"] = f"Marcar como pagado (*0) el gasto {payload['item_name']}"
            elif tool == "propose_collect_receivable":
                payload["item_name"] = selected_candidate["item_name"]
                action["preview_summary"] = f"Marcar como cobrado {payload['item_name']}"

        exec_result = {}
        if tool == "propose_ledger_adjustment":
            exec_result = cmd_svc.execute_add_adjustment(
                payload["parent_type"], payload["target_name"], payload["amount"], payload["note"]
            )
        elif tool == "propose_set_account_balance":
            exec_result = cmd_svc.execute_set_account_balance(
                payload["parent_type"], payload["target_name"], payload["new_balance"], payload.get("note", "")
            )
        elif tool == "propose_toggle_pending_status":
            exec_result = cmd_svc.execute_toggle_pending(
                payload["category"], payload["item_name"], payload["is_paid"]
            )
        elif tool == "propose_collect_receivable":
            exec_result = cmd_svc.execute_collect_receivable(
                payload["item_name"], payload.get("is_collected", True), payload.get("dest_account")
            )
        elif tool == "propose_pay_expense_from_account":
            exec_result = cmd_svc.execute_pay_expense_from_account(
                payload["item_name"], payload["source_account"]
            )
        elif tool == "propose_transfer_between_accounts":
            exec_result = cmd_svc.execute_transfer_between_accounts(
                payload["from_account"], payload["to_account"], payload["amount"], payload.get("note", "")
            )
        elif tool == "propose_allocate_goal":
            exec_result = cmd_svc.execute_update_goal(
                payload["goal_name"], payload["amount"]
            )
        elif tool == "propose_undo_last_adjustment":
            exec_result = cmd_svc.execute_undo_last_adjustment(
                payload.get("account_name")
            )
        elif tool == "propose_update_item":
            exec_result = cmd_svc.execute_update_item(
                payload["category"], payload["name"], payload["new_amount"]
            )

        action["status"] = "confirmed"
        action["confirmed_at"] = datetime.utcnow().isoformat()

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

    # --- Spanish Voice Intent Engine (Prompt Enhancement + Multi-Signal Re-Ranking) ---
    def _finalize_staged_response(self, staged: Dict[str, Any], enhanced: Dict[str, Any], custom_reply: Optional[str] = None) -> Dict[str, Any]:
        score = ReRanker.score_text_against_exemplars(enhanced["canonical_text"], staged["tool_name"])
        staged["rerank_score"] = score
        staged["prompt_enhancement"] = enhanced
        return {
            "type": "stage_action",
            "staged_action": staged,
            "prompt_enhancement": enhanced,
            "rerank_score": score,
            "reply": custom_reply or f"Propuesta: {staged['preview_summary']}. ¿Confirmas el cambio?"
        }

    def process_voice_command(self, text: str) -> Dict[str, Any]:
        # Step 1: User Prompt Enhancement (Phonetic ASR + Colloquial Slang + Verb Canonicalization)
        enhanced = PromptEnhancer.enhance(text)
        clean = enhanced["canonical_text"]

        # 0. Immediate voice confirmation / cancellation words
        if clean in ("confirmar", "si confirmar", "confirmo", "dale", "si", "aprobar"):
            for act_id, act in reversed(list(pending_voice_actions_store.items())):
                if act.get("user_id") == self.user_id and act.get("status") == "pending":
                    res = self.confirm_action(act_id)
                    return {"type": "confirmed", "reply": res["message"], "needs_refresh": True, "prompt_enhancement": enhanced}

        if clean in ("cancelar", "no", "descartar", "cancela"):
            for act_id, act in reversed(list(pending_voice_actions_store.items())):
                if act.get("user_id") == self.user_id and act.get("status") == "pending":
                    res = self.cancel_action(act_id)
                    return {"type": "cancelled", "reply": "Acción descartada", "needs_refresh": False, "prompt_enhancement": enhanced}

        # 1. Undo Last Adjustment Intent
        is_undo_intent = any(
            kw in clean
            for kw in ("deshacer", "borrar ultimo", "borrar el ultimo", "eliminar ultimo", "eliminar el ultimo", "revertir ultimo")
        )
        if is_undo_intent:
            target_acc = _identify_liquid_account(clean)
            staged = self.propose_undo_last_adjustment(target_acc)
            return self._finalize_staged_response(staged, enhanced)

        # 2. Smart Read Queries: Pending Receivables, Pending Bills, Goals Progress
        is_pending_recs_query = any(
            kw in clean
            for kw in ("quien falta por pagar", "arriendos pendientes", "cuentas por cobrar", "quien me debe", "falta por cobrar", "pendientes por cobrar")
        ) or ("arriendo" in clean and any(q in clean for q in ("quien", "cual", "pendiente", "falta")))
        if is_pending_recs_query:
            summary = self.query_service.get_dashboard_summary()
            pending_recs = [r for r in summary["receivables"] if r["calculated_pending"] > 0]
            if not pending_recs:
                return {"type": "read", "reply": "Todas las cuentas por cobrar y arriendos del mes ya fueron recaudados.", "prompt_enhancement": enhanced}
            items_str = ", ".join(f"{r['name']} (${r['calculated_pending']:,.0f})" for r in pending_recs)
            return {
                "type": "read",
                "reply": f"Tienes {len(pending_recs)} cobros pendientes por un total de ${summary['kpis']['pend']:,.0f} COP: {items_str}.",
                "data": pending_recs,
                "prompt_enhancement": enhanced
            }

        is_pending_bills_query = any(
            kw in clean
            for kw in ("que facturas", "cuales facturas", "cuales recibos", "facturas pendientes", "recibos pendientes", "falta por pagar")
        )
        if is_pending_bills_query:
            summary = self.query_service.get_dashboard_summary()
            pending_exps = [e for e in summary["recurring_expenses"] if not e["is_paid"]]
            if not pending_exps:
                return {"type": "read", "reply": "¡Excelente! No tienes ninguna factura pendiente por pagar este mes.", "prompt_enhancement": enhanced}
            items_str = ", ".join(f"{e['name']} (${e['calculated_pending']:,.0f})" for e in pending_exps)
            return {
                "type": "read",
                "reply": f"Tienes {len(pending_exps)} facturas pendientes por un total de ${summary['kpis']['gastos_mes']:,.0f} COP: {items_str}.",
                "data": pending_exps,
                "prompt_enhancement": enhanced
            }

        matched_goal = _identify_goal(clean)
        is_goal_query = any(
            kw in clean
            for kw in ("como van mis metas", "mis metas", "cuanto me falta para", "cuanto falta para", "estado de la meta", "progreso de")
        )
        if is_goal_query:
            goals = self.query_service.repo.get_financial_goals()
            if matched_goal:
                g = next((item for item in goals if item["name"].lower() == matched_goal.lower()), None)
                if g:
                    rem = max(0.0, float(g["target_amount"]) - float(g["allocated_amount"]))
                    pct = round((float(g["allocated_amount"]) / float(g["target_amount"])) * 100, 1)
                    return {
                        "type": "read",
                        "reply": f"En la meta {g['name']} llevas ${g['allocated_amount']:,.0f} de ${g['target_amount']:,.0f} COP ({pct}%). Te faltan ${rem:,.0f} COP.",
                        "data": g,
                        "prompt_enhancement": enhanced
                    }
            summary_str = ", ".join(
                f"{g['name']}: ${g['allocated_amount']:,.0f}/${g['target_amount']:,.0f}"
                for g in goals
            )
            return {
                "type": "read",
                "reply": f"Estado actual de tus {len(goals)} metas financieras: {summary_str}.",
                "data": goals,
                "prompt_enhancement": enhanced
            }

        # 3. Allocate to Financial Goal Intent
        if matched_goal:
            goal_amount = _extract_amount(clean, mask_entity=matched_goal)
            has_goal_verb = any(v in clean for v in ("abonar", "abono", "asignar", "meter", "aportar", "agregar", "destinar", "ahorrar", "meta"))
            if goal_amount is not None and has_goal_verb:
                staged = self.propose_allocate_goal(matched_goal, goal_amount)
                return self._finalize_staged_response(staged, enhanced)

        # 4. Transfer Between Liquid Accounts Intent
        transfer_pair = _identify_transfer_accounts(clean)
        has_transfer_verb = any(
            v in clean
            for v in ("transferi", "transferir", "transferencia", "pase", "pasar", "movi", "mover", "saque", "retire", "enviar", "envie")
        )
        if transfer_pair and has_transfer_verb:
            from_acc, to_acc = transfer_pair
            amount = _extract_amount(clean)
            if amount is not None:
                staged = self.propose_transfer_between_accounts(from_acc, to_acc, amount)
                return self._finalize_staged_response(staged, enhanced)

        # 5. Collect Receivable / Rent Intent
        matched_rec = _identify_receivable(clean)
        is_collect_intent = any(
            kw in clean
            for kw in ("arriendo", "marcar cobrado", "cobrado", "cobre", "ya pago", "me pago", "recibi el pago", "pago de")
        )
        if is_collect_intent:
            dest_acc = _identify_liquid_account(clean)
            if matched_rec:
                staged = self.propose_collect_receivable(matched_rec, is_collected=True, dest_account=dest_acc)
                return self._finalize_staged_response(staged, enhanced)
            else:
                summary = self.query_service.get_dashboard_summary()
                rec_candidates = []
                for r in summary["receivables"]:
                    if r["calculated_pending"] > 0:
                        preview = self.command_service.preview_mutation("collect_receivable", {
                            "item_name": r["name"],
                            "is_collected": True,
                            "dest_account": dest_acc
                        })
                        rec_candidates.append({
                            "item_name": r["name"],
                            "amount": float(r["calculated_pending"]),
                            "preview_summary": f"Marcar {r['name']} como cobrado",
                            "delta_incl_pend": preview["impact_delta"]["delta_incl_pend"],
                            "delta_restante": preview["impact_delta"]["delta_restante"],
                            "target_item": preview.get("target_item")
                        })
                if rec_candidates:
                    reranked_recs = ReRanker.rerank_disambiguation_options(clean, rec_candidates)
                    staged = self.propose_collect_receivable(
                        reranked_recs[0]["item_name"],
                        is_collected=True,
                        dest_account=dest_acc,
                        candidates=reranked_recs
                    )
                    return self._finalize_staged_response(
                        staged,
                        enhanced,
                        custom_reply="¿Cuál cuenta por cobrar o arriendo recibiste? Selecciona una opción:"
                    )

        # 6. Mark Expense Pending (*1) or Paid (*0) / Pay Expense From Account
        expenses = self.query_service.repo.get_recurring_expenses()
        matched_expense_name = _identify_expense(clean, expenses)

        is_revert_pending_intent = any(kw in clean for kw in ("marcar pendiente", "como pendiente", "reactivar factura", "reactivar recibo"))
        if is_revert_pending_intent and matched_expense_name:
            staged = self.propose_toggle_pending_status(matched_expense_name, is_paid=False)
            return self._finalize_staged_response(staged, enhanced)

        is_paid_intent = any(kw in clean for kw in ("marcar pagado", "pagado", "pague", "pago", "cancela factura"))
        if is_paid_intent:
            source_liq_acc = _identify_liquid_account(clean)

            if matched_expense_name:
                if source_liq_acc:
                    staged = self.propose_pay_expense_from_account(matched_expense_name, source_liq_acc)
                else:
                    staged = self.propose_toggle_pending_status(matched_expense_name, is_paid=True)
                return self._finalize_staged_response(staged, enhanced)

            # Ambiguous match or generic invoice intent -> Re-Rank pending candidates
            pending_candidates = []
            for exp in expenses:
                if exp.get("is_pending", True):
                    preview = self.command_service.preview_mutation("toggle_pending_status", {
                        "category": "recurring_expenses",
                        "item_name": exp["name"],
                        "is_paid": True
                    })
                    pending_candidates.append({
                        "item_name": exp["name"],
                        "amount": float(exp.get("recurrent_base", 0.0)),
                        "preview_summary": f"Marcar {exp['name']} como pagado",
                        "delta_incl_pend": preview["impact_delta"]["delta_incl_pend"],
                        "delta_restante": preview["impact_delta"]["delta_restante"],
                        "target_item": preview.get("target_item")
                    })

            if pending_candidates:
                reranked_exps = ReRanker.rerank_disambiguation_options(clean, pending_candidates)
                top_candidate = reranked_exps[0]
                staged = self.propose_toggle_pending_status(
                    top_candidate["item_name"],
                    is_paid=True,
                    candidates=reranked_exps
                )
                return self._finalize_staged_response(
                    staged,
                    enhanced,
                    custom_reply="¿Cuál factura deseas marcar como pagada? Selecciona una de las opciones pendientes:"
                )

        # 7. Direct Account Balance Modification
        has_set_verb = any(v in clean for v in ("modificar", "cambiar", "fijar", "poner", "dejar", "actualizar", "establecer", "ajustar"))
        has_movement_verb = any(v in clean for v in ("gaste", "gasto", "compre", "pague", "retire", "saque", "abono", "ingreso", "recibi", "agregar"))
        identified_acc = _identify_account(clean)

        if has_set_verb and not has_movement_verb and identified_acc:
            amount = _extract_amount(clean, mask_entity=identified_acc)
            if amount is not None:
                staged = self.propose_set_account_balance(identified_acc, amount, note="Actualización directa de saldo")
                return self._finalize_staged_response(staged, enhanced)

        # 8. Add Ledger Adjustment / Natural Expense or Income
        identified_acc = identified_acc or "Daviplata"
        amount = _extract_amount(clean, mask_entity=identified_acc)

        is_expense_phrase = any(v in clean for v in ("gaste", "gasto", "compre", "retire", "saque", "descuento", "costo"))
        is_income_phrase = any(v in clean for v in ("abono", "ingreso", "recibi", "recibo", "meti", "deposite"))
        is_general_add = any(v in clean for v in ("agregar", "anotar", "ajuste", "movimiento"))

        if amount is not None and (is_expense_phrase or is_income_phrase or is_general_add):
            if is_expense_phrase or "gasto" in clean:
                amount_delta = -abs(amount)
            else:
                amount_delta = abs(amount)

            parent_type = "receivable" if identified_acc in RECEIVABLES_MAP.values() else "liquid_account"
            reason = _extract_reason(clean, account_name=identified_acc)
            staged = self.propose_ledger_adjustment(identified_acc, amount_delta, reason, parent_type=parent_type)
            return self._finalize_staged_response(staged, enhanced)

        # 9. Read Investment Capacity
        if any(w in clean for w in ("invertir", "capacidad", "excedente", "incl pend")):
            cap = self.get_investment_capacity("month")
            val = cap["capacidad_invertible"]
            return {
                "type": "read",
                "reply": f"Tu capacidad disponible para invertir este mes (Incl Pend) es de ${val:,.0f} COP. (Fórmula: Restante + Pend - Total Gastos).",
                "data": cap,
                "prompt_enhancement": enhanced
            }

        # 10. Read Account details / balance
        if any(w in clean for w in ("cuanto", "saldo", "estado")):
            summary = self.query_service.get_dashboard_summary()
            for acc in summary["liquid_accounts"]:
                if acc["name"].lower() in clean:
                    return {
                        "type": "read",
                        "reply": f"El saldo actual en {acc['name']} es de ${acc['calculated_total']:,.0f} COP con {len(acc.get('adjustments', []))} movimientos inline.",
                        "data": acc,
                        "prompt_enhancement": enhanced
                    }

        # Default fallback: general summary
        kpis = self.query_service.get_dashboard_summary()["kpis"]
        return {
            "type": "read",
            "reply": f"Actualmente tienes ${kpis['total_actual']:,.0f} COP en liquidez actual, ${kpis['restante']:,.0f} COP de liquidez restante y ${kpis['incl_pend']:,.0f} COP disponible para invertir este mes.",
            "data": kpis,
            "prompt_enhancement": enhanced
        }
