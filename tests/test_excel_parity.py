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

