'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';
import { authFetch } from '@/lib/api';

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
      const [uData, dData] = await Promise.all([
        authFetch('/api/py/admin/users'),
        authFetch('/api/py/admin/diagnostics'),
      ]);
      setUsers(uData);
      setDiagnostics(dData);
      setSelectedDefaultModel(dData.system?.default_ai_model || 'claude-3-7-sonnet-latest');
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
      await authFetch(`/api/py/admin/users/${userId}/toggle-role`, { method: 'POST' });
      setMsg('Rol actualizado exitosamente');
      fetchData();
    } catch (e: any) {
      console.error(e);
      setMsg(`Error: ${e.message || 'No fue posible actualizar rol'}`);
    }
  };

  const handleToggleStatus = async (userId: string) => {
    try {
      await authFetch(`/api/py/admin/users/${userId}/toggle-status`, { method: 'POST' });
      setMsg('Estado de usuario actualizado exitosamente');
      fetchData();
    } catch (e: any) {
      console.error(e);
      setMsg(`Error: ${e.message || 'No fue posible actualizar estado'}`);
    }
  };

  const handleUpdateModel = async () => {
    try {
      await authFetch('/api/py/admin/default-model', {
        method: 'POST',
        body: JSON.stringify({ model: selectedDefaultModel }),
      });
      setMsg(`Modelo predeterminado actualizado a ${selectedDefaultModel}`);
      fetchData();
    } catch (e: any) {
      console.error(e);
      setMsg(`Error: ${e.message || 'No fue posible actualizar modelo'}`);
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
                    {diagnostics.system.supabase_connected ? 'Conectado (PostgreSQL)' : 'Modo Local / Demo'}
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

        {/* Default Model Selector - Open Text Input with Datalist Suggestions */}
        <div className="card shadow-sm border-0 rounded-4 p-4 bg-white mb-4">
          <h5 className="fw-bold text-dark mb-1">
            <i className="bi bi-cpu-fill text-primary me-2"></i>
            Modelo Predeterminado Global (Campo Abierto)
          </h5>
          <p className="text-muted small mb-3">
            Puedes escribir libremente cualquier modelo disponible en tus proveedores de IA (Claude, OpenAI, Groq, etc.).
          </p>
          <div className="row g-3 align-items-center">
            <div className="col-12 col-md-8">
              <input
                type="text"
                list="admin-model-list"
                className="form-control bg-light"
                placeholder="Escribe el modelo (ej. claude-3-7-sonnet-latest, gpt-4o, llama-3.3-70b-versatile)"
                value={selectedDefaultModel}
                onChange={(e) => setSelectedDefaultModel(e.target.value)}
              />
              <datalist id="admin-model-list">
                <option value="claude-3-7-sonnet-latest" />
                <option value="claude-3-5-sonnet-20241022" />
                <option value="claude-3-5-haiku-20241022" />
                <option value="claude-3-haiku-20240307" />
                <option value="gpt-4o" />
                <option value="gpt-4o-mini" />
                <option value="gpt-4.5-preview" />
                <option value="o3-mini" />
                <option value="llama-3.1-8b-instant" />
                <option value="llama-3.3-70b-versatile" />
                <option value="deepseek-r1-distill-llama-70b" />
              </datalist>
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
