'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    if (!isSupabaseConfigured()) {
      // Offline/Dev mode fallback
      localStorage.setItem('rbr_auth_user', JSON.stringify({ email: email || 'albeiro@rbrfinance.com', role: 'admin' }));
      router.push('/dashboard');
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setErrorMsg(error.message || 'Error al iniciar sesión. Revisa tus credenciales.');
      } else if (data.session) {
        router.push('/dashboard');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoAccess = () => {
    localStorage.setItem('rbr_auth_user', JSON.stringify({ email: 'albeiro@rbrfinance.com', role: 'admin' }));
    router.push('/dashboard');
  };

  return (
    <div className="container min-vh-100 d-flex align-items-center justify-content-center py-5">
      <div className="col-12 col-md-8 col-lg-5">
        <div className="text-center mb-4">
          <div className="d-inline-flex align-items-center justify-content-center bg-primary text-white rounded-circle mb-3 shadow" style={{ width: '64px', height: '64px', fontSize: '2rem' }}>
            <i className="bi bi-wallet2"></i>
          </div>
          <h2 className="fw-bold text-dark">RBR Finance Manager</h2>
          <p className="text-muted">Gestión de Liquidez, Flujo de Caja y Capacidad de Inversión</p>
        </div>

        <div className="card shadow-sm border-0 rounded-4 p-4 p-md-5 bg-white">
          <h4 className="fw-semibold mb-4 text-center">Iniciar Sesión</h4>

          {errorMsg && (
            <div className="alert alert-danger d-flex align-items-center" role="alert">
              <i className="bi bi-exclamation-triangle-fill me-2"></i>
              <div>{errorMsg}</div>
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div className="mb-3">
              <label className="form-label text-muted small fw-bold">Correo Electrónico</label>
              <div className="input-group">
                <span className="input-group-text bg-light border-end-0"><i className="bi bi-envelope text-muted"></i></span>
                <input
                  type="email"
                  className="form-control bg-light border-start-0"
                  placeholder="ejemplo@rbrfinance.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required={isSupabaseConfigured()}
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="form-label text-muted small fw-bold">Contraseña</label>
              <div className="input-group">
                <span className="input-group-text bg-light border-end-0"><i className="bi bi-lock text-muted"></i></span>
                <input
                  type="password"
                  className="form-control bg-light border-start-0"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required={isSupabaseConfigured()}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary w-100 py-2 fw-semibold mb-3 rounded-3 shadow-sm"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Ingresando...
                </>
              ) : (
                'Entrar a Mi Panel'
              )}
            </button>

            <button
              type="button"
              onClick={handleDemoAccess}
              className="btn btn-outline-secondary w-100 py-2 fw-semibold rounded-3"
            >
              <i className="bi bi-lightning-charge me-2 text-warning"></i>
              Acceso Rápido Demo (Excel 2026)
            </button>
          </form>

          <hr className="my-4" />

          <p className="text-center text-muted small mb-0">
            ¿No tienes cuenta?{' '}
            <Link href="/register" className="text-primary text-decoration-none fw-semibold">
              Crear cuenta nueva
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
