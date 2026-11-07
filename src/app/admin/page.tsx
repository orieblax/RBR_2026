'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';

interface AdminUser {
  id: string;
  email: string;
  full_name?: string;
  is_admin: boolean;
  is_active: boolean;
  default_ai_model: string;
  created_at: string;
}

interface Diagnostics {
  status: string;
  system: {
    environment: string;
    supabase_connected: boolean;
    encryption_vault_active: boolean;
    total_users: number;
    stored_ai_credentials: number;
    default_ai_model: string;
  };
}

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [diagnostics, setDiagnostics] = useState<Diagnostics | null>(null);
  const [selectedDefaultModel, setSelectedDefaultModel] = useState('claude-3-7-sonnet-latest');
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const [uRes, dRes] = await Promise.all([
        fetch('/api/py/admin/users'),
        fetch('/api/py/admin/diagnostics'),
      ]);
      if (uRes.ok && dRes.ok) {
        const uData = await uRes.json();
        const dData = await dRes.json();
        setUsers(uData);
        setDiagnostics(dData);
        setSelectedDefaultModel(dData.system?.default_ai_model || 'claude-3-7-sonnet-latest');
      }
    } catch (err) {
      console.error('Error fetching admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleToggleRole = async (userId: string) => {
    try {
      const res = await fetch(`/api/py/admin/users/${userId}/toggle-role`, { method: 'POST' });
      if (res.ok) {
        setMsg('Rol actualizado exitosamente');
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleStatus = async (userId: string) => {
    try {
      const res = await fetch(`/api/py/admin/users/${userId}/toggle-status`, { method: 'POST' });
      if (res.ok) {
        setMsg('Estado de usuario actualizado exitosamente');
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpdateModel = async () => {
    try {
      const res = await fetch('/api/py/admin/default-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedDefaultModel }),
      });
      if (res.ok) {
        setMsg(`Modelo predeterminado actualizado a ${selectedDefaultModel}`);
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="min-vh-100 d-flex flex-column">
        <Navbar />
        <div className="flex-grow-1 d-flex align-items-center justify-content-center">
          <div className="spinner-border text-primary" role="status"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-vh-100 d-flex flex-column pb-5">
      <Navbar />

      <main className="container py-4 flex-grow-1">
        <div className="d-flex align-items-center mb-4 gap-3">
          <div className="d-inline-flex align-items-center justify-content-center bg-dark text-white rounded-circle shadow-sm" style={{ width: '48px', height: '48px' }}>
            <i className="bi bi-shield-lock fs-4 text-warning"></i>
          </div>
          <div>
            <h3 className="fw-bold text-dark mb-0">Consola de Administración</h3>
            <p className="text-muted small mb-0">Diagnósticos del sistema, roles RBAC y modelos de IA</p>
          </div>
        </div>

        {msg && (
          <div className="alert alert-success alert-dismissible fade show rounded-4" role="alert">
            <i className="bi bi-check-circle-fill me-2"></i>
            {msg}
            <button type="button" className="btn-close" onClick={() => setMsg(null)}></button>
          </div>
        )}

        {/* Diagnostics & Health Cards */}
        {diagnostics && (
          <div className="row g-3 mb-4">
            <div className="col-12 col-md-3">
              <div className="card shadow-sm border-0 rounded-4 p-3 bg-white h-100">
                <div className="text-muted small mb-1">Estado de Supabase</div>
                <div className="d-flex align-items-center gap-2">
                  <span className={`badge ${diagnostics.system.supabase_connected ? 'bg-success' : 'bg-info text-dark'}`}>
                    {diagnostics.system.supabase_connected ? 'Conectado (PostgreSQL)' : 'Modo Local / Dev'}
                  </span>
                </div>
              </div>
            </div>

            <div className="col-12 col-md-3">
              <div className="card shadow-sm border-0 rounded-4 p-3 bg-white h-100">
                <div className="text-muted small mb-1">Bóveda Cifrada (AES-256)</div>
                <div className="d-flex align-items-center gap-2">
                  <span className="badge bg-success">
                    <i className="bi bi-check2 me-1"></i> Activa & Cifrada
                  </span>
                </div>
              </div>
            </div>

            <div className="col-12 col-md-3">
              <div className="card shadow-sm border-0 rounded-4 p-3 bg-white h-100">
                <div className="text-muted small mb-1">Usuarios Registrados</div>
                <div className="fs-4 fw-bold text-dark">{diagnostics.system.total_users}</div>
              </div>
            </div>

            <div className="col-12 col-md-3">
              <div className="card shadow-sm border-0 rounded-4 p-3 bg-white h-100">
                <div className="text-muted small mb-1">Credenciales IA Activas</div>
                <div className="fs-4 fw-bold text-primary">{diagnostics.system.stored_ai_credentials}</div>
              </div>
            </div>
          </div>
        )}

        {/* Default Model Selector */}
        <div className="card shadow-sm border-0 rounded-4 p-4 bg-white mb-4">
          <h5 className="fw-bold text-dark mb-3">
            <i className="bi bi-cpu-fill text-primary me-2"></i>
            Modelo Predeterminado para Nuevos Usuarios y Agente
          </h5>
          <div className="row g-3 align-items-center">
            <div className="col-12 col-md-8">
              <select
                className="form-select bg-light"
                value={selectedDefaultModel}
                onChange={(e) => setSelectedDefaultModel(e.target.value)}
              >
                <option value="claude-3-7-sonnet-latest">claude-3-7-sonnet-latest (Recomendado)</option>
                <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet-20241022</option>
                <option value="claude-3-haiku-20240307">claude-3-haiku-20240307</option>
                <option value="gpt-4o">gpt-4o</option>
                <option value="gpt-4o-mini">gpt-4o-mini</option>
                <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Groq)</option>
              </select>
            </div>
            <div className="col-12 col-md-4">
              <button
                onClick={handleUpdateModel}
                className="btn btn-primary w-100 rounded-pill fw-semibold"
              >
                Actualizar Modelo Global
              </button>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="card shadow-sm border-0 rounded-4 p-4 bg-white">
          <h5 className="fw-bold text-dark mb-3">
            <i className="bi bi-people-fill text-primary me-2"></i>
            Gestión de Usuarios y Roles (RBAC)
          </h5>

          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Usuario</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Fecha Registro</th>
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="fw-semibold text-dark">{u.full_name || 'Sin nombre'}</td>
                    <td className="text-muted small">{u.email}</td>
                    <td>
                      <span className={`badge ${u.is_admin ? 'bg-primary' : 'bg-secondary'}`}>
                        {u.is_admin ? 'Administrador' : 'Usuario'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'}`}>
                        {u.is_active ? 'Activo' : 'Suspendido'}
                      </span>
                    </td>
                    <td className="text-muted small">
                      {new Date(u.created_at).toLocaleDateString('es-CO')}
                    </td>
                    <td className="text-center">
                      <div className="btn-group btn-group-sm">
                        <button
                          onClick={() => handleToggleRole(u.id)}
                          className="btn btn-outline-secondary"
                          title="Alternar rol Admin"
                        >
                          <i className="bi bi-shield me-1"></i> Alternar Rol
                        </button>
                        <button
                          onClick={() => handleToggleStatus(u.id)}
                          className="btn btn-outline-danger"
                          title="Alternar estado activo"
                        >
                          <i className="bi bi-power me-1"></i>
                          {u.is_active ? 'Suspender' : 'Activar'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
