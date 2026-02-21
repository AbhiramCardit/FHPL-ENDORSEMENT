import type { ReactNode } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from './useAuth';

interface RedirectState {
  from?: {
    pathname?: string;
    search?: string;
    hash?: string;
  };
}

function getRedirectTarget(state: unknown): string | null {
  if (!state || typeof state !== 'object') {
    return null;
  }

  const maybeState = state as RedirectState;
  const from = maybeState.from;
  if (!from || typeof from !== 'object') {
    return null;
  }

  const pathname = from.pathname || '';
  if (!pathname.startsWith('/')) {
    return null;
  }

  return `${pathname}${from.search || ''}${from.hash || ''}`;
}

function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-600 shadow-sm">
        Validating session...
      </div>
    </div>
  );
}

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <FullPageLoader />;
  }

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function PublicOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <FullPageLoader />;
  }

  if (status === 'authenticated') {
    const redirectTarget = getRedirectTarget(location.state) || '/pipelines';
    return <Navigate to={redirectTarget} replace />;
  }

  return <>{children}</>;
}
