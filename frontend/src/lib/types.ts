/**
 * Shared TypeScript types — only define types for models that actually exist.
 * Add new interfaces here as backend tables are created.
 */

// ── User ────────────────────────────────────
export type UserRole = 'ADMIN' | 'OPERATOR' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
}

export interface UpdateUserPayload {
  email?: string;
  full_name?: string;
  role?: UserRole;
}

// ── API Response Wrappers ───────────────────
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  offset: number;
  limit: number;
}
