import re
from typing import Dict, Any, List, Optional

def strip_accents(text: str) -> str:
    accents = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u'
    }
    res = text
    for acc, norm in accents.items():
        res = res.replace(acc, norm)
    return res


class PromptEnhancer:
    """
    Non-destructive pre-processing, canonicalization, and intent hint extraction layer
    for raw user voice/text commands.
    Strictly preserves sentence structure and semantics while:
    1. Cleaning currency symbols and units ('$300000' -> '300000', 'COP 50.000' -> '50000').
    2. Normalizing bank and account prefixes ('banco caja social' -> 'caja social').
    3. Normalizing phonetic ASR errors for Colombian financial entities ('david plata' -> 'daviplata', 'neki' -> 'nequi').
    4. Normalizing Colombian colloquial currency multipliers ('50 lucas' -> '50 mil', 'un palo' -> '1000000').
    5. Normalizing safe entity synonyms ('billetera' -> 'bolsillo', 'recibo de la luz' -> 'recibo de energia').
    6. Extracting high-level morphological intent hints (SET_BALANCE, TRANSFER, EXPENSE, INCOME, PAY_BILL, COLLECT, GOAL, UNDO)
       to empower downstream re-ranking.
    """

    # 1. Safe Phonetic ASR & Synonym Replacements for Entities (ordered longest-first)
    ENTITY_NORMALIZATIONS = [
        (r"\bdavid\s+plata\b", "daviplata"),
        (r"\bdavi\s+plata\b", "daviplata"),
        (r"\bdabi\s*plata\b", "daviplata"),
        (r"\bdaviplata\b", "daviplata"),
        (r"\bel\s+banco\s+caja\s+social\b", "caja social"),
        (r"\bbanco\s+caja\s+social\b", "caja social"),
        (r"\bcaja\s+social\b", "caja social"),
        (r"\bcajasocial\b", "caja social"),
        (r"\bneki\b", "nequi"),
        (r"\bneky\b", "nequi"),
        (r"\bnequi\b", "nequi"),
        (r"\bmi\s+billetera\b", "mi bolsillo"),
        (r"\bla\s+billetera\b", "mi bolsillo"),
        (r"\bbilletera\b", "bolsillo"),
        (r"\bmi\s+cartera\b", "mi bolsillo"),
        (r"\bla\s+cartera\b", "mi bolsillo"),
        (r"\ben\s+efectivo\b", "en mi bolsillo"),
        (r"\befectivo\b", "bolsillo"),
        (r"\brecibo\s+de\s+la\s+luz\b", "recibo de energia"),
        (r"\bfactura\s+de\s+la\s+luz\b", "factura de energia"),
        (r"\bservicio\s+de\s+la\s+luz\b", "servicio de energia"),
        (r"\blo\s+de\s+la\s+luz\b", "energia"),
        (r"\blo\s+del\s+gas\b", "gas"),
        (r"\blo\s+del\s+agua\b", "agua"),
        (r"\blo\s+del\s+internet\b", "internet"),
        (r"\bel\s+plan\s+del\s+celular\b", "movistar"),
    ]

    # 2. Colloquial Currency Slang (es-CO)
    CURRENCY_NORMALIZATIONS = [
        (r"\bmedio\s+palo\b", "500000"),
        (r"\bmedio\s+melon\b", "500000"),
        (r"\bun\s+palo\b", "1000000"),
        (r"\bun\s+melon\b", "1000000"),
        (r"\b(\d+(?:[\.,]\d+)?)\s*(?:lucas|lukas|barras)\b", r"\1 mil"),
        (r"\b(\d+(?:[\.,]\d+)?)\s*(?:palos|melones)\b", r"\1 millones"),
        (r"\bcincuenta\s+(?:lucas|lukas|barras)\b", "50000"),
        (r"\bcien\s+(?:lucas|lukas|barras)\b", "100000"),
        (r"\bveinte\s+(?:lucas|lukas|barras)\b", "20000"),
        (r"\btreinta\s+(?:lucas|lukas|barras)\b", "30000"),
        (r"\bcuarenta\s+(?:lucas|lukas|barras)\b", "40000"),
        (r"\bdiez\s+(?:lucas|lukas|barras)\b", "10000"),
    ]

    # 3. Safe Colloquial Verb Phrase Canonicalizations (only unambiguous phrases)
    VERB_CANONICALIZATIONS = [
        # Expense variants -> "gaste"
        (r"\bse\s+me\s+fueron\b", "gaste"),
        (r"\bme\s+gaste\b", "gaste"),
        (r"\bme\s+cobraron\b", "gaste"),
        (r"\bme\s+descontaron\b", "gaste"),
        # Bill payment variants -> "marcar pagado" / "pague"
        (r"\bya\s+quedo\s+pago\b", "marcar pagado"),
        (r"\bya\s+quedo\s+pagado\b", "marcar pagado"),
        (r"\bya\s+cancele\s+(?:el\s+recibo|la\s+factura|el\s+servicio)\b", "pague el recibo"),
        (r"\bcancele\s+el\s+recibo\b", "pague el recibo"),
        (r"\bcancele\s+la\s+factura\b", "pague la factura"),
        # Rent / Receivable collection variants (ONLY when arriendo or tenant name is present)
        (r"\bme\s+consigno\s+lo\s+del\s+arriendo\b", "ya pago el arriendo"),
        (r"\bme\s+transfirio\s+el\s+arriendo\b", "ya pago el arriendo"),
        (r"\bdeposito\s+el\s+arriendo\b", "ya pago el arriendo"),
        # Direct balance set variants -> "fijar en"
        (r"\bquedo\s+en\b", "fijar en"),
        (r"\btiene\s+un\s+saldo\s+de\b", "fijar saldo en"),
    ]

    TENANT_NAMES = ("camila", "ana", "marisol", "angelica", "odeth")

    @classmethod
    def extract_intent_hints(cls, clean_text: str) -> List[str]:
        hints: List[str] = []
        t = clean_text

        # SET_BALANCE hint: actualiza, modificar, cambiar, fijar, poner, pon, deja, ajustar, saldo en, etc.
        if re.search(r"\b(?:actualiz\w*|modific\w*|cambi\w*|fij\w*|establec\w*|ajust\w*|pon\w*|puse|deja\w*|quedo\s+en|queda\s+en|saldo\s+en)\b", t):
            hints.append("SET_BALANCE")

        # TRANSFER hint: mover, mueve, transferir, transfiere, pasar, pasa, sacar, saca, enviar, etc.
        if re.search(r"\b(?:muev\w*|mov\w*|transfier\w*|transfer\w*|pas\w*|sac\w*|retir\w*|envi\w*|mand\w*|traslad\w*)\b", t):
            hints.append("TRANSFER")

        # GOAL hint: meta, metas, or any goal name/alias or saving verbs
        if re.search(r"\b(?:meta|metas|ahorr\w*|abon\w*|aport\w*|destin\w*|separ\w*|guard\w*|maestria|posgrado|visa|english|ingles|brisas|matrimonio|boda|ortodoncia|odontologia)\b", t):
            hints.append("ALLOCATE_GOAL")

        # COLLECT hint: arriendo, cobrado, cobre, ya pago, me pago, consigno, inquilino
        if re.search(r"\b(?:arriendo|cobrad\w*|cobr\w*|ya\s+pago|me\s+pago)\b", t) or (
            any(re.search(rf"\b{name}\b", t) for name in cls.TENANT_NAMES) and re.search(r"\b(?:pago|consign\w*|transfir\w*|deposito)\b", t)
        ):
            hints.append("COLLECT_RECEIVABLE")

        # PAY_BILL hint: factura, recibo, servicio, marcar pagado, como pagado
        if re.search(r"\b(?:factura\w*|recibo\w*|servicio\w*|marcar\s+pagado|como\s+pagado)\b", t):
            hints.append("PAY_EXPENSE")

        # UNDO hint: deshacer, borrar ultimo, eliminar ultimo, revertir
        if re.search(r"\b(?:deshac\w*|deshaz|deshice|borr\w*\s+el\s+ultimo|borr\w*\s+ultimo|elimin\w*\s+ultimo|revert\w*|reviert\w*)\b", t):
            hints.append("UNDO")

        # LEDGER EXPENSE / INCOME hints
        if re.search(r"\b(?:gast\w*|compr\w*|descont\w*|descuent\w*|cobraron|salieron|costo)\b", t):
            hints.append("LEDGER_EXPENSE")
        if re.search(r"\b(?:ingres\w*|deposit\w*|recib\w*|sum\w*|abono\w*|met[ií]|mete|meter)\b", t):
            hints.append("LEDGER_INCOME")

        return hints

    @classmethod
    def enhance(cls, raw_text: str) -> Dict[str, Any]:
        """
        Transforms user variants into a normalized canonical representation
        without corrupting standard commands.
        """
        original = (raw_text or "").strip()
        clean = strip_accents(original).lower()
        clean = re.sub(r"[¿?¡!;:]+", " ", clean)

        # 0. Clean currency symbols and prefixes ($300000 -> 300000, COP 50.000 -> 50.000)
        clean = re.sub(r"\$\s*", "", clean)
        clean = re.sub(r"\b(?:cop|pesos(?:\s+colombianos)?)\b", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        applied_rules: List[str] = []

        # Step 1: Phonetic ASR & Entity synonym replacements
        for pattern, replacement in cls.ENTITY_NORMALIZATIONS:
            new_clean = re.sub(pattern, replacement, clean)
            if new_clean != clean:
                applied_rules.append(f"entity:{replacement}")
                clean = new_clean

        # Step 2: Currency slang normalization
        for pattern, replacement in cls.CURRENCY_NORMALIZATIONS:
            new_clean = re.sub(pattern, replacement, clean)
            if new_clean != clean:
                applied_rules.append(f"currency:{replacement}")
                clean = new_clean

        # Step 3: Safe verb canonicalizations
        for pattern, replacement in cls.VERB_CANONICALIZATIONS:
            new_clean = re.sub(pattern, replacement, clean)
            if new_clean != clean:
                applied_rules.append(f"verb:{replacement}")
                clean = new_clean

        # Context-aware tenant rent normalization: "<tenant> me consigno" -> "<tenant> ya pago el arriendo"
        if any(re.search(rf"\b{t}\b", clean) for t in cls.TENANT_NAMES):
            new_clean = re.sub(r"\bme\s+consigno\b", "ya pago el arriendo", clean)
            if new_clean != clean:
                applied_rules.append("verb:ya pago el arriendo")
                clean = new_clean

        clean = re.sub(r"\s+", " ", clean).strip()
        hints = cls.extract_intent_hints(clean)

        return {
            "raw_text": original,
            "canonical_text": clean,
            "was_enhanced": len(applied_rules) > 0,
            "applied_rules": applied_rules,
            "intent_hints": hints,
        }

    @classmethod
    def build_llm_prompt(cls, raw_text: str, financial_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Builds a context-enriched prompt ready to send to an external LLM (Claude/OpenAI/Groq)
        when AI credentials are active.
        """
        enhanced = cls.enhance(raw_text)
        lines = [
            f"Comando original del usuario: \"{enhanced['raw_text']}\"",
            f"Forma canónica normalizada: \"{enhanced['canonical_text']}\"",
        ]
        if enhanced["applied_rules"]:
            lines.append(f"Normalizaciones aplicadas: {', '.join(enhanced['applied_rules'])}")
        if enhanced.get("intent_hints"):
            lines.append(f"Pistas de intención detectadas: {', '.join(enhanced['intent_hints'])}")
        if financial_context:
            kpis = financial_context.get("kpis", {})
            lines.append(
                f"Contexto KPI Actual: Liquidez Restante=${kpis.get('restante', 0):,.0f} COP, "
                f"Disp. Invertir (Incl Pend)=${kpis.get('incl_pend', 0):,.0f} COP."
            )
        return "\n".join(lines)
