'use client';

import React, { useState, useEffect } from 'react';
import { Navbar } from '@/components/Navbar';

export default function AISettingsPage() {
  const [provider, setProvider] = useState('anthropic');
  const [authMode, setAuthMode] = useState('oauth_token');
  const [token, setToken] = useState('');
  const [preferredModel, setPreferredModel] = useState('claude-3-7-sonnet-latest');
  const [maskedToken, setMaskedToken] = useState<string | null>(null);
  const [lastTestedAt, setLastTestedAt] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'danger'; text: string } | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; latency?: number; message?: string } | null>(null);

  useEffect(() => {
    fetch('/api/py/settings/ai')
      .then((res) => res.json())
      .then((data) => {
        if (data.has_credential) {
          setProvider(data.provider || 'anthropic');
          setAuthMode(data.auth_mode || 'oauth_token');
          setMaskedToken(data.masked_token);
          setPreferredModel(data.preferred_model || 'claude-3-7-sonnet-latest');
          setLastTestedAt(data.last_tested_at);
        }
      })
      .catch((err) => console.error('Error fetching AI settings:', err));
  }, []);

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    if (newProvider === 'anthropic') {
      setPreferredModel('claude-3-7-sonnet-latest');
    } else if (newProvider === 'openai') {
      setPreferredModel('gpt-4o');
      setAuthMode('api_key');
    } else if (newProvider === 'groq') {
      setPreferredModel('llama-3.1-8b-instant');
      setAuthMode('api_key');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;

    setSaving(true);
    setStatusMessage(null);

    try {
      const res = await fetch('/api/py/settings/ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          token: token.trim(),
          preferred_model: preferredModel,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setMaskedToken(data.masked_token);
        setAuthMode(data.auth_mode);
        setToken('');
        setStatusMessage({ type: 'success', text: data.message || 'Token guardado y cifrado con éxito.' });
      } else {
        setStatusMessage({ type: 'danger', text: data.detail || 'Error al guardar credencial.' });
      }
    } catch (err: any) {
      setStatusMessage({ type: 'danger', text: err.message || 'Error de red.' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const res = await fetch('/api/py/settings/ai/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          token: token.trim() || undefined,
          model: preferredModel,
        }),
      });

      const data = await res.json();
      if (data.status === 'success') {
        setTestResult({
          success: true,
          latency: data.latency_ms,
          message: data.message,
        });
        setLastTestedAt(new Date().toISOString());
      } else {
        setTestResult({
          success: false,
          latency: data.latency_ms,
          message: data.message,
        });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Fallo de conexión.',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="min-vh-100 d-flex flex-column pb-5">
      <Navbar />

      <main className="container py-4 flex-grow-1">
        <div className="row justify-content-center">
          <div className="col-12 col-lg-8">
            <div className="d-flex align-items-center mb-4 gap-3">
              <div className="d-inline-flex align-items-center justify-content-center bg-primary text-white rounded-circle shadow-sm" style={{ width: '48px', height: '48px' }}>
                <i className="bi bi-cpu fs-4"></i>
              </div>
              <div>
                <h3 className="fw-bold text-dark mb-0">Credenciales del Agente IA</h3>
                <p className="text-muted small mb-0">
                  Cifrado de grado militar (AES-256 / Fernet) con soporte para Claude Setup-Token y API Keys
                </p>
              </div>
            </div>

            {statusMessage && (
              <div className={`alert alert-${statusMessage.type} alert-dismissible fade show rounded-4`} role="alert">
                <i className={`bi bi-${statusMessage.type === 'success' ? 'check-circle-fill' : 'exclamation-circle-fill'} me-2`}></i>
                {statusMessage.text}
                <button type="button" className="btn-close" onClick={() => setStatusMessage(null)}></button>
              </div>
            )}

            {/* AI Vault Card */}
            <div className="card shadow-sm border-0 rounded-4 p-4 p-md-5 bg-white mb-4">
              <form onSubmit={handleSave}>
                {/* Provider Selector */}
                <div className="mb-4">
                  <label className="form-label text-dark fw-bold small text-uppercase">Proveedor de Inteligencia Artificial</label>
                  <div className="row g-2">
                    <div className="col-12 col-md-4">
                      <div
                        onClick={() => handleProviderChange('anthropic')}
                        className={`card p-3 border-2 cursor-pointer text-center rounded-3 ${provider === 'anthropic' ? 'border-primary bg-primary-subtle text-primary fw-bold' : 'border-light bg-light text-dark'}`}
                        style={{ cursor: 'pointer' }}
                      >
                        <i className="bi bi-stars fs-4 mb-1"></i>
                        <div>Anthropic Claude</div>
                        <small className="fw-normal text-muted" style={{ fontSize: '0.75rem' }}>Setup-Token & API</small>
                      </div>
                    </div>
                    <div className="col-12 col-md-4">
                      <div
                        onClick={() => handleProviderChange('openai')}
                        className={`card p-3 border-2 cursor-pointer text-center rounded-3 ${provider === 'openai' ? 'border-primary bg-primary-subtle text-primary fw-bold' : 'border-light bg-light text-dark'}`}
                        style={{ cursor: 'pointer' }}
                      >
                        <i className="bi bi-robot fs-4 mb-1"></i>
                        <div>OpenAI</div>
                        <small className="fw-normal text-muted" style={{ fontSize: '0.75rem' }}>GPT-4o & Mini</small>
                      </div>
                    </div>
                    <div className="col-12 col-md-4">
                      <div
                        onClick={() => handleProviderChange('groq')}
                        className={`card p-3 border-2 cursor-pointer text-center rounded-3 ${provider === 'groq' ? 'border-primary bg-primary-subtle text-primary fw-bold' : 'border-light bg-light text-dark'}`}
                        style={{ cursor: 'pointer' }}
                      >
                        <i className="bi bi-lightning-charge fs-4 mb-1"></i>
                        <div>Groq Fast</div>
                        <small className="fw-normal text-muted" style={{ fontSize: '0.75rem' }}>Llama 3.1 Instant</small>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Model Selector */}
                <div className="mb-4">
                  <label className="form-label text-dark fw-bold small text-uppercase">Modelo Preferido</label>
                  <select
                    className="form-select bg-light"
                    value={preferredModel}
                    onChange={(e) => setPreferredModel(e.target.value)}
                  >
                    {provider === 'anthropic' && (
                      <>
                        <option value="claude-3-7-sonnet-latest">claude-3-7-sonnet-latest (Recomendado)</option>
                        <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet-20241022</option>
                        <option value="claude-3-haiku-20240307">claude-3-haiku-20240307 (Rápido)</option>
                      </>
                    )}
                    {provider === 'openai' && (
                      <>
                        <option value="gpt-4o">gpt-4o</option>
                        <option value="gpt-4o-mini">gpt-4o-mini</option>
                      </>
                    )}
                    {provider === 'groq' && (
                      <>
                        <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
                        <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile</option>
                      </>
                    )}
                  </select>
                </div>

                {/* Stored Token Preview */}
                {maskedToken && (
                  <div className="p-3 bg-light rounded-3 mb-4 d-flex justify-content-between align-items-center">
                    <div>
                      <span className="badge bg-success-subtle text-success me-2">Token Cifrado Activo</span>
                      <code className="fw-bold">{maskedToken}</code>
                      {lastTestedAt && (
                        <div className="small text-muted mt-1">
                          Última verificación: {new Date(lastTestedAt).toLocaleTimeString('es-CO')}
                        </div>
                      )}
                    </div>
                    <span className="badge bg-dark rounded-pill">
                      {authMode === 'oauth_token' ? 'Claude Setup-Token (OAuth)' : 'API Key'}
                    </span>
                  </div>
                )}

                {/* Token Input */}
                <div className="mb-4">
                  <label className="form-label text-dark fw-bold small text-uppercase">
                    {maskedToken ? 'Reemplazar Token / Clave' : 'Ingresar Token / Clave'}
                  </label>
                  <div className="input-group">
                    <span className="input-group-text bg-light"><i className="bi bi-key-fill text-muted"></i></span>
                    <input
                      type="password"
                      className="form-control bg-light"
                      placeholder={
                        provider === 'anthropic'
                          ? 'sk-ant-oat01-... o sk-ant-api03-...'
                          : provider === 'groq'
                          ? 'gsk_...'
                          : 'sk-...'
                      }
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      required={!maskedToken}
                    />
                  </div>
                  <div className="form-text">
                    {provider === 'anthropic'
                      ? 'Admite tokens de claude setup-token (sk-ant-oat01-*) con cabecera OAuth beta o API Keys normales.'
                      : 'El token se cifra antes de almacenarse en la base de datos y nunca se expone en texto plano.'}
                  </div>
                </div>

                {/* Actions */}
                <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center pt-2">
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    className="btn btn-outline-primary px-4 rounded-pill fw-semibold"
                    disabled={testing || (!token.trim() && !maskedToken)}
                  >
                    {testing ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Probando Ping...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-broadcast me-2"></i>
                        Probar Conexión (Ping 5 Tokens)
                      </>
                    )}
                  </button>

                  <button
                    type="submit"
                    className="btn btn-primary px-4 rounded-pill fw-bold shadow-sm"
                    disabled={saving || !token.trim()}
                  >
                    {saving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Guardando Cifrado...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-lock-fill me-2"></i>
                        Guardar Cifrado en Bóveda
                      </>
                    )}
                  </button>
                </div>
              </form>

              {/* Test Result Feedback */}
              {testResult && (
                <div className={`mt-4 alert alert-${testResult.success ? 'success' : 'danger'} rounded-3 p-3 mb-0`} role="alert">
                  <div className="d-flex justify-content-between align-items-center">
                    <div>
                      <i className={`bi bi-${testResult.success ? 'check-circle-fill' : 'x-circle-fill'} me-2 fs-5`}></i>
                      <strong>{testResult.success ? 'Conexión Exitosa' : 'Error en la Prueba'}:</strong> {testResult.message}
                    </div>
                    {testResult.latency !== undefined && (
                      <span className="badge bg-white text-dark border">
                        Latencia: {testResult.latency} ms
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
