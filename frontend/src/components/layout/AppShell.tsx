import { LogOut, ShieldCheck } from 'lucide-react';
import { Outlet } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/useAuth';

function roleLabel(role: string): string {
  return role.replace(/_/g, ' ');
}

export default function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-[#0a2540] text-white">
              <ShieldCheck className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-gray-900">FHPL Endorsement Platform</p>
              <p className="text-xs text-gray-500">Secure operations console</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-semibold text-gray-900">{user?.full_name || 'Authenticated User'}</p>
              <p className="text-xs text-gray-500">{roleLabel(user?.role || 'VIEWER')}</p>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  );
}
