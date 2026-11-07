'use client';

import React from 'react';
import { formatCOP } from './KPICards';

interface CashFlowCardsProps {
  summary: any;
  onOpenLedger: (item: any, type: 'liquid_account' | 'receivable') => void;
  onToggleExpensePaid: (name: string, isPaid: boolean) => void;
}

export function CashFlowCards({
  summary,
  onOpenLedger,
  onToggleExpensePaid,
}: CashFlowCardsProps) {
  if (!summary) return null;

  return (
    <div className="row g-4">
      {/* 1. Liquidez Actual (Block A) */}
      <div className="col-12 col-lg-6">
        <div className="card shadow-sm border-0 rounded-4 p-4 h-100 bg-white">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0 text-dark">
              <i className="bi bi-wallet2 text-primary me-2"></i>
              Liquidez Actual
            </h5>
            <span className="badge bg-primary rounded-pill px-3 py-2 fw-bold">
              Total: {formatCOP(summary.kpis.total_actual)}
            </span>
          </div>
          <p className="text-muted small mb-3">
            Saldos disponibles en cuentas bancarias, billeteras digitales y efectivo.
          </p>

          <div className="list-group list-group-flush">
            {summary.liquid_accounts.map((acc: any) => (
              <div
                key={acc.name}
                className="list-group-item d-flex justify-content-between align-items-center px-0 py-3 border-light"
              >
                <div>
                  <div className="fw-semibold text-dark d-flex align-items-center gap-2">
                    {acc.name}
                    {!acc.is_active && (
                      <span className="badge bg-secondary-subtle text-secondary small">Inactivo (*0)</span>
                    )}
                  </div>
                  {acc.adjustments && acc.adjustments.length > 0 && (
                    <small className="text-muted">
                      {acc.adjustments.length} ajustes inline
                    </small>
                  )}
                </div>

                <div className="d-flex align-items-center gap-3">
                  <span className="fw-bold text-dark fs-6">
                    {formatCOP(acc.calculated_total)}
                  </span>
                  <button
                    onClick={() => onOpenLedger(acc, 'liquid_account')}
                    className="btn btn-outline-primary btn-sm rounded-pill px-2 py-1"
                    title="Ver ajustes inline"
                  >
                    <i className="bi bi-journal-text me-1"></i>
                    Ajustes
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Cuentas Por Cobrar / Pendientes Mes (Block B) */}
      <div className="col-12 col-lg-6">
        <div className="card shadow-sm border-0 rounded-4 p-4 h-100 bg-white">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0 text-dark">
              <i className="bi bi-clock-history text-info me-2"></i>
              Por Cobrar (Pend)
            </h5>
            <span className="badge bg-info text-dark rounded-pill px-3 py-2 fw-bold">
              Total: {formatCOP(summary.kpis.pend)}
            </span>
          </div>
          <p className="text-muted small mb-3">
            Arriendos, rendimientos y cobros pendientes del mes con fecha límite.
          </p>

          <div className="list-group list-group-flush">
            {summary.receivables.map((rec: any) => (
              <div
                key={rec.name}
                className="list-group-item d-flex justify-content-between align-items-center px-0 py-3 border-light"
              >
                <div>
                  <div className="fw-semibold text-dark d-flex align-items-center gap-2">
                    {rec.name}
                    {rec.due_day && (
                      <span className="badge bg-info-subtle text-info-emphasis rounded-pill small">
                        Día {rec.due_day}
                      </span>
                    )}
                  </div>
                  {rec.linked_source && (
                    <small className="text-muted">Origen: {rec.linked_source}</small>
                  )}
                </div>

                <div className="d-flex align-items-center gap-3">
                  <span className="fw-bold text-dark fs-6">
                    {formatCOP(rec.calculated_pending)}
                  </span>
                  {rec.adjustments && rec.adjustments.length > 0 && (
                    <button
                      onClick={() => onOpenLedger(rec, 'receivable')}
                      className="btn btn-outline-info btn-sm rounded-pill px-2 py-1 text-dark"
                      title="Ver ajustes"
                    >
                      <i className="bi bi-journal-text me-1"></i>
                      Ajustes
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Egresos del Mes (Block E: Recurrentes vs Pendientes con 1-click Marcar Pagado) */}
      <div className="col-12">
        <div className="card shadow-sm border-0 rounded-4 p-4 bg-white">
          <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 gap-2">
            <div>
              <h5 className="fw-bold mb-1 text-dark">
                <i className="bi bi-receipt-cutoff text-danger me-2"></i>
                Egresos del Mes: Recurrente vs Pendiente
              </h5>
              <p className="text-muted small mb-0">
                Total Recurrente: <strong>{formatCOP(summary.kpis.total_gastos)}</strong> | Pendiente por Pagar: <strong className="text-danger">{formatCOP(summary.kpis.gastos_mes)}</strong>
              </p>
            </div>
            <span className="badge bg-danger-subtle text-danger px-3 py-2 rounded-pill fw-semibold">
              {summary.recurring_expenses.filter((e: any) => !e.is_paid).length} Pendientes
            </span>
          </div>

          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Concepto / Gasto</th>
                  <th>Día(s) Pago</th>
                  <th className="text-end">Recurrente (COP)</th>
                  <th className="text-end">Pendiente (COP)</th>
                  <th className="text-center">Estado / Acción</th>
                </tr>
              </thead>
              <tbody>
                {summary.recurring_expenses.map((exp: any) => (
                  <tr key={exp.name}>
                    <td className="fw-semibold text-dark">{exp.name}</td>
                    <td>
                      {exp.due_days ? (
                        <span className="badge bg-light text-dark border">
                          Día {exp.due_days}
                        </span>
                      ) : (
                        <span className="text-muted small">—</span>
                      )}
                    </td>
                    <td className="text-end text-muted">
                      {formatCOP(exp.calculated_recurrent)}
                    </td>
                    <td className="text-end fw-bold">
                      {exp.calculated_pending > 0 ? (
                        <span className="text-danger">{formatCOP(exp.calculated_pending)}</span>
                      ) : (
                        <span className="text-muted">$0</span>
                      )}
                    </td>
                    <td className="text-center">
                      {exp.is_paid ? (
                        <span className="badge bg-success-subtle text-success px-3 py-2 rounded-pill">
                          <i className="bi bi-check2-circle me-1"></i> Pagado
                        </span>
                      ) : (
                        <button
                          onClick={() => onToggleExpensePaid(exp.name, true)}
                          className="btn btn-sm btn-outline-danger rounded-pill px-3"
                          title="Hacer clic para marcar como pagado (*0)"
                        >
                          <i className="bi bi-check2 me-1"></i> Marcar pagado
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 4. Inversiones y Patrimonio (Block C) */}
      <div className="col-12 col-lg-6">
        <div className="card shadow-sm border-0 rounded-4 p-4 h-100 bg-white">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0 text-dark">
              <i className="bi bi-shield-check text-success me-2"></i>
              Patrimonio e Inversiones
            </h5>
            <span className="badge bg-success rounded-pill px-3 py-2 fw-bold">
              Total: {formatCOP(summary.kpis.patrimonio_total)}
            </span>
          </div>

          <div className="list-group list-group-flush">
            {summary.investment_assets.map((inv: any) => (
              <div
                key={inv.name}
                className="list-group-item d-flex justify-content-between align-items-center px-0 py-3 border-light"
              >
                <div>
                  <div className="fw-semibold text-dark">{inv.name}</div>
                  <small className="text-muted">
                    {inv.asset_type === 'crypto' && `${inv.units} unidades @ ${formatCOP(inv.exchange_rate)}`}
                    {inv.asset_type === 'fiducia' && 'Rendimiento: 7.00% E.A.'}
                    {inv.asset_type === 'cesantias' && 'Cesantías acumuladas'}
                  </small>
                </div>
                <div className="text-end">
                  <div className="fw-bold text-dark fs-6">{formatCOP(inv.calculated_value)}</div>
                  {inv.asset_type === 'fiducia' && (
                    <small className="text-success fw-semibold">
                      +{formatCOP(summary.kpis.rendimiento_mensual_fiducia)}/mes
                    </small>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 5. Metas Financieras (Block G) */}
      <div className="col-12 col-lg-6">
        <div className="card shadow-sm border-0 rounded-4 p-4 h-100 bg-white">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="fw-bold mb-0 text-dark">
              <i className="bi bi-bullseye text-warning me-2"></i>
              Metas Financieras
            </h5>
            <span className="badge bg-warning text-dark rounded-pill px-3 py-2 fw-bold">
              {summary.financial_goals.length} Metas
            </span>
          </div>

          <div className="d-flex flex-column gap-3">
            {summary.financial_goals.map((g: any) => {
              const pct = Math.min(100, Math.round((g.allocated_amount / (g.target_amount || 1)) * 100));
              return (
                <div key={g.name} className="p-3 bg-light rounded-3">
                  <div className="d-flex justify-content-between align-items-center mb-1">
                    <span className="fw-bold text-dark">{g.name}</span>
                    <span className="small fw-semibold text-primary">{pct}%</span>
                  </div>
                  <div className="progress mb-2" style={{ height: '6px' }}>
                    <div
                      className="progress-bar bg-primary"
                      role="progressbar"
                      style={{ width: `${pct}%` }}
                      aria-valuenow={pct}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    ></div>
                  </div>
                  <div className="d-flex justify-content-between small text-muted">
                    <span>Asignado: {formatCOP(g.allocated_amount)}</span>
                    <span>Objetivo: {formatCOP(g.target_amount)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
