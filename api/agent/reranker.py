import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple
from api.agent.prompt_enhancer import strip_accents


def _char_trigrams(text: str) -> set:
    s = f"  {text.lower().strip()}  "
    return {s[i:i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}


def fuzzy_similarity(a: str, b: str) -> float:
    """
    Combines character trigram Jaccard similarity and SequenceMatcher ratio
    without partial-word substring false positives (e.g. 'gas' is NOT matched inside 'gaste').
    """
    a_norm = strip_accents(a).lower().strip()
    b_norm = strip_accents(b).lower().strip()
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    # Only boost whole-word containment across multi-word strings, never partial tokens
    if (" " in a_norm or " " in b_norm) and (
        re.search(rf"\b{re.escape(a_norm)}\b", b_norm)
        or re.search(rf"\b{re.escape(b_norm)}\b", a_norm)
    ):
        return 0.90

    tri_a = _char_trigrams(a_norm)
    tri_b = _char_trigrams(b_norm)
    union = len(tri_a | tri_b)
    jaccard = len(tri_a & tri_b) / union if union > 0 else 0.0
    seq = SequenceMatcher(None, a_norm, b_norm).ratio()
    return round(0.5 * jaccard + 0.5 * seq, 4)


STOP_TOKENS = {
    "marcar", "pagado", "pague", "pago", "pagar", "factura", "facturas",
    "recibo", "recibos", "servicio", "servicios", "arriendo", "meta",
    "metas", "saldo", "cuenta", "desde", "para", "con", "por", "gaste",
    "gasto", "gastos", "compre", "agregar", "modificar", "cambiar",
    "fijar", "transferi", "transferir", "abonar", "abono", "ingreso",
    "bolsillo", "daviplata", "nequi", "caja", "social", "mil", "pesos",
}


class ReRanker:
    """
    Multi-Signal Candidate Re-Ranker for RBR Finance Manager.
    Scores and re-orders:
    1. Intent / Tool candidates across user phrasing variants and morphological forms.
    2. Domain entities (expenses, receivables, accounts, goals) with strict word boundaries + state priors.
    3. Disambiguation modal options and financial history search results.
    """

    TOOL_EXEMPLARS: Dict[str, List[str]] = {
        "propose_set_account_balance": [
            "actualiza banco caja social a",
            "actualizar saldo de caja social en",
            "actualiza mi cuenta en",
            "modificar el saldo de bolsillo a",
            "modifica mi bolsillo a",
            "fijar daviplata en",
            "fija daviplata en",
            "cambiar el saldo de nequi a",
            "cambia nequi a",
            "pon nequi en",
            "poner bolsillo en",
            "dejar bolsillo en",
            "deja daviplata en",
            "establecer saldo de cuenta en",
            "ajustar saldo de caja social a",
            "daviplata quedo en",
        ],
        "propose_transfer_between_accounts": [
            "mueve desde caja social a bolsillo",
            "mueve de caja social a bolsillo",
            "mover dinero de caja social a bolsillo",
            "transferi de caja social a nequi",
            "transfiere de nequi a daviplata",
            "transferir plata de una cuenta a otra",
            "pase dinero de daviplata a mi bolsillo",
            "pasa de daviplata a bolsillo",
            "pasar plata entre cuentas",
            "saque de caja social para mi bolsillo",
            "saca de daviplata para bolsillo",
            "mover plata desde nequi hacia daviplata",
            "trasladar fondos de cuenta a cuenta",
        ],
        "propose_undo_last_adjustment": [
            "borrar el ultimo movimiento de cuenta",
            "deshacer ultimo ajuste",
            "eliminar ultimo gasto registrado",
            "revertir ultimo movimiento",
        ],
        "propose_allocate_goal": [
            "abonar a la meta de maestria",
            "le meti a la maestria",
            "meter plata a la maestria",
            "asignar dinero a la meta visa",
            "meter ahorro a casa brisas",
            "aportar a meta de ortodoncia",
            "destinar a meta english matrimonio",
        ],
        "propose_collect_receivable": [
            "ana ya pago el arriendo en caja social",
            "marcar cobrado camila",
            "recibi el pago de marisol en nequi",
            "me pagaron un arriendo",
            "odeth ya pago el arriendo",
        ],
        "propose_pay_expense_from_account": [
            "pague el recibo de gas desde mi bolsillo",
            "pague energia con daviplata",
            "pague movistar por nequi",
            "pague factura de agua con caja social",
        ],
        "propose_toggle_pending_status": [
            "marcar pagado gas",
            "pague energia 20",
            "marcar como pagado movistar",
            "marcar pendiente gas",
            "pague una factura recibo servicio",
        ],
        "propose_ledger_adjustment": [
            "gaste en transporte desde mi bolsillo",
            "agregar gasto en daviplata por mercado",
            "abono a cuenta de",
            "compre con nequi",
            "ingreso en caja social",
        ],
    }

    TOOL_INTENT_MAP: Dict[str, List[str]] = {
        "propose_set_account_balance": ["SET_BALANCE"],
        "propose_transfer_between_accounts": ["TRANSFER"],
        "propose_undo_last_adjustment": ["UNDO"],
        "propose_allocate_goal": ["ALLOCATE_GOAL"],
        "propose_collect_receivable": ["COLLECT_RECEIVABLE"],
        "propose_pay_expense_from_account": ["PAY_EXPENSE"],
        "propose_toggle_pending_status": ["PAY_EXPENSE"],
        "propose_ledger_adjustment": ["LEDGER_EXPENSE", "LEDGER_INCOME"],
    }

    @classmethod
    def score_text_against_exemplars(cls, canonical_text: str, tool_name: str) -> float:
        exemplars = cls.TOOL_EXEMPLARS.get(tool_name, [])
        if not exemplars:
            return 0.0
        query_tokens = set(re.findall(r"[a-zñ]+", canonical_text))
        if not query_tokens:
            return 0.0

        best_score = 0.0
        for ex in exemplars:
            ex_tokens = set(re.findall(r"[a-zñ]+", ex))
            overlap = len(query_tokens & ex_tokens) / max(1, len(ex_tokens))
            fuzz = fuzzy_similarity(canonical_text, ex)
            score = 0.65 * overlap + 0.35 * fuzz
            if score > best_score:
                best_score = score
        return round(min(1.0, best_score), 4)

    @classmethod
    def rerank_intent_candidates(
        cls,
        canonical_text: str,
        candidates: List[Dict[str, Any]],
        intent_hints: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate tool calls using 5 weighted signals:
        - w1 (0.30): Exemplar similarity across morphological variations
        - w2 (0.25): Morphological intent hint alignment
        - w3 (0.25): Slot / entity completeness
        - w4 (0.10): Specificity bonus
        - w5 (0.10): Domain state prior / entity confidence
        """
        scored = []
        hints_set = set(intent_hints or [])

        for cand in candidates:
            tool_name = cand.get("tool_name", "")
            s1_exemplar = cls.score_text_against_exemplars(canonical_text, tool_name)

            # Intent alignment
            expected_hints = cls.TOOL_INTENT_MAP.get(tool_name, [])
            if any(h in hints_set for h in expected_hints):
                s2_intent = 1.0
            elif hints_set:
                s2_intent = 0.20
            else:
                s2_intent = 0.70

            s3_slots = float(cand.get("slot_completeness", 0.8))
            s4_specificity = float(cand.get("specificity_bonus", 0.5))
            s5_prior = float(cand.get("state_prior", cand.get("entity_confidence", 0.8)))

            total_score = (
                0.30 * s1_exemplar
                + 0.25 * s2_intent
                + 0.25 * s3_slots
                + 0.10 * s4_specificity
                + 0.10 * s5_prior
            )
            cand_copy = {
                **cand,
                "rerank_score": round(total_score, 4),
            }
            scored.append(cand_copy)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored

    @classmethod
    def rerank_entity_matches(
        cls,
        canonical_text: str,
        items: List[Dict[str, Any]],
        aliases_map: Optional[Dict[str, str]] = None,
        prefer_pending: bool = True,
        threshold: float = 0.75
    ) -> List[Tuple[Dict[str, Any], float]]:
        clean = strip_accents(canonical_text).lower()
        words = [w for w in re.findall(r"[a-zñ0-9]+", clean) if len(w) >= 5 and w not in STOP_TOKENS]

        item_aliases: Dict[str, List[str]] = {}
        if aliases_map:
            for alias, official in aliases_map.items():
                item_aliases.setdefault(official.lower(), []).append(strip_accents(alias).lower())

        ranked: List[Tuple[Dict[str, Any], float]] = []
        for item in items:
            raw_name = item.get("name", "")
            name_clean = strip_accents(raw_name).lower()
            base_name = re.sub(r"\s+\d+(?:-\d+)?$", "", name_clean).strip()

            base_score = 0.0

            # 1. Exact full name match (e.g. "gas 15", "servicio 30")
            if re.search(rf"\b{re.escape(name_clean)}\b", clean):
                base_score = 0.99
            # 2. Exact base name match (avoiding generic 'servicio' when used as 'servicio de <x>' or 'un servicio')
            elif base_name and re.search(rf"\b{re.escape(base_name)}\b", clean):
                if base_name == "servicio" and (
                    re.search(r"\b(?:un|el|la|algun)\s+servicio\b", clean)
                    or re.search(r"\bservicio\s+de\b", clean)
                ):
                    base_score = 0.0
                else:
                    base_score = 0.95
            else:
                # 3. Check aliases mapped specifically to this item
                for al in item_aliases.get(raw_name.lower(), []):
                    if al in ("servicio", "servicios") and (
                        re.search(r"\b(?:un|el|la|algun)\s+servicio\b", clean)
                        or re.search(r"\bservicio\s+de\b", clean)
                    ):
                        continue
                    if re.search(rf"\b{re.escape(al)}\b", clean):
                        base_score = 0.92
                        break

                # 4. Strict typo tolerance only for long words (>=5 chars)
                if base_score == 0.0 and len(base_name) >= 5:
                    for w in words:
                        if abs(len(w) - len(base_name)) <= 2:
                            sim = SequenceMatcher(None, w, base_name).ratio()
                            if sim >= 0.84 and (sim * 0.88) > base_score:
                                base_score = round(sim * 0.88, 4)

            if base_score >= threshold:
                is_pend = item.get("is_pending", not item.get("is_paid", False))
                prior_boost = 0.03 if (prefer_pending and is_pend) else 0.0
                final_score = round(min(1.0, base_score + prior_boost), 4)
                ranked.append((item, final_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    @classmethod
    def rerank_disambiguation_options(
        cls,
        canonical_text: str,
        options: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not options:
            return []

        max_amount = max((abs(float(o.get("amount", 0.0))) for o in options), default=1.0) or 1.0
        scored = []
        for opt in options:
            name = opt.get("item_name", "")
            sim = fuzzy_similarity(canonical_text, name)
            amt_norm = abs(float(opt.get("amount", 0.0))) / max_amount
            score = round(0.70 * sim + 0.30 * amt_norm, 4)
            scored.append({**opt, "rerank_score": score})

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored

    @classmethod
    def rerank_history_results(cls, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not results:
            return []
        scored = []
        for item in results:
            label = f"{item.get('name', '')} {item.get('cuenta', '')} {item.get('nota', '')}".strip()
            score = fuzzy_similarity(query, label)
            scored.append({**item, "relevance_score": score})
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored
