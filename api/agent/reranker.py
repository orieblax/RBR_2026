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
    for fast, zero-dependency fuzzy matching in serverless environments.
    """
    a_norm = strip_accents(a).lower().strip()
    b_norm = strip_accents(b).lower().strip()
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if a_norm in b_norm or b_norm in a_norm:
        return 0.90

    tri_a = _char_trigrams(a_norm)
    tri_b = _char_trigrams(b_norm)
    union = len(tri_a | tri_b)
    jaccard = len(tri_a & tri_b) / union if union > 0 else 0.0
    seq = SequenceMatcher(None, a_norm, b_norm).ratio()
    return round(0.5 * jaccard + 0.5 * seq, 4)


class ReRanker:
    """
    Multi-Signal Candidate Re-Ranker for RBR Finance Manager.
    Scores and re-orders:
    1. Intent / Tool candidates across user phrasing variants.
    2. Domain entities (expenses, receivables, accounts, goals) with fuzzy + state priors.
    3. Financial history search results.
    """

    # Canonical exemplar templates per tool for semantic/lexical overlap scoring
    TOOL_EXEMPLARS: Dict[str, List[str]] = {
        "propose_undo_last_adjustment": [
            "borrar el ultimo movimiento de cuenta",
            "deshacer ultimo ajuste",
            "eliminar ultimo gasto registrado",
            "revertir ultimo movimiento",
        ],
        "propose_allocate_goal": [
            "abonar a la meta de maestria",
            "asignar dinero a la meta visa",
            "meter ahorro a casa brisas",
            "aportar a meta de ortodoncia",
            "destinar a meta english matrimonio",
        ],
        "propose_transfer_between_accounts": [
            "transferi de caja social a nequi",
            "pase dinero de daviplata a mi bolsillo",
            "saque de caja social para mi bolsillo",
            "mover plata desde nequi hacia daviplata",
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
        "propose_set_account_balance": [
            "modificar el saldo de bolsillo a",
            "fijar daviplata en",
            "cambiar el saldo de nequi a",
            "actualizar saldo de caja social en",
            "dejar bolsillo en",
        ],
        "propose_ledger_adjustment": [
            "gaste en transporte desde mi bolsillo",
            "agregar gasto en daviplata por mercado",
            "abono a cuenta de",
            "compre con nequi",
            "ingreso en caja social",
        ],
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
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Scores each candidate tool invocation using 5 weighted signals:
        - w1 (0.35): Exemplar similarity
        - w2 (0.25): Slot/entity completeness
        - w3 (0.15): Fuzzy match quality
        - w4 (0.15): Database state prior (e.g. pending *1 status)
        - w5 (0.10): Compound specificity bonus
        Returns candidates sorted descending by `rerank_score`.
        """
        scored = []
        for cand in candidates:
            tool_name = cand.get("tool_name", "")
            s1_exemplar = cls.score_text_against_exemplars(canonical_text, tool_name)
            s2_slots = float(cand.get("slot_completeness", 0.8))
            s3_fuzzy = float(cand.get("entity_match_score", 0.85))
            s4_prior = float(cand.get("state_prior", 0.8))
            s5_specificity = float(cand.get("specificity_bonus", 0.5))

            total_score = (
                0.35 * s1_exemplar
                + 0.25 * s2_slots
                + 0.15 * s3_fuzzy
                + 0.15 * s4_prior
                + 0.10 * s5_specificity
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
        threshold: float = 0.52
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Ranks domain entities (expenses, receivables, accounts, goals) against the utterance.
        Combines exact token match, alias match, fuzzy token similarity, and pending state prior.
        """
        clean = strip_accents(canonical_text).lower()
        words = [w for w in re.findall(r"[a-zñ0-9]+", clean) if len(w) >= 3]

        alias_target = None
        if aliases_map:
            for alias, official in sorted(aliases_map.items(), key=lambda x: -len(x[0])):
                if re.search(rf"\b{re.escape(alias)}\b", clean):
                    alias_target = official.lower()
                    break

        ranked: List[Tuple[Dict[str, Any], float]] = []
        for item in items:
            raw_name = item.get("name", "")
            name_clean = strip_accents(raw_name).lower()
            base_name = re.sub(r"\s+\d+(?:-\d+)?$", "", name_clean).strip()

            base_score = 0.0
            if alias_target and alias_target == raw_name.lower():
                base_score = 0.98
            elif re.search(rf"\b{re.escape(name_clean)}\b", clean):
                base_score = 0.96
            elif base_name and re.search(rf"\b{re.escape(base_name)}\b", clean):
                base_score = 0.92
            else:
                # Fuzzy token comparison for slight typos / ASR phonetic variants
                for w in words:
                    if w in ("marcar", "pagado", "pague", "pago", "factura", "recibo", "arriendo", "meta", "saldo", "cuenta", "desde", "para", "con", "por"):
                        continue
                    sim = fuzzy_similarity(w, base_name)
                    if sim >= 0.78 and sim > base_score:
                        base_score = sim * 0.88

            if base_score >= threshold:
                # Apply pending state prior boost (+0.04 if currently pending)
                is_pend = item.get("is_pending", not item.get("is_paid", False))
                prior_boost = 0.04 if (prefer_pending and is_pend) else 0.0
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
        """
        Re-orders disambiguation candidates shown in the ConfirmationModal
        by relevance to the query and financial impact magnitude.
        """
        if not options:
            return []

        max_amount = max((abs(float(o.get("amount", 0.0))) for o in options), default=1.0) or 1.0
        scored = []
        for opt in options:
            name = opt.get("item_name", "")
            sim = fuzzy_similarity(canonical_text, name)
            amt_norm = abs(float(opt.get("amount", 0.0))) / max_amount
            # Combine query similarity (70%) + amount significance (30%)
            score = round(0.70 * sim + 0.30 * amt_norm, 4)
            scored.append({**opt, "rerank_score": score})

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored

    @classmethod
    def rerank_history_results(cls, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-ranks financial history search hits by lexical + fuzzy similarity.
        """
        if not results:
            return []
        scored = []
        for item in results:
            label = f"{item.get('name', '')} {item.get('cuenta', '')} {item.get('nota', '')}".strip()
            score = fuzzy_similarity(query, label)
            scored.append({**item, "relevance_score": score})
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored
