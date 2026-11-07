from typing import Dict, Any, List
import uuid

def generate_seed_data(user_id: str) -> Dict[str, Any]:
    """
    Returns the exact initial dataset and micro-ledger adjustments from EXCEL_SPEC.md (Gastos Albeiro.xlsx).
    """
    # 1. Liquid Accounts (Block A)
    liquid_accounts = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Daviplata",
            "base_amount": 0.0,
            "factor": 1.0,
            "is_active": True,
            "display_order": 1,
            "adjustments": [
                {"amount": 12600.0, "note": "Saldo inicial base"},
                {"amount": 430000.0, "note": "Transferencia recibida"},
                {"amount": -200000.0, "note": "Retiro cajero"},
                {"amount": -34850.0, "note": "Pago factura"},
                {"amount": -44697.0, "note": "Compras"},
                {"amount": -131660.0, "note": "Pago tarjeta"},
                {"amount": -24900.0, "note": "Domicilio"},
                {"amount": -3600.0, "note": "Comisión"},
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Caja social",
            "base_amount": 0.0,
            "factor": 1.0,
            "is_active": True,
            "display_order": 2,
            "adjustments": [
                {"amount": 73085.0, "note": "Saldo previo"},
                {"amount": -49980.0, "note": "Cuota manejo"},
                {"amount": 1050543.0, "note": "Ingreso nómina/remanente"},
                {"amount": 2000000.0, "note": "Préstamo/Abono"},
                {"amount": -1900000.0, "note": "Transferencia inversión"},
                {"amount": -64000.0, "note": "Pago recibo"},
                {"amount": -100000.0, "note": "Retiro efectivo"},
                {"amount": -21700.0, "note": "Gasto vario"},
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Bolsillo",
            "base_amount": 205000.0,
            "factor": 1.0,
            "is_active": True,
            "display_order": 3,
            "adjustments": []
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Colchon",
            "base_amount": 100000.0,
            "factor": 0.0,
            "is_active": False,
            "display_order": 4,
            "adjustments": []
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Nequi",
            "base_amount": 100675.0,
            "factor": 1.0,
            "display_order": 5,
            "is_active": True,
            "adjustments": []
        }
    ]

    # 2. Investment Assets (Block C)
    investment_assets = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Cesantías",
            "asset_type": "cesantias",
            "base_amount": 0.0,
            "units": 0.0,
            "exchange_rate": 1.0,
            "annual_yield_rate": 0.0,
            "is_active": False,
            "display_order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Crypto",
            "asset_type": "crypto",
            "base_amount": 0.0,
            "units": 200.0,
            "exchange_rate": 3400.0,
            "annual_yield_rate": 0.0,
            "is_active": True,
            "display_order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Fiducia (Capital)",
            "asset_type": "fiducia",
            "base_amount": 32560000.0,
            "units": 1.0,
            "exchange_rate": 1.0,
            "annual_yield_rate": 0.07,
            "is_active": True,
            "display_order": 3
        }
    ]

    # 3. Monthly Extras (Block F)
    monthly_extras = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Matrimonio",
            "base_amount": 0.0,
            "factor": 1.0,
            "is_active": False,
            "display_order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Freelance",
            "base_amount": 1100000.0,
            "factor": 0.89, # 1100000 * 0.89 = 979,000 COP
            "is_active": True,
            "display_order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Comfamiliar",
            "base_amount": 1725000.0,
            "factor": 0.45,
            "is_active": False,
            "display_order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Indemnización",
            "base_amount": 17717000.0,
            "factor": 0.25,
            "is_active": False,
            "display_order": 4
        }
    ]

    # 4. Receivables (Block B)
    receivables = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Fiducia",
            "linked_source": "Fiducia Capital",
            "due_day": 30,
            "base_amount": 189933.33333333334,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "fiducia_yield",
            "display_order": 1,
            "adjustments": []
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Ana 26",
            "linked_source": "Casa 3p",
            "due_day": 26,
            "base_amount": 700000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "standard",
            "display_order": 2,
            "adjustments": []
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Marisol 23",
            "linked_source": "Casa 2p",
            "due_day": 23,
            "base_amount": 950000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "standard",
            "display_order": 3,
            "adjustments": [
                {"amount": -15000.0, "note": "Descuento mantenimiento"},
                {"amount": -30700.0, "note": "Deducción servicios"}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Camila 20",
            "linked_source": "Apto 01",
            "due_day": 20,
            "base_amount": 500000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "standard",
            "display_order": 4,
            "adjustments": [
                {"amount": 38000.0, "note": "Ajuste acueducto"},
                {"amount": 22700.0, "note": "Ajuste energía"},
                {"amount": 32000.0, "note": "Gas"},
                {"amount": 3600.0, "note": "Aseo"},
                {"amount": -3000.0, "note": "Retención"},
                {"amount": 24684.0, "note": "Otros cobros"},
                {"amount": -90000.0, "note": "Descuento acordado"}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Angelica 1",
            "linked_source": "Apto 03",
            "due_day": 1,
            "base_amount": 500000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "standard",
            "display_order": 5,
            "adjustments": []
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Odeth 28",
            "linked_source": "Apto 02",
            "due_day": 28,
            "base_amount": 340000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "standard",
            "display_order": 6,
            "adjustments": [
                {"amount": 100000.0, "note": "Abono anterior"},
                {"amount": -140000.0, "note": "Deducción arreglos"}
            ]
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Pagos Extras",
            "linked_source": "Extras mes",
            "due_day": 30,
            "base_amount": 979000.0,
            "factor": 1.0,
            "is_active": True,
            "is_pending": True,
            "formula_type": "sum_extras",
            "display_order": 7,
            "adjustments": []
        }
    ]

    # 5. Income Sources (Block D)
    income_sources = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Sueldo",
            "base_amount": 29000000.0,
            "factor": 0.91,
            "is_active": False,
            "formula_type": "standard",
            "display_order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Fiducia",
            "base_amount": 189933.33333333334,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "fiducia_yield",
            "display_order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Apto 01",
            "base_amount": 500000.0,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "standard",
            "display_order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Apto 02",
            "base_amount": 340000.0,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "standard",
            "display_order": 4
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Apto 03",
            "base_amount": 500000.0,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "standard",
            "display_order": 5
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Casa AL",
            "base_amount": 1000000.0,
            "factor": 0.0,
            "is_active": False,
            "formula_type": "standard",
            "display_order": 6
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Casa 2p",
            "base_amount": 950000.0,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "standard",
            "display_order": 7
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Casa 3p",
            "base_amount": 700000.0,
            "factor": 1.0,
            "is_active": True,
            "formula_type": "standard",
            "display_order": 8
        }
    ]

    # 6. Recurring Expenses (Block E)
    recurring_expenses = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Merc Aseo 1",
            "due_days": "1",
            "recurrent_base": 925000.0, # 14000*30+300000+120000+70000+15000
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0,
            "pending_factor": 1.0,
            "is_pending": False,
            "display_order": 1
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Movistar 1-26",
            "due_days": "1, 26",
            "recurrent_base": 60000.0, # 35000+25000
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 25000.0,
            "pending_factor": 1.0,
            "is_pending": True,
            "display_order": 2
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Internet 25",
            "due_days": "25",
            "recurrent_base": 15000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0,
            "pending_factor": 1.0,
            "is_pending": False,
            "display_order": 3
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Gas 15",
            "due_days": "15",
            "recurrent_base": 10000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 10000.0,
            "pending_factor": 1.0,
            "is_pending": True,
            "display_order": 4
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Energía 20",
            "due_days": "20",
            "recurrent_base": 180000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 180000.0,
            "pending_factor": 1.0,
            "is_pending": True,
            "display_order": 5
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Agua 25",
            "due_days": "25",
            "recurrent_base": 35000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0,
            "pending_factor": 1.0,
            "is_pending": False,
            "display_order": 6
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Mamá 1",
            "due_days": "1",
            "recurrent_base": 750000.0, # 500000+250000
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0,
            "pending_factor": 1.0,
            "is_pending": False,
            "display_order": 7
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Papá 1-15",
            "due_days": "1, 15",
            "recurrent_base": 260000.0, # 130000*2
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 130000.0, # 130000*1
            "pending_factor": 1.0,
            "is_pending": True,
            "display_order": 8
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Planilla 1",
            "due_days": "1",
            "recurrent_base": 508000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0, # 508000*0
            "pending_factor": 0.0,
            "is_pending": False,
            "display_order": 9
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Servicio 30",
            "due_days": "30",
            "recurrent_base": 140000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0, # 100000*0
            "pending_factor": 0.0,
            "is_pending": False,
            "display_order": 10
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Moto",
            "due_days": "",
            "recurrent_base": 40000.0, # 10000*4
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0, # 10000*0
            "pending_factor": 0.0,
            "is_pending": False,
            "display_order": 11
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": "Hija",
            "due_days": "",
            "recurrent_base": 130000.0,
            "recurrent_factor": 1.0,
            "recurrent_is_active": True,
            "pending_base": 0.0,
            "pending_factor": 1.0,
            "is_pending": False,
            "display_order": 12
        }
    ]

    # 7. Financial Goals (Block G)
    financial_goals = [
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "English", "target_amount": 5000000.0, "allocated_amount": 1200000.0, "priority": 1, "status": "active", "display_order": 1},
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "Maestría", "target_amount": 25000000.0, "allocated_amount": 3500000.0, "priority": 2, "status": "active", "display_order": 2},
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "Visa", "target_amount": 2000000.0, "allocated_amount": 800000.0, "priority": 3, "status": "active", "display_order": 3},
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "Casa brisas", "target_amount": 50000000.0, "allocated_amount": 5000000.0, "priority": 4, "status": "active", "display_order": 4},
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "Matrimonio", "target_amount": 15000000.0, "allocated_amount": 2000000.0, "priority": 5, "status": "active", "display_order": 5},
        {"id": str(uuid.uuid4()), "user_id": user_id, "name": "Ortodoncia", "target_amount": 4000000.0, "allocated_amount": 1500000.0, "priority": 6, "status": "active", "display_order": 6}
    ]

    return {
        "liquid_accounts": liquid_accounts,
        "investment_assets": investment_assets,
        "monthly_extras": monthly_extras,
        "receivables": receivables,
        "income_sources": income_sources,
        "recurring_expenses": recurring_expenses,
        "financial_goals": financial_goals
    }
