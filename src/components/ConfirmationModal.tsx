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

  if (!stagedAction) return null;

  const { tool_name, preview_summary, impact_delta, kpis_before, kpis_after, action_id } = stagedAction;

  const deltaRestante = impact_delta?.delta_restante ?? 0;
  const deltaInclPend = impact_delta?.delta_incl_pend ?? 0;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await authFetch('/api/py/voice/confirm', {
        method: 'POST',
        body: JSON.stringify({ action_id }),
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
            <div className="alert alert-primary d-flex align-items-center mb-3 py-2 px-3 rounded-3" role="alert">
              <i className="bi bi-mic-fill text-primary me-2 fs-5"></i>
              <div className="small fw-semibold">{preview_summary || 'Acción solicitada por voz'}</div>
            </div>

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
