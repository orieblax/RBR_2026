import pytest
from api.seed import generate_seed_data
from api.domain.calculator import FinancialCalculator
from api.core.security import vault, TokenVault
from api.queries.finance_queries import FinanceQueryService
from api.commands.finance_commands import FinanceCommandService
from api.agent.llm_factory import LLMFactory
from api.agent.finance_agent import FinanceAgent

def test_excel_parity_exact_numbers():
    user_id = "test-user-parity"
    dataset = generate_seed_data(user_id)
    kpis = FinancialCalculator.calculate_full_kpis(dataset)

    # 1. Total actual = 1,296,516 (B18)
    assert kpis.total_actual == 1296516.00, f"Expected 1,296,516 got {kpis.total_actual}"

    # 2. Gastos mes = 345,000 (B19 / G18)
    assert kpis.gastos_mes == 345000.00, f"Expected 345,000 got {kpis.gastos_mes}"

    # 3. Restante = 951,516 (B20 = B18 - G18)
    assert kpis.restante == 951516.00, f"Expected 951,516 got {kpis.restante}"

    # 4. Ingresos = 3,179,933.33 (D18)
    assert kpis.ingresos == 3179933.33, f"Expected 3,179,933.33 got {kpis.ingresos}"

    # 5. Total gastos = 3,053,000 (F18)
    assert kpis.total_gastos == 3053000.00, f"Expected 3,053,000 got {kpis.total_gastos}"

    # 6. Ahorro = 126,933.33 (D20 = D18 - F18)
    assert kpis.ahorro == 126933.33, f"Expected 126,933.33 got {kpis.ahorro}"

    # 7. Pend = 4,101,217.33 (B21)
    assert kpis.pend == 4101217.33, f"Expected 4,101,217.33 got {kpis.pend}"

    # 8. Incl Pend (Invertible) = 1,999,733.33 (B22 = B20 + B21 - F18)
    assert kpis.incl_pend == 1999733.33, f"Expected 1,999,733.33 got {kpis.incl_pend}"

def test_liquid_accounts_individual_parity():
    user_id = "test-user-liquid"
    dataset = generate_seed_data(user_id)
    accounts = {acc["name"]: FinancialCalculator.calculate_liquid_account_total(acc) for acc in dataset["liquid_accounts"]}

    assert accounts["Daviplata"] == 2893.00
    assert accounts["Caja social"] == 987948.00
    assert accounts["Bolsillo"] == 205000.00
    assert accounts["Colchon"] == 0.00
    assert accounts["Nequi"] == 100675.00

def test_receivables_individual_parity():
    user_id = "test-user-rec"
    dataset = generate_seed_data(user_id)
    fiducia_yield = FinancialCalculator.calculate_fiducia_monthly_yield(32560000.0)
    sum_extras = sum(FinancialCalculator.calculate_monthly_extra_value(e) for e in dataset["monthly_extras"])

    recs = {r["name"]: FinancialCalculator.calculate_receivable_value(r, fiducia_yield, sum_extras) for r in dataset["receivables"]}

    assert round(recs["Fiducia"], 2) == 189933.33
    assert recs["Ana 26"] == 700000.00
    assert recs["Marisol 23"] == 904300.00
    assert recs["Camila 20"] == 527984.00
    assert recs["Angelica 1"] == 500000.00
    assert recs["Odeth 28"] == 300000.00
    assert recs["Pagos Extras"] == 979000.00

def test_cqrs_query_and_command_parity():
    user_id = "test-cqrs-user"
    q_service = FinanceQueryService(user_id)
    c_service = FinanceCommandService(user_id)

    summary = q_service.get_dashboard_summary()
    assert summary["kpis"]["incl_pend"] == 1999733.33
    assert summary["kpis"]["restante"] == 951516.00

    # Test preview mutation: marking Energia 20 ($180,000) as paid (*0)
    preview = c_service.preview_mutation(
        "toggle_pending_status",
        {"category": "recurring_expenses", "item_name": "Energía 20", "is_paid": True}
    )
    assert preview["impact_delta"]["delta_restante"] == 180000.00
    assert preview["impact_delta"]["delta_incl_pend"] == 180000.00

    # Test actual command execution
    res = c_service.execute_toggle_pending("recurring_expenses", "Energía 20", True)
    assert res["status"] == "success"
    new_summary = q_service.get_dashboard_summary()
    assert new_summary["kpis"]["gastos_mes"] == 165000.00
    assert new_summary["kpis"]["restante"] == 1131516.00
    assert new_summary["kpis"]["incl_pend"] == 2179733.33

def test_token_vault_security():
    setup_token = "sk-ant-oat01-my-claude-setup-token-value"
    encrypted = vault.encrypt(setup_token)
    assert encrypted != setup_token
    decrypted = vault.decrypt(encrypted)
    assert decrypted == setup_token

    classified = TokenVault.classify_token(setup_token)
    assert classified["provider"] == "anthropic"
    assert classified["auth_mode"] == "oauth_token"
    assert classified["beta_header"] == "oauth-2025-04-20"

def test_llm_factory_ping_test():
    result_setup = LLMFactory.ping_test_token("sk-ant-oat01-dummy-test-key-here-12345")
    assert result_setup["status"] == "success"
    assert result_setup["auth_mode"] == "oauth_token"

    result_openai = LLMFactory.ping_test_token("sk-dummy-test-key-here-12345")
    assert result_openai["status"] == "success"
    assert result_openai["provider"] == "openai"

def test_voice_agent_two_step_safety():
    user_id = "test-voice-user"
    agent = FinanceAgent(user_id)

    # 1. Read command: does not stage
    read_res = agent.process_voice_command("¿cuánto puedo invertir este mes?")
    assert read_res["type"] == "read"
    assert "1,999,733" in read_res["reply"]

    # 2. Write command: stages action, does NOT mutate DB immediately
    stage_res = agent.process_voice_command("marcar pagado Energía 20")
    assert stage_res["type"] == "stage_action"
    staged = stage_res["staged_action"]
    assert staged["impact_delta"]["delta_restante"] == 180000.0
    assert staged["impact_delta"]["delta_incl_pend"] == 180000.0

    # 3. Confirm action via voice command "confirmar"
    confirm_res = agent.process_voice_command("confirmar")
    assert confirm_res["type"] == "confirmed"
    assert confirm_res["needs_refresh"] is True

    # Check that database was updated only after confirmation
    summary = agent.query_service.get_dashboard_summary()
    assert summary["kpis"]["gastos_mes"] == 165000.00

def test_vercel_bundle_limits():
    with open("api/requirements.txt", "r") as f:
        reqs = f.read().lower()

    # Rule 4: NEVER install heavy torch or transformers in serverless
    forbidden = ["torch", "transformers", "sentence-transformers", "scipy", "tensorflow"]
    for pkg in forbidden:
        assert pkg not in reqs, f"Heavy dependency '{pkg}' violates Vercel 250MB serverless limit"

def test_use_case_1_natural_expense_bolsillo():
    user_id = "test-case-1-user"
    agent = FinanceAgent(user_id)
    cmd = "Gasté 50000 en transporte desde mi bolsillo"
    res = agent.process_voice_command(cmd)

    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_ledger_adjustment"
    assert staged["target_item"]["name"] == "Bolsillo"
    assert staged["target_item"]["before_value"] == 205000.0
    assert staged["target_item"]["after_value"] == 155000.0
    assert staged["target_item"]["delta"] == -50000.0
    assert staged["target_item"]["note"] == "Transporte"

    # Confirm
    agent.confirm_action(staged["action_id"])
    summary = agent.query_service.get_dashboard_summary()
    bolsillo = next(a for a in summary["liquid_accounts"] if a["name"] == "Bolsillo")
    assert bolsillo["calculated_total"] == 155000.0

def test_use_case_2_thousands_with_spaces_daviplata():
    user_id = "test-case-2-user"
    agent = FinanceAgent(user_id)
    cmd = "Agregar gasto en Daviplata de 50 000 por mercado"
    res = agent.process_voice_command(cmd)

    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_ledger_adjustment"
    assert staged["target_item"]["name"] == "Daviplata"
    assert staged["target_item"]["delta"] == -50000.0
    assert staged["target_item"]["delta"] != -50.0  # Must not truncate at whitespace!
    assert staged["target_item"]["note"] == "Mercado"

def test_use_case_3_direct_account_balance_modification():
    user_id = "test-case-3-user"
    agent = FinanceAgent(user_id)

    # 1. Direct set on Bolsillo
    res1 = agent.process_voice_command("Modificar el saldo de Bolsillo a 300000")
    assert res1["type"] == "stage_action"
    staged1 = res1["staged_action"]
    assert staged1["tool_name"] == "propose_set_account_balance"
    assert staged1["target_item"]["name"] == "Bolsillo"
    assert staged1["target_item"]["after_value"] == 300000.0
    agent.confirm_action(staged1["action_id"])

    summary1 = agent.query_service.get_dashboard_summary()
    bolsillo = next(a for a in summary1["liquid_accounts"] if a["name"] == "Bolsillo")
    assert bolsillo["calculated_total"] == 300000.0

    # 2. Direct set on Daviplata with space thousands
    res2 = agent.process_voice_command("Fijar Daviplata en 150 000")
    assert res2["type"] == "stage_action"
    staged2 = res2["staged_action"]
    assert staged2["tool_name"] == "propose_set_account_balance"
    assert staged2["target_item"]["name"] == "Daviplata"
    assert staged2["target_item"]["after_value"] == 150000.0
    agent.confirm_action(staged2["action_id"])

    summary2 = agent.query_service.get_dashboard_summary()
    davi = next(a for a in summary2["liquid_accounts"] if a["name"] == "Daviplata")
    assert davi["calculated_total"] == 150000.0

def test_use_case_4_fuzzy_invoice_and_disambiguation():
    user_id = "test-case-4-user"
    agent = FinanceAgent(user_id)

    # 1. Fuzzy match "Gas" -> "Gas 15"
    res = agent.process_voice_command("Marcar pagado Gas")
    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_toggle_pending_status"
    assert staged["target_item"]["name"] == "Gas 15"
    assert staged["target_item"]["after_status"] == "Pagado"

    # 2. Generic ambiguous bill command returns candidate list
    res_ambiguous = agent.process_voice_command("pagué una factura")
    assert res_ambiguous["type"] == "stage_action"
    staged_amb = res_ambiguous["staged_action"]
    assert len(staged_amb["candidates"]) > 0
    # Candidate can be confirmed
    chosen_candidate = staged_amb["candidates"][0]
    confirm_res = agent.confirm_action(staged_amb["action_id"], selected_candidate=chosen_candidate)
    assert confirm_res["status"] == "success"

def test_use_case_5_collect_receivable_with_deposit():
    user_id = "test-case-5-user"
    agent = FinanceAgent(user_id)

    res = agent.process_voice_command("Ana ya pagó el arriendo en Caja Social")
    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_collect_receivable"
    assert staged["target_item"]["name"] == "Ana 26"
    assert staged["target_item"]["after_status"] == "Cobrado"
    assert staged["target_item"]["secondary_item"]["name"] == "Caja social"
    assert staged["target_item"]["secondary_item"]["delta"] == 700000.0
    # Restante goes up by +700,000, Incl Pend stays unchanged ($0 delta) because Pend goes down -700,000
    assert staged["impact_delta"]["delta_restante"] == 700000.0
    assert staged["impact_delta"]["delta_incl_pend"] == 0.0

    agent.confirm_action(staged["action_id"])
    summary = agent.query_service.get_dashboard_summary()
    caja = next(a for a in summary["liquid_accounts"] if a["name"] == "Caja social")
    assert caja["calculated_total"] == 987948.0 + 700000.0

def test_use_case_6_pay_expense_from_account():
    user_id = "test-case-6-user"
    agent = FinanceAgent(user_id)

    res = agent.process_voice_command("Pagué el recibo de Gas desde mi bolsillo")
    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_pay_expense_from_account"
    assert staged["target_item"]["name"] == "Gas 15"
    assert staged["target_item"]["after_status"] == "Pagado"
    assert staged["target_item"]["secondary_item"]["name"] == "Bolsillo"
    assert staged["target_item"]["secondary_item"]["after_value"] == 195000.0

    agent.confirm_action(staged["action_id"])
    summary = agent.query_service.get_dashboard_summary()
    bolsillo = next(a for a in summary["liquid_accounts"] if a["name"] == "Bolsillo")
    assert bolsillo["calculated_total"] == 195000.0
    gas = next(e for e in summary["recurring_expenses"] if e["name"] == "Gas 15")
    assert gas["is_paid"] is True

def test_use_case_7_transfer_between_accounts():
    user_id = "test-case-7-user"
    agent = FinanceAgent(user_id)

    res = agent.process_voice_command("Transferí 100 000 de Caja Social a Nequi")
    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_transfer_between_accounts"
    assert staged["target_item"]["name"] == "Caja social"
    assert staged["target_item"]["delta"] == -100000.0
    assert staged["target_item"]["secondary_item"]["name"] == "Nequi"
    assert staged["target_item"]["secondary_item"]["delta"] == 100000.0
    assert staged["impact_delta"]["delta_restante"] == 0.0

    agent.confirm_action(staged["action_id"])
    summary = agent.query_service.get_dashboard_summary()
    caja = next(a for a in summary["liquid_accounts"] if a["name"] == "Caja social")
    nequi = next(a for a in summary["liquid_accounts"] if a["name"] == "Nequi")
    assert caja["calculated_total"] == 887948.0
    assert nequi["calculated_total"] == 200675.0

def test_use_case_8_financial_goals_allocation_and_query():
    user_id = "test-case-8-user"
    agent = FinanceAgent(user_id)

    # 1. Allocate to Maestría
    res = agent.process_voice_command("Abonar 300 000 a la meta de Maestría")
    assert res["type"] == "stage_action"
    staged = res["staged_action"]
    assert staged["tool_name"] == "propose_allocate_goal"
    assert staged["target_item"]["name"] == "Maestría"
    assert staged["target_item"]["before_value"] == 3500000.0
    assert staged["target_item"]["after_value"] == 3800000.0
    agent.confirm_action(staged["action_id"])

    # 2. Query specific goal
    q_res = agent.process_voice_command("¿Cuánto me falta para la meta de Visa?")
    assert q_res["type"] == "read"
    assert "Visa" in q_res["reply"]
    assert "1,200,000" in q_res["reply"]

def test_use_case_9_undo_last_adjustment_and_pending_queries():
    user_id = "test-case-9-user"
    agent = FinanceAgent(user_id)

    # 1. Query pending bills
    q_bills = agent.process_voice_command("¿Qué facturas tengo pendientes?")
    assert q_bills["type"] == "read"
    assert "345,000" in q_bills["reply"]
    assert "Gas 15" in q_bills["reply"]

    # 2. Query pending receivables
    q_recs = agent.process_voice_command("¿Quién falta por pagar arriendo?")
    assert q_recs["type"] == "read"
    assert "Ana 26" in q_recs["reply"]

    # 3. Undo last adjustment in Daviplata (last seed adjustment is -3600 Comisión)
    undo_res = agent.process_voice_command("Borrar el último movimiento de Daviplata")
    assert undo_res["type"] == "stage_action"
    staged = undo_res["staged_action"]
    assert staged["tool_name"] == "propose_undo_last_adjustment"
    assert staged["target_item"]["name"] == "Daviplata"
    assert staged["target_item"]["delta"] == 3600.0
    agent.confirm_action(staged["action_id"])

    summary = agent.query_service.get_dashboard_summary()
    davi = next(a for a in summary["liquid_accounts"] if a["name"] == "Daviplata")
    assert davi["calculated_total"] == 2893.0 + 3600.0

def test_use_case_10_prompt_enhancer_and_reranker_variants():
    from api.agent.prompt_enhancer import PromptEnhancer
    from api.agent.reranker import ReRanker

    user_id = "test-case-10-user"
    agent = FinanceAgent(user_id)

    # Variant 1: Colloquial slang ("Se me fueron 50 lucas") + synonym ("billetera") -> Bolsillo -50,000 Taxi
    res1 = agent.process_voice_command("Se me fueron 50 lucas en taxi desde la billetera")
    assert res1["type"] == "stage_action"
    assert res1["prompt_enhancement"]["was_enhanced"] is True
    staged1 = res1["staged_action"]
    assert staged1["tool_name"] == "propose_ledger_adjustment"
    assert staged1["target_item"]["name"] == "Bolsillo"
    assert staged1["target_item"]["delta"] == -50000.0
    assert staged1["target_item"]["note"] == "Taxi"
    assert staged1["rerank_score"] > 0

    # Variant 2: ASR phonetic transcription ("David plata") + balance setter
    res2 = agent.process_voice_command("David plata quedó en 150 mil")
    assert res2["type"] == "stage_action"
    staged2 = res2["staged_action"]
    assert staged2["tool_name"] == "propose_set_account_balance"
    assert staged2["target_item"]["name"] == "Daviplata"
    assert staged2["target_item"]["after_value"] == 150000.0

    # Variant 3: Colloquial bill payment ("Ya cancelé el recibo de la luz con neki") -> Energía 20 + Nequi
    res3 = agent.process_voice_command("Ya cancelé el recibo de la luz con neki")
    assert res3["type"] == "stage_action"
    staged3 = res3["staged_action"]
    assert staged3["tool_name"] == "propose_pay_expense_from_account"
    assert staged3["target_item"]["name"] == "Energía 20"
    assert staged3["target_item"]["secondary_item"]["name"] == "Nequi"

    # Variant 4: Colloquial rent collection ("Ana me consignó lo del arriendo en el banco caja social")
    res4 = agent.process_voice_command("Ana me consignó lo del arriendo en el banco caja social")
    assert res4["type"] == "stage_action"
    staged4 = res4["staged_action"]
    assert staged4["tool_name"] == "propose_collect_receivable"
    assert staged4["target_item"]["name"] == "Ana 26"
    assert staged4["target_item"]["secondary_item"]["name"] == "Caja social"

    # Variant 5: Colloquial goal allocation ("Le metí 300 lucas a la maestría")
    res5 = agent.process_voice_command("Le metí 300 lucas a la maestría")
    assert res5["type"] == "stage_action"
    staged5 = res5["staged_action"]
    assert staged5["tool_name"] == "propose_allocate_goal"
    assert staged5["target_item"]["name"] == "Maestría"
    assert staged5["target_item"]["delta"] == 300000.0

    # Variant 6: Re-Ranker direct intent ranking verification
    enh = PromptEnhancer.enhance("Pasé 100 barras de davi plata a neki")
    ranked = ReRanker.rerank_intent_candidates(
        enh["canonical_text"],
        [
            {"tool_name": "propose_ledger_adjustment", "has_amount": True, "entity_confidence": 0.9},
            {"tool_name": "propose_transfer_between_accounts", "has_amount": True, "entity_confidence": 0.95},
        ],
    )
    assert ranked[0]["tool_name"] == "propose_transfer_between_accounts"
    assert ranked[0]["rerank_score"] > ranked[1]["rerank_score"]


def test_ai_model_persistence_across_restarts(tmp_path):
    from api.repositories.settings_repo import SettingsRepository
    from api.index import (
        update_default_ai_model,
        UpdateDefaultModelRequest,
        get_admin_diagnostics,
        save_ai_credentials,
        SaveAICredentialRequest,
        get_ai_credentials,
    )

    original_path = SettingsRepository._store_path
    test_store = tmp_path / ".rbr_settings_store.json"
    try:
        SettingsRepository.set_store_path(test_store)
        demo_user = {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": "albeiro@rbrfinance.com",
            "is_admin": True,
        }

        # 1. Update Global Default Model in /admin
        update_default_ai_model(UpdateDefaultModelRequest(model="gpt-4o"), admin=demo_user)

        # Simulate server restart by clearing cache & reloading from disk
        SettingsRepository.load_state(force_reload=True)

        diag = get_admin_diagnostics(admin=demo_user)
        assert diag["system"]["default_ai_model"] == "gpt-4o"

        # Without a custom user credential yet, /settings/ai should also reflect the saved global model
        ai_cfg = get_ai_credentials(current_user=demo_user)
        assert ai_cfg["preferred_model"] == "gpt-4o"

        # 2. Save Preferred Model in /settings/ai with token
        save_ai_credentials(
            SaveAICredentialRequest(
                provider="groq",
                token="gsk_test_token_1234567890",
                preferred_model="llama-3.3-70b-versatile",
            ),
            current_user=demo_user,
        )

        # Simulate server restart
        SettingsRepository.load_state(force_reload=True)
        ai_cfg_after = get_ai_credentials(current_user=demo_user)
        assert ai_cfg_after["has_credential"] is True
        assert ai_cfg_after["provider"] == "groq"
        assert ai_cfg_after["preferred_model"] == "llama-3.3-70b-versatile"

        # 3. Update Preferred Model in /settings/ai WITHOUT re-entering token
        save_ai_credentials(
            SaveAICredentialRequest(
                provider="groq",
                token=None,
                preferred_model="deepseek-r1-distill-llama-70b",
            ),
            current_user=demo_user,
        )

        # Simulate server restart
        SettingsRepository.load_state(force_reload=True)
        ai_cfg_model_only = get_ai_credentials(current_user=demo_user)
        assert ai_cfg_model_only["has_credential"] is True
        assert ai_cfg_model_only["preferred_model"] == "deepseek-r1-distill-llama-70b"
    finally:
        SettingsRepository.set_store_path(original_path)


def test_voice_command_regression_matrix():
    from api.agent.reranker import fuzzy_similarity

    user_id = "test-regression-matrix-user"
    agent = FinanceAgent(user_id)

    # 1. Verify 'gas' is never matched as substring inside 'gaste' or 'gasto'
    assert fuzzy_similarity("gaste", "gas") < 0.65
    assert fuzzy_similarity("gasto", "gas") < 0.65

    # 2. Everyday 'Pagué <amount> en <motivo>' must trigger ledger adjustment, NOT invoice selector
    r_almuerzo = agent.process_voice_command("Pagué 30000 de almuerzo con Nequi")
    assert r_almuerzo["type"] == "stage_action"
    assert r_almuerzo["staged_action"]["tool_name"] == "propose_ledger_adjustment"
    assert r_almuerzo["staged_action"]["target_item"]["name"] == "Nequi"
    assert r_almuerzo["staged_action"]["target_item"]["delta"] == -30000.0

    r_taxi = agent.process_voice_command("Pagué 50000 en taxi desde mi bolsillo")
    assert r_taxi["type"] == "stage_action"
    assert r_taxi["staged_action"]["tool_name"] == "propose_ledger_adjustment"
    assert r_taxi["staged_action"]["target_item"]["name"] == "Bolsillo"
    assert r_taxi["staged_action"]["target_item"]["delta"] == -50000.0
    assert r_taxi["staged_action"]["target_item"]["note"] == "Taxi"

    # 3. 'Pagué el servicio de gas' must match 'Gas 15', NOT 'Servicio 30'
    r_serv_gas = agent.process_voice_command("Pagué el servicio de gas")
    assert r_serv_gas["type"] == "stage_action"
    assert r_serv_gas["staged_action"]["tool_name"] == "propose_toggle_pending_status"
    assert r_serv_gas["staged_action"]["target_item"]["name"] == "Gas 15"

    # 4. 'Pagué el servicio de agua con Daviplata' must match 'Agua 25' + 'Daviplata', NOT 'Servicio 30'
    r_serv_agua = agent.process_voice_command("Pagué el servicio de agua con Daviplata")
    assert r_serv_agua["type"] == "stage_action"
    assert r_serv_agua["staged_action"]["tool_name"] == "propose_pay_expense_from_account"
    assert r_serv_agua["staged_action"]["target_item"]["name"] == "Agua 25"
    assert r_serv_agua["staged_action"]["target_item"]["secondary_item"]["name"] == "Daviplata"

    # 5. 'Le metí 100000 a Nequi' must register +100,000 income in Nequi
    r_meti_nequi = agent.process_voice_command("Le metí 100000 a Nequi")
    assert r_meti_nequi["type"] == "stage_action"
    assert r_meti_nequi["staged_action"]["tool_name"] == "propose_ledger_adjustment"
    assert r_meti_nequi["staged_action"]["target_item"]["name"] == "Nequi"
    assert r_meti_nequi["staged_action"]["target_item"]["delta"] == 100000.0

    # 6. 'Me consignaron 200000 en Daviplata' must register +200,000 income in Daviplata (not rent collection)
    r_consig = agent.process_voice_command("Me consignaron 200000 en Daviplata")
    assert r_consig["type"] == "stage_action"
    assert r_consig["staged_action"]["tool_name"] == "propose_ledger_adjustment"
    assert r_consig["staged_action"]["target_item"]["name"] == "Daviplata"
    assert r_consig["staged_action"]["target_item"]["delta"] == 200000.0

    # 7. 'Gasté 20000 en efectivo por almuerzo' must register -20,000 in Bolsillo with note 'Almuerzo'
    r_efectivo = agent.process_voice_command("Gasté 20000 en efectivo por almuerzo")
    assert r_efectivo["type"] == "stage_action"
    assert r_efectivo["staged_action"]["tool_name"] == "propose_ledger_adjustment"
    assert r_efectivo["staged_action"]["target_item"]["name"] == "Bolsillo"
    assert r_efectivo["staged_action"]["target_item"]["delta"] == -20000.0
    assert r_efectivo["staged_action"]["target_item"]["note"] == "Almuerzo"

def test_use_case_11_reranker_active_and_account_updates_transfers():
    user_id = "test-case-11-user"
    agent = FinanceAgent(user_id)

    # 1. 'Actualiza banco caja social a $300000' -> propose_set_account_balance on Caja social
    r1 = agent.process_voice_command("Actualiza banco caja social a $300000")
    assert r1["type"] == "stage_action"
    staged1 = r1["staged_action"]
    assert staged1["tool_name"] == "propose_set_account_balance"
    assert staged1["target_item"]["name"] == "Caja social"
    assert staged1["target_item"]["after_value"] == 300000.0
    assert "SET_BALANCE" in r1["prompt_enhancement"]["intent_hints"]
    assert r1["rerank_score"] >= 0.80

    # 2. 'Modifica mi bolsillo a $150.000' -> propose_set_account_balance on Bolsillo
    r2 = agent.process_voice_command("Modifica mi bolsillo a $150.000")
    assert r2["type"] == "stage_action"
    staged2 = r2["staged_action"]
    assert staged2["tool_name"] == "propose_set_account_balance"
    assert staged2["target_item"]["name"] == "Bolsillo"
    assert staged2["target_item"]["after_value"] == 150000.0

    # 3. 'Pon Nequi en 250000' -> propose_set_account_balance on Nequi
    r3 = agent.process_voice_command("Pon Nequi en 250000")
    assert r3["type"] == "stage_action"
    staged3 = r3["staged_action"]
    assert staged3["tool_name"] == "propose_set_account_balance"
    assert staged3["target_item"]["name"] == "Nequi"
    assert staged3["target_item"]["after_value"] == 250000.0

    # 4. 'Mueve desde caja social 100000 a bolsillo' -> propose_transfer_between_accounts
    r4 = agent.process_voice_command("Mueve desde caja social 100000 a bolsillo")
    assert r4["type"] == "stage_action"
    staged4 = r4["staged_action"]
    assert staged4["tool_name"] == "propose_transfer_between_accounts"
    assert staged4["target_item"]["name"] == "Caja social"
    assert staged4["target_item"]["delta"] == -100000.0
    assert staged4["target_item"]["secondary_item"]["name"] == "Bolsillo"
    assert staged4["target_item"]["secondary_item"]["delta"] == 100000.0
    assert "TRANSFER" in r4["prompt_enhancement"]["intent_hints"]
    assert r4["rerank_score"] >= 0.85

    # 5. 'Mueve 100000 a bolsillo desde caja social' (destination first) -> propose_transfer_between_accounts
    r5 = agent.process_voice_command("Mueve 100000 a bolsillo desde caja social")
    assert r5["type"] == "stage_action"
    staged5 = r5["staged_action"]
    assert staged5["tool_name"] == "propose_transfer_between_accounts"
    assert staged5["target_item"]["name"] == "Caja social"
    assert staged5["target_item"]["delta"] == -100000.0
    assert staged5["target_item"]["secondary_item"]["name"] == "Bolsillo"
    assert staged5["target_item"]["secondary_item"]["delta"] == 100000.0

    # 6. 'Transfiere de Nequi $50.000 a Daviplata' -> propose_transfer_between_accounts
    r6 = agent.process_voice_command("Transfiere de Nequi $50.000 a Daviplata")
    assert r6["type"] == "stage_action"
    staged6 = r6["staged_action"]
    assert staged6["tool_name"] == "propose_transfer_between_accounts"
    assert staged6["target_item"]["name"] == "Nequi"
    assert staged6["target_item"]["delta"] == -50000.0
    assert staged6["target_item"]["secondary_item"]["name"] == "Daviplata"
    assert staged6["target_item"]["secondary_item"]["delta"] == 50000.0






