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
    Pre-processes and canonicalizes raw user voice/text commands before intent routing or LLM generation.
    Handles:
    1. Phonetic ASR corrections for Colombian Spanish financial entities (e.g. 'david plata' -> 'daviplata', 'neki' -> 'nequi').
    2. Colloquial slang and currency multipliers ('50 lucas' -> '50000', 'un palo' -> '1000000', 'billetera' -> 'bolsillo').
    3. Verb phrase canonicalization (mapping diverse natural expressions to canonical financial verbs).
    4. Structured context enrichment for downstream LLM / NLU consumption.
    """

    # 1. Phonetic ASR & Synonym Replacements for Entities (ordered longest-first)
    ENTITY_NORMALIZATIONS = [
        (r"\bdavid\s+plata\b", "daviplata"),
        (r"\bdavi\s+plata\b", "daviplata"),
        (r"\bdabi\s*plata\b", "daviplata"),
        (r"\bdaviplata\b", "daviplata"),
        (r"\bbanco\s+caja\s+social\b", "caja social"),
        (r"\bcaja\s+social\b", "caja social"),
        (r"\bcajasocial\b", "caja social"),
        (r"\bla\s+caja\b", "caja social"),
        (r"\bneki\b", "nequi"),
        (r"\bneky\b", "nequi"),
        (r"\bnequi\b", "nequi"),
        (r"\bmi\s+billetera\b", "mi bolsillo"),
        (r"\bla\s+billetera\b", "mi bolsillo"),
        (r"\bbilletera\b", "bolsillo"),
        (r"\bmi\s+cartera\b", "mi bolsillo"),
        (r"\bla\s+cartera\b", "mi bolsillo"),
        (r"\ben\s+efectivo\b", "desde mi bolsillo"),
        (r"\befectivo\b", "bolsillo"),
        (r"\brecibo\s+de\s+la\s+luz\b", "recibo de energia"),
        (r"\bfactura\s+de\s+la\s+luz\b", "factura de energia"),
        (r"\blo\s+de\s+la\s+luz\b", "energia"),
        (r"\blo\s+del\s+gas\b", "gas"),
        (r"\blo\s+del\s+agua\b", "agua"),
        (r"\blo\s+del\s+internet\b", "internet"),
        (r"\blo\s+del\s+celular\b", "movistar"),
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

    # 3. Colloquial Verb Phrase Canonicalizations
    VERB_CANONICALIZATIONS = [
        # Expense variants -> "gaste"
        (r"\bse\s+me\s+fueron\b", "gaste"),
        (r"\bme\s+gaste\b", "gaste"),
        (r"\bme\s+cobraron\b", "gaste"),
        (r"\bme\s+descontaron\b", "gaste"),
        (r"\bsalieron\b", "gaste"),
        (r"\bpague\s+por\b", "gaste en"),
        # Bill payment variants -> "marcar pagado" / "pague"
        (r"\bya\s+quedo\s+pago\b", "marcar pagado"),
        (r"\bya\s+quedo\s+pagado\b", "marcar pagado"),
        (r"\bya\s+cancele\b", "pague"),
        (r"\bcancele\s+el\s+recibo\b", "pague el recibo"),
        (r"\bcancele\s+la\s+factura\b", "pague la factura"),
        (r"\bliquide\b", "marcar pagado"),
        # Rent / Receivable collection variants -> "pago el arriendo"
        (r"\bme\s+consigno\s+lo\s+del\s+arriendo\b", "ya pago el arriendo"),
        (r"\bme\s+consigno\b", "ya pago el arriendo"),
        (r"\bme\s+transfirio\s+el\s+arriendo\b", "ya pago el arriendo"),
        (r"\bse\s+puso\s+al\s+dia\b", "ya pago el arriendo"),
        (r"\bdeposito\s+el\s+arriendo\b", "ya pago el arriendo"),
        # Goal allocation variants -> "abonar a la meta"
        (r"\ble\s+meti\b", "abonar"),
        (r"\bguarde\b", "abonar"),
        (r"\bahorre\b", "abonar"),
        (r"\bsepare\b", "abonar"),
        # Direct balance set variants -> "fijar"
        (r"\bquedo\s+en\b", "fijar en"),
        (r"\btiene\s+un\s+saldo\s+de\b", "fijar saldo en"),
        (r"\bdeje\s+en\b", "dejar en"),
    ]

    @classmethod
    def enhance(cls, raw_text: str) -> Dict[str, Any]:
        """
        Transforms any user variant into a normalized canonical representation
        while preserving the original text and tracking applied transformations.
        """
        original = (raw_text or "").strip()
        clean = strip_accents(original).lower()
        clean = re.sub(r"[¿?¡!;:]+", " ", clean)
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

        # Step 3: Colloquial verb canonicalization
        for pattern, replacement in cls.VERB_CANONICALIZATIONS:
            new_clean = re.sub(pattern, replacement, clean)
            if new_clean != clean:
                applied_rules.append(f"verb:{replacement}")
                clean = new_clean

        clean = re.sub(r"\s+", " ", clean).strip()

        return {
            "raw_text": original,
            "canonical_text": clean,
            "was_enhanced": len(applied_rules) > 0,
            "applied_rules": applied_rules,
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
        if financial_context:
            kpis = financial_context.get("kpis", {})
            lines.append(
                f"Contexto KPI Actual: Liquidez Restante=${kpis.get('restante', 0):,.0f} COP, "
                f"Disp. Invertir (Incl Pend)=${kpis.get('incl_pend', 0):,.0f} COP."
            )
        return "\n".join(lines)
