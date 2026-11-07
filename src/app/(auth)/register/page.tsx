'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');
    setSuccessMsg('');

    if (!isSupabaseConfigured()) {
      localStorage.setItem('rbr_auth_user', JSON.stringify({ email, fullName, role: 'admin' }));
      router.push('/dashboard');
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      if (error) {
        setErrorMsg(error.message || 'No fue posible registrar el usuario.');
      } else {
        // Trigger seed endpoint for new user
        if (data.user) {
          try {
            await fetch('/api/py/seed', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ user_id: data.user.id }),
            });
          } catch (e) {
            console.error('Seed trigger error:', e);
          }
        }
        setSuccessMsg('¡Cuenta creada exitosamente! Redirigiendo al panel...');
        setTimeout(() => router.push('/dashboard'), 1500);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error inesperado');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container min-vh-100 d-flex align-items-center justify-content-center py-5">
      <div className="col-12 col-md-8 col-lg-5">
        <div className="text-center mb-4">
          <div className="d-inline-flex align-items-center justify-content-center bg-primary text-white rounded-circle mb-3 shadow" style={{ width: '64px', height: '64px', fontSize: '2rem' }}>
            <i className="bi bi-person-plus"></i>
          </div>
          <h2 className="fw-bold text-dark">Crear Cuenta</h2>
          <p className="text-muted">Inicia con tus plantillas financieras y cálculo de excedentes</p>
        </div>

        <div className="card shadow-sm border-0 rounded-4 p-4 p-md-5 bg-white">
          <h4 className="fw-semibold mb-4 text-center">Registro de Usuario</h4>

          {errorMsg && (
            <div className="alert alert-danger d-flex align-items-center" role="alert">
              <i className="bi bi-exclamation-triangle-fill me-2"></i>
              <div>{errorMsg}</div>
            </div>
          )}

          {successMsg && (
            <div className="alert alert-success d-flex align-items-center" role="alert">
              <i className="bi bi-check-circle-fill me-2"></i>
              <div>{successMsg}</div>
            </div>
          )}

          <form onSubmit={handleRegister}>
            <div className="mb-3">
              <label className="form-label text-muted small fw-bold">Nombre Completo</label>
              <div className="input-group">
                <span className="input-group-text bg-light border-end-0"><i className="bi bi-person text-muted"></i></span>
                <input
                  type="text"
                  className="form-control bg-light border-start-0"
                  placeholder="Albeiro Yaime"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                />
              </div>
            </div>

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
                  required
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
                  placeholder="Mínimo 6 caracteres"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={6}
                  required
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
                  Registrando...
                </>
              ) : (
                'Crear Mi Cuenta'
              )}
            </button>
          </form>

          <hr className="my-4" />

          <p className="text-center text-muted small mb-0">
            ¿Ya tienes una cuenta?{' '}
            <Link href="/login" className="text-primary text-decoration-none fw-semibold">
              Iniciar Sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
