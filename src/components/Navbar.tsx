'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    if (isSupabaseConfigured()) {
      await supabase.auth.signOut();
    }
    localStorage.removeItem('rbr_auth_user');
    router.push('/login');
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark sticky-top shadow-sm py-2">
      <div className="container">
        <Link href="/dashboard" className="navbar-brand d-flex align-items-center fw-bold fs-4">
          <i className="bi bi-wallet2 text-primary me-2"></i>
          <span>RBR <span className="text-primary">Finance</span></span>
        </Link>

        <div className="d-flex align-items-center gap-3">
          <div className="navbar-nav flex-row gap-2">
            <Link
              href="/dashboard"
              className={`nav-link px-3 rounded-pill small fw-semibold ${pathname === '/dashboard' ? 'active bg-primary text-white' : 'text-light'}`}
            >
              <i className="bi bi-speedometer2 me-1"></i> Panel
            </Link>
            <Link
              href="/settings/ai"
              className={`nav-link px-3 rounded-pill small fw-semibold ${pathname === '/settings/ai' ? 'active bg-primary text-white' : 'text-light'}`}
            >
              <i className="bi bi-cpu me-1"></i> IA Tokens
            </Link>
            <Link
              href="/admin"
              className={`nav-link px-3 rounded-pill small fw-semibold ${pathname === '/admin' ? 'active bg-primary text-white' : 'text-light'}`}
            >
              <i className="bi bi-shield-lock me-1"></i> Admin
            </Link>
          </div>

          <button
            onClick={handleLogout}
            className="btn btn-outline-light btn-sm rounded-pill px-3"
            title="Cerrar sesión"
          >
            <i className="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </div>
    </nav>
  );
}
