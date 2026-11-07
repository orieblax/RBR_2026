'use client';

import React from 'react';

export function formatCOP(val: number | undefined): string {
  if (val === undefined || val === null || isNaN(val)) return '$0';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(val);
}

interface KPICardsProps {
  kpis: {
    total_actual: number;
    gastos_mes: number;
    restante: number;
    ingresos: number;
    total_gastos: number;
    ahorro: number;
    pend: number;
    incl_pend: number;
    proyeccion_invertible_anual: number;
  };
}

export function KPICards({ kpis }: KPICardsProps) {
  return (
    <div className="row g-3 mb-4">
      {/* 1. Primary Monthly Investable KPI (Cell B22: Incl Pend) */}
      <div className="col-12 col-md-6 col-xl-3">
        <div className="card kpi-card highlight p-4 h-100 position-relative overflow-hidden">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <span className="badge bg-white text-primary fw-bold text-uppercase px-2 py-1">
              Capacidad Invertible
            </span>
            <i className="bi bi-graph-up-arrow fs-4 opacity-75"></i>
          </div>
          <div className="text-white-50 small mb-1">Disponible Este Mes (Incl Pend)</div>
          <div className="kpi-value text-white mb-2">{formatCOP(kpis.incl_pend)}</div>
          <div className="small text-white-50">
            <i className="bi bi-info-circle me-1"></i>
            Restante + Pendientes - Egresos
          </div>
        </div>
      </div>

      {/* 2. Projected Annual Investable */}
      <div className="col-12 col-md-6 col-xl-3">
        <div className="card kpi-card bg-white p-4 h-100">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <span className="badge bg-success-subtle text-success fw-bold text-uppercase px-2 py-1">
              Proyección 2026
            </span>
            <i className="bi bi-piggy-bank text-success fs-4"></i>
          </div>
          <div className="text-muted small mb-1">Proyección Anual Invertible</div>
          <div className="kpi-value text-dark mb-2">{formatCOP(kpis.proyeccion_invertible_anual)}</div>
          <div className="small text-muted">
            <i className="bi bi-calendar3 me-1"></i>
            Ahorro base x 11m + Excedente actual
          </div>
        </div>
      </div>

      {/* 3. Liquidez Restante (Cell B20: Restante) */}
      <div className="col-12 col-md-6 col-xl-3">
        <div className="card kpi-card bg-white p-4 h-100">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <span className="badge bg-info-subtle text-info-emphasis fw-bold text-uppercase px-2 py-1">
              Liquidez Neta
            </span>
            <i className="bi bi-cash-stack text-info fs-4"></i>
          </div>
          <div className="text-muted small mb-1">Liquidez Restante (Restante)</div>
          <div className="kpi-value text-dark mb-2">{formatCOP(kpis.restante)}</div>
          <div className="small text-muted">
            Total actual ({formatCOP(kpis.total_actual)}) - Gastos mes ({formatCOP(kpis.gastos_mes)})
          </div>
        </div>
      </div>

      {/* 4. Ahorro Mensual Base (Cell D20: Ahorro) */}
      <div className="col-12 col-md-6 col-xl-3">
        <div className="card kpi-card bg-white p-4 h-100">
          <div className="d-flex justify-content-between align-items-start mb-2">
            <span className="badge bg-warning-subtle text-warning-emphasis fw-bold text-uppercase px-2 py-1">
              Flujo Operativo
            </span>
            <i className="bi bi-arrow-repeat text-warning-emphasis fs-4"></i>
          </div>
          <div className="text-muted small mb-1">Ahorro Mensual Base</div>
          <div className="kpi-value text-dark mb-2">{formatCOP(kpis.ahorro)}</div>
          <div className="small text-muted">
            Ingresos ({formatCOP(kpis.ingresos)}) - Total gastos ({formatCOP(kpis.total_gastos)})
          </div>
        </div>
      </div>
    </div>
  );
}
