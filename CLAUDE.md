# CLAUDE.md - RBR Finance Manager Architecture & Rules

## 1. Project Overview
RBR Finance Manager is a Spanish-first (`es-CO`), voice-controlled personal finance and investment surplus SaaS web application (PWA + Android TWA ready) built on a Vercel Hybrid Monorepo:
- **Frontend:** Next.js (App Router, TypeScript, Bootstrap 5 CSS, SWR/TanStack Query)
- **Backend:** Python FastAPI (`/api` serverless functions) + Agno AI Agent Framework
- **Database & Auth:** Single-tenant-per-row SaaS on Supabase (PostgreSQL + Supabase Auth + Row-Level Security + `pgvector`)

## 2. Directory Structure (Modular Monolith)
- `/src/app/` -> Next.js pages (`(auth)/login`, `(auth)/register`, `dashboard`, `settings/ai`, `admin`)
- `/src/components/` -> Bootstrap 5 UI components (`VoiceCommandBar`, `ConfirmationModal`, `CashFlowCards`, `LedgerDrawer`)
- `/src/hooks/` -> `useVoiceRecognition.ts` (`es-CO` Chrome SpeechRecognition), `useFinanceSummary.ts`
- `/api/index.py` -> FastAPI entrypoint mounted at `/api/py/*`
- `/api/core/` -> `config.py`, `security.py` (AES-256-GCM / Fernet vault, JWT validation, RBAC)
- `/api/domain/` -> Pure Python dataclasses/models & exact financial formulas from `EXCEL_SPEC.md`
- `/api/repositories/` -> Repository Pattern encapsulating all Supabase queries
- `/api/commands/` -> CQRS Write Command Services (Create/Update/Delete with Pydantic validation)
- `/api/queries/` -> CQRS Read Query Services (Monthly/Yearly Investable Surplus, Category Breakdowns)
- `/api/agent/` -> Agno Agent setup, `llm_factory.py` (supports `claude setup-token` `sk-ant-oat01-*` and API keys), and Agno Tools

## 3. Strict Engineering & Security Rules
1. **Pragmatic CQRS & SOLID:** Do NOT create over-engineered mediator buses. Keep `CommandService` classes for state mutations and `QueryService` classes for dashboard aggregations. Both REST endpoints and Agno Agent tools MUST call the exact same Command/Query services.
2. **Two-Step Voice Mutation Safety:** Agno tools that mutate data (add/edit/delete) via voice MUST NOT write directly to the DB on the first turn. They must return a `PendingVoiceAction` payload (showing current value, proposed value, and delta on `Restante` and `Incl Pend`). Writing only happens when the user confirms via `/api/py/voice/confirm`.
3. **Claude Setup-Token Support:** Users store encrypted AI credentials in `user_ai_credentials`. When decrypting in memory:
   - Prefix `sk-ant-oat` -> Pass as `auth_token` (Bearer) with header `{"anthropic-beta": "oauth-2025-04-20"}` to Anthropic/Agno.
   - Prefix `sk-ant-api` -> Pass as standard `api_key`.
   - Never log or return raw tokens to the frontend after saving (return masked `sk-ant-...****`).
4. **Vercel Bundle Limit (<250MB):** NEVER install `torch`, `transformers`, or `sentence-transformers`. Use lightweight dependencies (`fastapi`, `agno`, `anthropic`, `openai`, `supabase`, `cryptography`, `pydantic`).
5. **Security Guardrails:** Every FastAPI route and Agno tool execution must extract `user_id` from the verified Supabase Bearer JWT—never trust `user_id` passed by the LLM or client body.