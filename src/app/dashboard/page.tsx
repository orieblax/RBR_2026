'use client';

import React, { useState } from 'react';
import { Navbar } from '@/components/Navbar';
import { KPICards } from '@/components/KPICards';
import { CashFlowCards } from '@/components/CashFlowCards';
import { LedgerDrawer } from '@/components/LedgerDrawer';
import { VoiceCommandBar } from '@/components/VoiceCommandBar';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { useFinanceSummary } from '@/hooks/useFinanceSummary';

export default function DashboardPage() {
  const {
    summary,
    isLoading,
    isError,
    togglePendingExpense,
    addAdjustment,
    removeAdjustment,
    mutate,
  } = useFinanceSummary();

  const [activeLedgerItem, setActiveLedgerItem] = useState<any>(null);
  const [stagedAction, setStagedAction] = useState<any>(null);

  const handleOpenLedger = (item: any, type: 'liquid_account' | 'receivable') => {
    setActiveLedgerItem({
      ...item,
      parent_type: type,
    });
  };

  const handleCloseLedger = () => {
    setActiveLedgerItem(null);
  };

  if (isLoading) {
    return (
      <div className="min-vh-100 d-flex flex-column">
        <Navbar />
        <div className="flex-grow-1 d-flex align-items-center justify-content-center">
          <div className="text-center">
            <div className="spinner-border text-primary mb-3" role="status"></div>
            <p className="text-muted fw-semibold">Calculando paridad financiera Excel 2026...</p>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !summary) {
    return (
      <div className="min-vh-100 d-flex flex-column">
        <Navbar />
        <div className="container py-5 text-center">
          <div className="alert alert-danger p-4 rounded-4 shadow-sm" role="alert">
            <h5 className="alert-heading fw-bold">Error de conexión</h5>
            <p className="mb-0">No fue posible cargar el resumen financiero. Verifica el servidor backend.</p>
            <button onClick={() => mutate()} className="btn btn-outline-danger mt-3">
              Reintentar
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 d-flex flex-column pb-5 mb-5">
      <Navbar />

      <main className="container py-4 flex-grow-1">
        <div className="d-flex flex-wrap justify-content-between align-items-center mb-4 gap-2">
          <div>
            <h2 className="fw-bold text-dark mb-0">Panel Financiero RBR 2026</h2>
            <p className="text-muted small mb-0">
              Control de liquidez, cuentas por cobrar y cálculo de excedente disponible para inversión
            </p>
          </div>
          <div className="d-flex align-items-center gap-2">
            <button
              onClick={() => mutate()}
              className="btn btn-white bg-white border shadow-sm btn-sm px-3 py-2 rounded-pill fw-semibold"
              title="Recalcular"
            >
              <i className="bi bi-arrow-clockwise me-1 text-primary"></i>
              Actualizar
            </button>
          </div>
        </div>

        {/* Top KPI Banner */}
        <KPICards kpis={summary.kpis} />

        {/* Interactive Cash Flow Blocks */}
        <CashFlowCards
          summary={summary}
          onOpenLedger={handleOpenLedger}
          onToggleExpensePaid={async (name, isPaid) => {
            await togglePendingExpense(name, isPaid);
          }}
        />

        {/* Micro-Ledger Drawer Modal */}
        <LedgerDrawer
          item={activeLedgerItem}
          onClose={handleCloseLedger}
          onAddAdjustment={async (parentType, targetName, amount, note) => {
            await addAdjustment(parentType, targetName, amount, note);
            mutate();
          }}
          onRemoveAdjustment={async (id) => {
            await removeAdjustment(id);
            mutate();
          }}
        />

        {/* Voice Command Bar & Safety Confirmation */}
        <VoiceCommandBar
          onStageAction={(action) => setStagedAction(action)}
          onRefreshData={() => mutate()}
        />

        <ConfirmationModal
          stagedAction={stagedAction}
          onClose={() => setStagedAction(null)}
          onConfirmed={() => {
            setStagedAction(null);
            mutate();
          }}
        />
      </main>
    </div>
  );
}
