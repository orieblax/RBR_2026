# EXCEL_SPEC.md - RBR Finance Manager Domain Specification (from Gastos Albeiro.xlsx)

## 1. Core Financial Entities & Micro-Ledger Formula Behavior
In the original Excel (`Hoja: 2026`), cells frequently contain inline arithmetic (`=500000*1+38000-90000`) and boolean multipliers (`*1` active/pending, `*0` inactive/paid). The database and domain engine must support:
- **Base Amount (`base_amount`)**
- **Multiplier / Retention Factor (`factor`)**: e.g., `0.91` for Salary net of social security, `0.89` for Freelance net of withholding, or `2` for bi-monthly payments (`Papá 1-15`: `130000 * 2`).
- **Line-Item Adjustments (`adjustments[]`)**: A list of `{ amount: (+/-), note: string, created_at }` attached to any Liquid Account, Receivable, or Expense so users can add/subtract partial movements just like `=12600+430000-200000...` in Excel.
- **Active / Pending Toggle (`is_active`, `is_pending`)**: Replaces `*1` and `*0`.
- **Day of Month (`due_day`)**: Integer `1-31` (or `1, 15` / `1, 26`) extracted from labels like `Ana 26`, `Marisol 23`, `Energía 20`, `Movistar 1-26`.

## 2. The 7 Data Blocks (Initial Seed Data for User)

### Block A: Cuentas de Liquidez Actual (`Estado` B2:B6)
| Name | Base / Inline Ledger | Current Total (COP) |
| :--- | :--- | :---: |
| Daviplata | `+12600 +430000 -200000 -34850 -44697 -131660 -24900 -3600` | $2,893 |
| Caja social | `+73085 -49980 +1050543 +2000000 -1900000 -64000 -100000 -21700` | $987,948 |
| Bolsillo | `205000` | $205,000 |
| Colchon | `100000 * 0` (`is_active = false`) | $0 |
| Nequi | `100675` | $100,675 |
- **Formula `Total actual` (B18):** `SUM(B2:B6)` = **$1,296,516**

### Block B: Cuentas por Cobrar / Pendientes de Ingreso en el Mes (`B8:B14`)
| Name | Linked Source | Due Day | Formula / Adjustments | Current Pending (COP) |
| :--- | :--- | :---: | :--- | :---: |
| Fiducia | Yield from Fiducia Capital | 30 | `=D5 * 1` | $189,933.33 |
| Ana 26 | Casa 3p | 26 | `700000 * 1` | $700,000.00 |
| Marisol 23 | Casa 2p | 23 | `(950000 - 15000 - 30700) * 1` | $904,300.00 |
| Camila 20 | Apto 01 | 20 | `500000 + 38000 + 22700 + 32000 + 3600 - 3000 + 24684 - 90000` | $527,984.00 |
| Angelica 1 | Apto 03 | 1 | `500000 * 1` | $500,000.00 |
| Odeth 28 | Apto 02 | 28 | `340000 + 100000 - 140000` | $300,000.00 |
| Pagos Extras | Sum of Block F (`Extras mes`) | - | `SUM(Extras mes)` | $979,000.00 |
- **Formula `Pend` (B21):** `SUM(B8:B14)` = **$4,101,217.33**

### Block C: Patrimonio e Inversiones Acumuladas (`B15:B17`)
| Asset | Formula / Rule | Current Value (COP) |
| :--- | :--- | :---: |
| Cesantías | `0 + 24000000*0 + 4429444*0` | $0 |
| Crypto | `units (200) * exchange_rate (3400)` | $680,000 |
| Fiducia (Capital) | Capital Base yielding `7% E.A.` (`0.07 / 12` monthly) | $32,560,000 |

### Block D: Ingresos Mensuales Recurrentes (`C4:D11`)
| Source | Formula / Rule | Active | Monthly Amount (COP) |
| :--- | :--- | :---: | :---: |
| Sueldo | `29000000 * 0.91 * 0` | False | $0.00 |
| Fiducia | `Fiducia_Capital * (0.07 / 12) * (days/30)` | True | $189,933.33 |
| Apto 01 | `500000` | True | $500,000.00 |
| Apto 02 | `340000` | True | $340,000.00 |
| Apto 03 | `500000` | True | $500,000.00 |
| Casa AL | `1000000 * 0` | False | $0.00 |
| Casa 2p | `950000` | True | $950,000.00 |
| Casa 3p | `700000 * 1` | True | $700,000.00 |
- **Formula `Ingresos` (D18):** `SUM(D4:D15)` = **$3,179,933.33**

### Block E: Egresos Recurrentes y Pendientes del Mes (`E2:G13`)
| Expense Item | Due Day(s) | Recurrente Formula | Recurrente (COP) | Pendiente Formula | Pendiente (COP) |
| :--- | :---: | :--- | :---: | :--- | :---: |
| Merc Aseo 1 | 1 | `14000*30 + 300000 + 120000 + 70000 + 15000` | $925,000 | `0` | $0 |
| Movistar 1-26 | 1, 26 | `35000 + 25000` | $60,000 | `25000` | $25,000 |
| Internet 25 | 25 | `15000` | $15,000 | `0` | $0 |
| Gas 15 | 15 | `10000` | $10,000 | `10000` | $10,000 |
| Energía 20 | 20 | `180000` | $180,000 | `180000` | $180,000 |
| Agua 25 | 25 | `35000` | $35,000 | `0` | $0 |
| Mamá 1 | 1 | `500000 + 250000` | $750,000 | `0` | $0 |
| Papá 1-15 | 1, 15 | `130000 * 2` | $260,000 | `130000 * 1` | $130,000 |
| Planilla 1 | 1 | `508000 * 1` | $508,000 | `508000 * 0` | $0 |
| Servicio 30 | 30 | `140000 * 1` | $140,000 | `100000 * 0` | $0 |
| Moto | - | `10000 * 4` | $40,000 | `10000 * 0` | $0 |
| Hija | - | `130000` | $130,000 | `0` | $0 |
- **Formula `Total gastos` Recurrentes (F18):** `SUM(F2:F13)` = **$3,053,000**
- **Formula `Gastos mes` Pendientes (G18 / B19):** `SUM(G2:G13)` = **$345,000**

### Block F: Extras del Mes (`C26:D30`)
| Extra Item | Formula | Active | Value (COP) |
| :--- | :--- | :---: | :---: |
| Matrimonio | `0` | False | $0 |
| Freelance | `1100000 * 0.89` | True | $979,000 |
| Comfamiliar | `1725000 * 1.5 * 0.3 * 0` | False | $0 |
| Indemnización | `17717000 * 0.25 * 0` | False | $0 |

### Block G: Metas Financieras (`A26:A32`)
- `English`, `Maestría`, `Visa`, `Casa brisas`, `Matrimonio`, `Ortodoncia` (Track target amount, allocated savings, priority, and progress %).

## 3. Master KPI Formulas (Monthly & Yearly Investment Capacity)
1. **`total_actual`** = `SUM(liquid_accounts.current_balance)` -> **$1,296,516**
2. **`gastos_mes_pendientes`** = `SUM(expenses.pending_amount)` -> **$345,000**
3. **`restante_liquidez`** = `total_actual - gastos_mes_pendientes` -> **$951,516**
4. **`ahorro_mensual_recurrente`** = `total_ingresos_recurrentes - total_gastos_recurrentes` -> `$3,179,933.33 - $3,053,000` = **$126,933.33**
5. **`ahorro_sin_sueldo`** = `ahorro_mensual_recurrente - sueldo` -> **$126,933.33**
6. **`incl_pend_invertible_mes` (Primary Monthly Investable KPI, Cell B22):**
   `restante_liquidez + total_pendientes_por_cobrar - total_gastos_recurrentes`
   = `$951,516 + $4,101,217.33 - $3,053,000` = **$1,999,733.33**
7. **`proyeccion_invertible_anual` (Yearly Investable KPI):**
   `(ahorro_mensual_recurrente * remaining_months) + incl_pend_invertible_mes + proyectado_rendimiento_fiducia`