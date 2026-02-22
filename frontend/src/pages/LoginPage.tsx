import { useMemo, useState, type FormEvent } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/features/auth/useAuth';
import { ApiError } from '@/lib/api-client';

interface RedirectState {
  from?: {
    pathname?: string;
    search?: string;
    hash?: string;
  };
}

function resolveRedirectTarget(state: unknown): string {
  if (!state || typeof state !== 'object') {
    return '/pipelines';
  }

  const redirectState = state as RedirectState;
  const from = redirectState.from;

  if (!from || typeof from !== 'object') {
    return '/pipelines';
  }

  const pathname = from.pathname || '';
  if (!pathname.startsWith('/')) {
    return '/pipelines';
  }

  return `${pathname}${from.search || ''}${from.hash || ''}`;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = useMemo(() => resolveRedirectTarget(location.state), [location.state]);
  const isSubmitDisabled = submitting || email.trim().length === 0 || password.trim().length === 0;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setSubmitting(true);
    setErrorMessage(null);

    try {
      await login({
        email: email.trim(),
        password,
      });

      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setErrorMessage('Invalid email or password.');
      } else if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage('Unable to sign in right now. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-8">
      <section className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-[#0a2540] text-white">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Sign In</h1>
            <p className="text-sm text-gray-500">FHPL Endorsement Operations</p>
          </div>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-600" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@endorsements.local"
              disabled={submitting}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-600" htmlFor="password">
              Password
            </label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              disabled={submitting}
            />
          </div>

          {errorMessage && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
              {errorMessage}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitDisabled}>
            {submitting ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      </section>
    </div>
  );
}
