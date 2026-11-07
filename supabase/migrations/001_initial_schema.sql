-- RBR Finance Manager - Initial Multi-Tenant Schema with Strict RLS and pgvector
-- Migration: 001_initial_schema.sql

-- Enable Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Profiles Table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    default_ai_model TEXT NOT NULL DEFAULT 'claude-3-7-sonnet-latest',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Admin Check Function
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
  SELECT COALESCE(
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()),
    FALSE
  );
$$;

-- 2. Liquid Accounts Table (Block A: Daviplata, Caja social, Bolsillo, Colchón, Nequi)
CREATE TABLE IF NOT EXISTS public.liquid_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    base_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 3. Ledger Adjustments Table (Micro-Ledger movements for accounts, receivables, and expenses)
CREATE TABLE IF NOT EXISTS public.ledger_adjustments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_type TEXT NOT NULL CHECK (parent_type IN ('liquid_account', 'receivable', 'recurring_expense', 'monthly_extra', 'investment_asset')),
    parent_id UUID,
    parent_name TEXT,
    amount NUMERIC(15, 2) NOT NULL,
    factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT NOT NULL DEFAULT '',
    embedding vector(1536),
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 4. Receivables Table (Block B: Fiducia yield, Ana 26, Marisol 23, Camila 20, Angelica 1, Odeth 28, Pagos Extras)
CREATE TABLE IF NOT EXISTS public.receivables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    linked_source TEXT,
    due_day INT DEFAULT 1,
    base_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_pending BOOLEAN NOT NULL DEFAULT TRUE,
    formula_type TEXT DEFAULT 'standard',
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 5. Income Sources Table (Block D: Sueldo, Fiducia, Apto 01, Apto 02, Apto 03, Casa AL, Casa 2p, Casa 3p)
CREATE TABLE IF NOT EXISTS public.income_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    base_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    formula_type TEXT DEFAULT 'standard',
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 6. Recurring Expenses Table (Block E: Merc Aseo 1, Movistar 1-26, Internet 25, Gas 15, Energía 20, Agua 25, Mamá 1, Papá 1-15, Planilla 1, Servicio 30, Moto, Hija)
CREATE TABLE IF NOT EXISTS public.recurring_expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    due_days TEXT DEFAULT '1',
    recurrent_base NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    recurrent_factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    recurrent_is_active BOOLEAN NOT NULL DEFAULT TRUE,
    pending_base NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    pending_factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_pending BOOLEAN NOT NULL DEFAULT FALSE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 7. Monthly Extras Table (Block F: Matrimonio, Freelance, Comfamiliar, Indemnización)
CREATE TABLE IF NOT EXISTS public.monthly_extras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    base_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    factor NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 8. Investment Assets Table (Block C: Cesantías, Crypto, Fiducia Capital)
CREATE TABLE IF NOT EXISTS public.investment_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    base_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    units NUMERIC(15, 6) DEFAULT 0.000000,
    exchange_rate NUMERIC(15, 2) DEFAULT 1.00,
    annual_yield_rate NUMERIC(6, 4) DEFAULT 0.0700,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 9. Financial Goals Table (Block G: English, Maestría, Visa, Casa brisas, Matrimonio, Ortodoncia)
CREATE TABLE IF NOT EXISTS public.financial_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    target_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    allocated_amount NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    priority INT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 10. Monthly Snapshots Table
CREATE TABLE IF NOT EXISTS public.monthly_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    year_month TEXT NOT NULL,
    total_actual NUMERIC(15, 2) NOT NULL,
    gastos_mes NUMERIC(15, 2) NOT NULL,
    restante NUMERIC(15, 2) NOT NULL,
    ingresos NUMERIC(15, 2) NOT NULL,
    total_gastos NUMERIC(15, 2) NOT NULL,
    ahorro NUMERIC(15, 2) NOT NULL,
    pend NUMERIC(15, 2) NOT NULL,
    incl_pend NUMERIC(15, 2) NOT NULL,
    snapshot_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 11. User AI Credentials Table (AES-256-GCM / Fernet Encrypted Vault)
CREATE TABLE IF NOT EXISTS public.user_ai_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL, -- 'anthropic', 'openai', 'groq'
    auth_mode TEXT NOT NULL DEFAULT 'api_key', -- 'oauth_token', 'api_key'
    encrypted_token TEXT NOT NULL,
    masked_token TEXT NOT NULL,
    preferred_model TEXT NOT NULL DEFAULT 'claude-3-7-sonnet-latest',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_tested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    UNIQUE(user_id, provider)
);

-- 12. Pending Voice Actions (2-Step Safety Confirmation Workflow)
CREATE TABLE IF NOT EXISTS public.pending_voice_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    action_payload JSONB NOT NULL,
    preview_summary TEXT NOT NULL,
    impact_delta JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'confirmed', 'cancelled', 'expired'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 13. Audit Logs Table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    before_state JSONB,
    after_state JSONB,
    source TEXT NOT NULL DEFAULT 'web', -- 'web', 'voice', 'system'
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Enable Row Level Security on ALL tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.liquid_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_adjustments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.receivables ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.income_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recurring_expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monthly_extras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.investment_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financial_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monthly_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_ai_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pending_voice_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Strict RLS Policies (auth.uid() = user_id)

-- Profiles: user can read/update own profile; admins can read all
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id OR public.is_admin());
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id OR public.is_admin());
CREATE POLICY "Users can insert own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = id);

-- Liquid Accounts
CREATE POLICY "Liquid Accounts Isolation" ON public.liquid_accounts FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Ledger Adjustments
CREATE POLICY "Ledger Adjustments Isolation" ON public.ledger_adjustments FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Receivables
CREATE POLICY "Receivables Isolation" ON public.receivables FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Income Sources
CREATE POLICY "Income Sources Isolation" ON public.income_sources FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Recurring Expenses
CREATE POLICY "Recurring Expenses Isolation" ON public.recurring_expenses FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Monthly Extras
CREATE POLICY "Monthly Extras Isolation" ON public.monthly_extras FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Investment Assets
CREATE POLICY "Investment Assets Isolation" ON public.investment_assets FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Financial Goals
CREATE POLICY "Financial Goals Isolation" ON public.financial_goals FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Monthly Snapshots
CREATE POLICY "Monthly Snapshots Isolation" ON public.monthly_snapshots FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- User AI Credentials
CREATE POLICY "User AI Credentials Isolation" ON public.user_ai_credentials FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Pending Voice Actions
CREATE POLICY "Pending Voice Actions Isolation" ON public.pending_voice_actions FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Audit Logs
CREATE POLICY "Audit Logs User Isolation" ON public.audit_logs FOR SELECT USING (auth.uid() = user_id OR public.is_admin());
CREATE POLICY "Audit Logs User Insert" ON public.audit_logs FOR INSERT WITH CHECK (auth.uid() = user_id);
