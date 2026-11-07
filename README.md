# RBR Finance Manager

> **Spanish-first (`es-CO`), voice-controlled personal finance & investment surplus SaaS web application.**  
> Built as a **Vercel Hybrid Monorepo**: **Next.js 14** (App Router, TypeScript, Bootstrap 5) + **Python FastAPI** serverless backend, with **Supabase PostgreSQL** (Row-Level Security, Auth & `pgvector`).

---

## 🚀 Key Features

- **100% Exact Financial Math Parity:** Replicates cell-level logic and inline micro-ledger arithmetic (`+12600 +430000 -200000...`), retention factors (`*0.91`, `*0.89`), and active/pending status flags (`*1` active, `*0` paid/inactive).
- **Core KPI Engine:**
  - **`Incl Pend` (Primary Monthly Investable Surplus):** `Restante + Total Pendientes - Total Gastos Recurrentes`.
  - **`Restante` (Net Liquidity):** `Total Actual - Gastos Mes Pendientes`.
  - **`Ahorro` (Base Monthly Operating Flow):** `Ingresos Recurrentes - Total Gastos Recurrentes`.
  - **`Proyección Anual Invertible`:** Projected annual surplus including monthly savings and fiduciary asset yield.
- **Micro-Ledger Inline Drawer:** Interactive modal to review every historical adjustment on liquid accounts and receivables, with instant addition and removal of line items.
- **Two-Step Voice Mutation Safety:** Speech-to-text voice commands in Colombian Spanish (`es-CO` via Web Speech API). Mutating commands (e.g. *"Marcar pagado Energía 20"*, *"Agregar gasto en Daviplata de 50000"*) stage an action preview calculating the exact COP impact on `Restante` and `Incl Pend` before execution.
- **AES-256 / Fernet AI Encryption Vault:** Stores user AI credentials encrypted at rest. Native support for `claude setup-token` (`sk-ant-oat01-*`) with OAuth beta headers, standard Anthropic API keys (`sk-ant-api03-*`), OpenAI (`sk-*`), and Groq (`gsk_*`), with an in-memory 5-token ping test.
- **Admin Console & Diagnostics (RBAC):** Admin-protected view for user management, role and status toggling, system diagnostics, and default AI model assignment.
- **PWA & Android TWA Ready:** Offline service worker, web app manifest, Digital Asset Links (`/.well-known/assetlinks.json`), and Bubblewrap CLI configuration with microphone permission delegation (`RECORD_AUDIO`).

---

## 🏗️ Architecture & Directory Structure

```text
├── .well-known/              # Digital Asset Links for Android TWA verification
├── api/                      # FastAPI Python Serverless Backend
│   ├── agent/                # Agno Voice Agent & LLM Factory (OAuth setup-token & API keys)
│   ├── commands/             # CQRS Write Command Services (mutations & impact deltas)
│   ├── core/                 # Config, AES-256 Fernet Vault, JWT auth middleware, Rate Limiter
│   ├── domain/               # Domain models & pure Python FinancialCalculator (Excel math)
│   ├── queries/              # CQRS Read Query Services (aggregations & breakdowns)
│   ├── repositories/         # FinanceRepository encapsulating persistence with offline store
│   ├── index.py              # FastAPI entrypoint mounted at /api/py/*
│   └── requirements.txt      # Lightweight serverless dependencies (<250MB Vercel limit)
├── public/                   # Static assets, PWA icons, manifest.json, sw.js
├── src/                      # Next.js 14 App Router Frontend
│   ├── app/                  # Pages: (auth)/login, (auth)/register, dashboard, settings/ai, admin
│   ├── components/           # Bootstrap 5 UI: KPICards, CashFlowCards, LedgerDrawer, VoiceCommandBar
│   ├── hooks/                # useFinanceSummary (SWR), useVoiceRecognition (es-CO SpeechRecognition)
│   └── lib/                  # Supabase client helpers
├── supabase/
│   └── migrations/           # Multi-tenant schema with strict Row-Level Security (RLS)
├── tests/                    # Pytest suite verifying exact mathematical parity & security
├── twa/                      # Trusted Web Activity (TWA) Bubblewrap manifest and build scripts
├── next.config.mjs           # Next.js config with security headers and API rewrites
├── vercel.json               # Vercel serverless routing (/api/py/(.*) -> /api/index.py)
└── package.json              # Frontend dependencies and scripts
```

---

## ⚙️ Prerequisites

- **Node.js:** v18.x or v20.x+
- **Python:** 3.10, 3.11, or 3.12
- **npm** or **pnpm** / **yarn**

---

## 🛠️ Getting Started (Local Development)

### 1. Clone Repository & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/rbr-finance-manager.git
cd rbr-finance-manager

# Install Frontend Dependencies
npm install

# Install Python Backend Dependencies
python -m pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env.local
```

Configure your variables in `.env.local`:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Security & Encryption Vault
# Generate a new Fernet key with:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
MASTER_ENCRYPTION_KEY=Wk93Qkx4Y01XbmFqM19vRkV3c05mRE90TmlhSWl5d0hWZEtNYVhzQ0xYWT0=

# Application Environment
ENV=development
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

> **Note:** The application includes a persistent development fallback store. You can run and test all dashboard features, voice commands, and math engines immediately even before connecting a cloud Supabase project.

### 3. Run the Development Servers

Open two terminal windows:

**Terminal 1 — FastAPI Backend (Port 8000):**
```bash
python -m uvicorn api.index:app --reload --port 8000
```
- Swagger API Docs: [http://127.0.0.1:8000/api/py/docs](http://127.0.0.1:8000/api/py/docs)
- Health Check: [http://127.0.0.1:8000/api/py/health](http://127.0.0.1:8000/api/py/health)

**Terminal 2 — Next.js Frontend (Port 3000):**
```bash
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Running Automated Tests

Run the full pytest suite to verify mathematical parity against the domain specification, CQRS queries/commands, AES-256 token encryption, and voice agent safety:

```bash
python -m pytest tests/test_excel_parity.py -v
```

To run Next.js TypeScript validation and production build:

```bash
npm run build
```

---

## ☁️ Deploying to Vercel (with GitHub CI/CD)

1. Push your repository to GitHub:
   ```bash
   git branch -M main
   git remote add origin https://github.com/your-username/rbr-finance-manager.git
   git push -u origin main
   ```
2. Log in to [Vercel](https://vercel.com) and click **"Add New..."** → **"Project"**.
3. Select your GitHub repository and click **"Import"**.
4. Vercel automatically detects **Next.js** for the frontend and **FastAPI** (`api/index.py`) for the serverless backend.
5. In **"Environment Variables"**, configure:
   - `MASTER_ENCRYPTION_KEY`
   - `ENV=production`
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_JWT_SECRET`
   - `NEXT_PUBLIC_APP_URL`
6. Click **"Deploy"**. Every future `git push` to `main` will trigger automatic continuous deployment.

---

## 📱 Android TWA (Trusted Web Activity) APK

The `/twa` directory includes configuration for building an installable Android APK with microphone permission delegation for voice control:

```bash
# Using Bubblewrap CLI
cd twa
npm install -g @bubblewrap/cli

# Run build script
./build-apk.sh     # Linux / macOS
.\build-apk.ps1    # Windows PowerShell
```

---

## 🛡️ Security & Privacy

- **Zero Token Exposure:** AI API keys and OAuth setup-tokens are encrypted using AES-256-GCM / Fernet before saving and are masked (`sk-ant-...****`) when sent to clients.
- **Strict Row-Level Security:** Supabase tables enforce `auth.uid() = user_id` isolation.
- **User ID Guardrails:** Endpoints extract user identity strictly from verified Bearer JWT tokens, never from request parameters.
- **Rate Limiting:** Built-in sliding-window limiter guards serverless endpoints against abuse.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
