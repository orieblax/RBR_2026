'use client';

import React, { useState } from 'react';
import { formatCOP } from './KPICards';
import { authFetch } from '@/lib/api';

interface ConfirmationModalProps {
  stagedAction: any | null;
  onClose: () => void;
  onConfirmed: () => void;
}

export function ConfirmationModal({
  stagedAction,
  onClose,
  onConfirmed,
}: ConfirmationModalProps) {
  const [loading, setLoading] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);

  if (!stagedAction) return null;

  const {
    tool_name,
    preview_summary,
    impact_delta,
    kpis_before,
    kpis_after,
    action_id,
    target_item,
    candidates,
  } = stagedAction;

  const hasCandidates = Array.isArray(candidates) && candidates.length > 0;
  const activeCandidate = selectedCandidate || (hasCandidates ? candidates[0] : null);

  // If a candidate is selected, use candidate metrics if available
  const deltaRestante = activeCandidate?.delta_restante ?? impact_delta?.delta_restante ?? 0;
  const deltaInclPend = activeCandidate?.delta_incl_pend ?? impact_delta?.delta_incl_pend ?? 0;
  const displayTarget = activeCandidate?.target_item || target_item;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await authFetch('/api/py/voice/confirm', {
        method: 'POST',
        body: JSON.stringify({
          action_id,
          selected_candidate: activeCandidate,
        }),
      });
      onConfirmed();
    } catch (err) {
      console.error('Error confirming voice action:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    try {
      await authFetch('/api/py/voice/cancel', {
        method: 'POST',
        body: JSON.stringify({ action_id }),
      });
    } catch (err) {
      console.error('Error cancelling action:', err);
    }
    onClose();
  };

  return (
    <div
      className="modal fade show d-block"
      tabIndex={-1}
      style={{ backgroundColor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', zIndex: 1060 }}
    >
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
          <div className="modal-header bg-primary text-white py-3">
            <h6 className="modal-title fw-bold d-flex align-items-center gap-2">
              <i className="bi bi-shield-check fs-5"></i>
              Confirmar Modificación Financiera
            </h6>
            <button type="button" className="btn-close btn-close-white" onClick={handleCancel}></button>
          </div>

          <div className="modal-body p-4">
            {/* Action Summary Alert */}
            <div className="alert alert-primary d-flex align-items-center mb-3 py-2 px-3 rounded-3" role="alert">
              <i className="bi bi-mic-fill text-primary me-2 fs-5"></i>
              <div className="small fw-semibold">
                {activeCandidate ? activeCandidate.preview_summary : preview_summary || 'Acción solicitada por voz'}
              </div>
            </div>

            {/* Target Item Highlight Card (Direct Account or Invoice Change) */}
            {displayTarget && (
              <div className="card border-0 bg-light-subtle rounded-3 p-3 mb-3 border-start border-4 border-primary shadow-sm">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span className="badge bg-primary-subtle text-primary fw-semibold px-2 py-1">
                    {displayTarget.category_label || 'Movimiento'}
                  </span>
                  {displayTarget.note && (
                    <span className="badge bg-secondary-subtle text-secondary fw-normal">
                      <i className="bi bi-tag me-1"></i>
                      {displayTarget.note}
                    </span>
                  )}
                </div>

                <div className="d-flex justify-content-between align-items-baseline">
                  <div>
                    <h5 className="fw-bold mb-0 text-dark">{displayTarget.name}</h5>
                    <small className="text-muted">
                      {displayTarget.before_status ? (
                        <>
                          Estado actual:{' '}
                          <span className="badge bg-warning-subtle text-warning-emphasis">
                            {displayTarget.before_status}
                          </span>
                        </>
                      ) : (
                        `Saldo anterior: ${formatCOP(displayTarget.before_value)}`
                      )}
                    </small>
                  </div>

                  <div className="text-end">
                    <div className="fs-5 fw-bold text-primary">
                      {displayTarget.after_status ? (
                        <span className="badge bg-success">{displayTarget.after_status}</span>
                      ) : (
                        formatCOP(displayTarget.after_value)
                      )}
                    </div>
                    {displayTarget.delta !== undefined && (
                      <small className={`fw-semibold ${displayTarget.delta >= 0 ? 'text-success' : 'text-danger'}`}>
                        {displayTarget.delta >= 0
                          ? `+${formatCOP(displayTarget.delta)}`
                          : `-${formatCOP(Math.abs(displayTarget.delta))}`}
                      </small>
                    )}
                  </div>
                </div>

                {/* Secondary Item (Dual Operation: Transfer Destination or Payment/Collection Account) */}
                {displayTarget.secondary_item && (
                  <div className="mt-3 pt-3 border-top border-secondary-subtle">
                    <div className="d-flex justify-content-between align-items-center mb-1">
                      <span className="badge bg-info-subtle text-info-emphasis fw-semibold px-2 py-1">
                        {displayTarget.secondary_item.category_label || 'Cuenta Relacionada'}
                      </span>
                      {displayTarget.secondary_item.note && (
                        <span className="badge bg-secondary-subtle text-secondary fw-normal">
                          {displayTarget.secondary_item.note}
                        </span>
                      )}
                    </div>
                    <div className="d-flex justify-content-between align-items-baseline">
                      <div>
                        <h6 className="fw-bold mb-0 text-dark">{displayTarget.secondary_item.name}</h6>
                        <small className="text-muted">
                          Saldo anterior: {formatCOP(displayTarget.secondary_item.before_value)}
                        </small>
                      </div>
                      <div className="text-end">
                        <div className="fs-6 fw-bold text-primary">
                          {formatCOP(displayTarget.secondary_item.after_value)}
                        </div>
                        {displayTarget.secondary_item.delta !== undefined && (
                          <small
                            className={`fw-semibold ${
                              displayTarget.secondary_item.delta >= 0 ? 'text-success' : 'text-danger'
                            }`}
                          >
                            {displayTarget.secondary_item.delta >= 0
                              ? `+${formatCOP(displayTarget.secondary_item.delta)}`
                              : `-${formatCOP(Math.abs(displayTarget.secondary_item.delta))}`}
                          </small>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Disambiguation Candidates (Case 4: Ante la duda, coloca en el prompt las posibles opciones) */}
            {hasCandidates && (
              <div className="mb-3">
                <label className="form-label small fw-bold text-muted text-uppercase mb-2">
                  <i className="bi bi-question-circle me-1 text-primary"></i>
                  Selecciona la factura a marcar como pagada:
                </label>
                <div className="list-group list-group-flush border rounded-3 overflow-hidden shadow-sm">
                  {candidates.map((cand: any, idx: number) => {
                    const isSelected = (activeCandidate?.item_name || candidates[0].item_name) === cand.item_name;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSelectedCandidate(cand)}
                        className={`list-group-item list-group-item-action d-flex justify-content-between align-items-center p-2.5 ${
                          isSelected ? 'active bg-primary text-white' : ''
                        }`}
                      >
                        <div className="d-flex align-items-center gap-2">
                          <i className={`bi ${isSelected ? 'bi-check-circle-fill' : 'bi-circle'} fs-6`}></i>
                          <span className="fw-semibold">{cand.item_name}</span>
                        </div>
                        <span className={`badge ${isSelected ? 'bg-light text-primary' : 'bg-secondary-subtle text-dark'}`}>
                          {formatCOP(cand.amount)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Impact on Key Financial Metrics */}
            <h6 className="fw-bold text-dark small text-uppercase text-muted mb-2">Impacto en tus métricas:</h6>
            <div className="row g-2 mb-3">
              {/* Impact on Restante */}
              <div className="col-6">
                <div className="p-3 bg-light rounded-3 text-center">
                  <span className="text-muted small d-block mb-1">Liquidez Restante</span>
                  <span className={`fw-bold fs-6 ${deltaRestante >= 0 ? 'text-success' : 'text-danger'}`}>
                    {deltaRestante >= 0 ? `+${formatCOP(deltaRestante)}` : `-${formatCOP(Math.abs(deltaRestante))}`}
                  </span>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {formatCOP(kpis_before?.restante)} → {formatCOP(kpis_after?.restante)}
                  </div>
                </div>
              </div>

              {/* Impact on Incl Pend (Invertible) */}
              <div className="col-6">
                <div className="p-3 bg-light rounded-3 text-center border border-primary-subtle">
                  <span className="text-primary small fw-semibold d-block mb-1">Disp. Invertir (Mes)</span>
                  <span className={`fw-bold fs-6 ${deltaInclPend >= 0 ? 'text-success' : 'text-danger'}`}>
                    {deltaInclPend >= 0 ? `+${formatCOP(deltaInclPend)}` : `-${formatCOP(Math.abs(deltaInclPend))}`}
                  </span>
                  <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                    {formatCOP(kpis_before?.incl_pend)} → {formatCOP(kpis_after?.incl_pend)}
                  </div>
                </div>
              </div>
            </div>

            <p className="text-muted small mb-0 text-center">
              Puedes decir <strong>&quot;Confirmar&quot;</strong> o hacer clic en el botón.
            </p>
          </div>

          <div className="modal-footer border-0 bg-light p-3">
            <button
              type="button"
              className="btn btn-outline-secondary px-4 rounded-pill fw-semibold"
              onClick={handleCancel}
              disabled={loading}
            >
              Cancelar
            </button>
            <button
              type="button"
              className="btn btn-primary px-4 rounded-pill fw-bold shadow-sm"
              onClick={handleConfirm}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2"></span>
                  Confirmando...
                </>
              ) : (
                <>
                  <i className="bi bi-check2-circle me-1"></i>
                  Confirmar
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
