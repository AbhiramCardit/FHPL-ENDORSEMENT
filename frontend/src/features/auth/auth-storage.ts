const ACCESS_TOKEN_STORAGE_KEY = 'fhpl_endorsement_access_token';

export function readStoredAccessToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function writeStoredAccessToken(token: string): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore client storage errors and keep in-memory auth behavior.
  }
}

export function clearStoredAccessToken(): void {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore client storage errors and keep in-memory auth behavior.
  }
}
