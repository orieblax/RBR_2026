'use client';

import React, { useState } from 'react';
import { formatCOP } from './KPICards';

interface Adjustment {
  id?: string;
  amount: number;
  note: string;
  created_at?: string;
}

interface ItemWithLedger {
  id?: string;
  name: string;
  parent_type: 'liquid_account' | 'receivable';
  calculated_total?: number;
  calculated_pending?: number;
  adjustments: Adjustment[];
}

interface LedgerDrawerProps {
  item: ItemWithLedger | null;
  onClose: () => void;
  onAddAdjustment: (parentType: string, targetName: string, amount: number, note: string) => Promise<any>;
  onRemoveAdjustment: (id: string) => Promise<any>;
}

export function LedgerDrawer({
  item,
  onClose,
  onAddAdjustment,
  onRemoveAdjustment,
}: LedgerDrawerProps) {
  const [newAmount, setNewAmount] = useState<string>('');
  const [newNote, setNewNote] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  if (!item) return null;

  const currentTotal = item.calculated_total ?? item.calculated_pending ?? 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedAmount = parseFloat(newAmount);
    if (isNaN(parsedAmount) || parsedAmount === 0) return;

    setIsSubmitting(true);
    await onAddAdjustment(item.parent_type, item.name, parsedAmount, newNote || 'Ajuste manual');
    setNewAmount('');
    setNewNote('');
    setIsSubmitting(false);
  };

  return (
    <div
      className="modal fade show d-block"
      tabIndex={-1}
      style={{ backgroundColor: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(3px)' }}
    >
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 shadow-lg rounded-4">
          <div className="modal-header border-bottom pb-3">
            <div>
              <span className="badge bg-primary-subtle text-primary mb-1">Micro-Ledger Aritmético</span>
              <h5 className="modal-title fw-bold text-dark">{item.name}</h5>
            </div>
            <button type="button" className="btn-close" onClick={onClose} aria-label="Close"></button>
          </div>

          <div className="modal-body p-4">
            <div className="d-flex justify-content-between align-items-center bg-light p-3 rounded-3 mb-4">
              <span className="text-muted fw-semibold">Saldo / Valor Actual Calculado:</span>
              <span className="fs-4 fw-bold text-primary">{formatCOP(currentTotal)}</span>
            </div>

            <h6 className="fw-bold text-dark mb-3">Movimientos y Ajustes Inline ({item.adjustments?.length || 0}):</h6>

            {(!item.adjustments || item.adjustments.length === 0) ? (
              <p className="text-muted small italic">No hay ajustes inline registrados en esta cuenta.</p>
            ) : (
              <div className="table-responsive mb-4" style={{ maxHeight: '250px' }}>
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>Descripción / Nota</th>
                      <th className="text-end">Monto</th>
                      <th className="text-center" style={{ width: '60px' }}>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {item.adjustments.map((adj, idx) => (
                      <tr key={adj.id || idx}>
                        <td className="small">{adj.note || 'Movimiento parcial'}</td>
                        <td className={`text-end fw-semibold small ${adj.amount >= 0 ? 'text-success' : 'text-danger'}`}>
                          {adj.amount >= 0 ? `+${formatCOP(adj.amount)}` : `-${formatCOP(Math.abs(adj.amount))}`}
                        </td>
                        <td className="text-center">
                          {adj.id && (
                            <button
                              onClick={() => onRemoveAdjustment(adj.id!)}
                              className="btn btn-outline-danger btn-sm p-1"
                              title="Eliminar movimiento"
                            >
                              <i className="bi bi-trash"></i>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="card bg-light border-0 p-3 rounded-3">
              <h6 className="fw-bold text-dark mb-3">
                <i className="bi bi-plus-circle-fill text-primary me-2"></i>
                Agregar Nuevo Movimiento (+ / -)
              </h6>
              <form onSubmit={handleSubmit} className="row g-2">
                <div className="col-12 col-md-5">
                  <input
                    type="number"
                    step="any"
                    className="form-control"
                    placeholder="Monto (+50000 o -20000)"
                    value={newAmount}
                    onChange={(e) => setNewAmount(e.target.value)}
                    required
                  />
                </div>
                <div className="col-12 col-md-5">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Nota (ej. Retiro, Abono, Factura)"
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                  />
                </div>
                <div className="col-12 col-md-2">
                  <button
                    type="submit"
                    className="btn btn-primary w-100 fw-semibold"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? '...' : 'Agregar'}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <div className="modal-footer border-0">
            <button type="button" className="btn btn-secondary px-4 rounded-3" onClick={onClose}>
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
