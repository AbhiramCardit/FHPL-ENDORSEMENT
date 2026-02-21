/**
 * Centralized backend API client.
 */

import type { User } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface LoginRequestPayload {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export type UnauthorizedHandler = () => void;

interface RequestOptions {
  skipUnauthorizedHandling?: boolean;
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details: unknown = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private unauthorizedHandler: UnauthorizedHandler | null = null;
  private isDispatchingUnauthorized = false;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
  }

  clearToken() {
    this.token = null;
  }

  setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
    this.unauthorizedHandler = handler;
  }

  private dispatchUnauthorized() {
    if (this.isDispatchingUnauthorized || this.unauthorizedHandler === null) {
      return;
    }

    this.isDispatchingUnauthorized = true;
    try {
      this.unauthorizedHandler();
    } finally {
      this.isDispatchingUnauthorized = false;
    }
  }

  private async parseResponseBody(response: Response): Promise<unknown> {
    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('application/json')) {
      try {
        return (await response.json()) as unknown;
      } catch {
        return null;
      }
    }

    const textBody = await response.text();
    return textBody.length > 0 ? textBody : null;
  }

  private getErrorMessage(statusText: string, details: unknown): string {
    if (details && typeof details === 'object' && 'detail' in details) {
      const detailValue = (details as Record<string, unknown>).detail;
      if (typeof detailValue === 'string' && detailValue.length > 0) {
        return detailValue;
      }
    }

    if (typeof details === 'string' && details.length > 0) {
      return details;
    }

    return statusText || 'API request failed';
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
    requestOptions: RequestOptions = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) || {}),
    };

    if (options.body !== undefined && !('Content-Type' in headers)) {
      headers['Content-Type'] = 'application/json';
    }

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const details = await this.parseResponseBody(response);
      const message = this.getErrorMessage(response.statusText, details);
      const error = new ApiError(response.status, message, details);

      if (response.status === 401 && !requestOptions.skipUnauthorizedHandling) {
        this.dispatchUnauthorized();
      }

      throw error;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  login(payload: LoginRequestPayload) {
    return this.request<TokenResponse>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
      {
        skipUnauthorizedHandling: true,
      },
    );
  }

  getCurrentUser() {
    return this.request<User>('/auth/me');
  }

  getInsurees() {
    return this.request<unknown>('/insurees');
  }

  createInsuree(data: unknown) {
    return this.request<unknown>('/insurees', { method: 'POST', body: JSON.stringify(data) });
  }

  updateInsuree(id: string, data: unknown) {
    return this.request<unknown>(`/insurees/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }

  testSftp(id: string) {
    return this.request<unknown>(`/insurees/${id}/test-sftp`, { method: 'POST' });
  }

  triggerPoll(id: string) {
    return this.request<unknown>(`/insurees/${id}/trigger-poll`, { method: 'POST' });
  }

  getFiles() {
    return this.request<unknown>('/files');
  }

  getFile(id: string) {
    return this.request<unknown>(`/files/${id}`);
  }

  getEndorsements() {
    return this.request<unknown>('/endorsements');
  }

  getEndorsement(id: string) {
    return this.request<unknown>(`/endorsements/${id}`);
  }

  approveEndorsement(id: string) {
    return this.request<unknown>(`/endorsements/${id}/approve`, { method: 'POST' });
  }

  rejectEndorsement(id: string) {
    return this.request<unknown>(`/endorsements/${id}/reject`, { method: 'POST' });
  }

  retrySubmission(id: string) {
    return this.request<unknown>(`/endorsements/${id}/retry-submission`, { method: 'POST' });
  }

  getSubmissions() {
    return this.request<unknown>('/submissions');
  }

  getReviewQueue() {
    return this.request<unknown>('/review');
  }

  getVolumeReport() {
    return this.request<unknown>('/reports/volume');
  }

  getSlaReport() {
    return this.request<unknown>('/reports/sla');
  }

  getErrorReport() {
    return this.request<unknown>('/reports/errors');
  }

  triggerPipeline() {
    return this.request<unknown>('/pipeline/trigger', { method: 'POST' });
  }

  getPipelineRuns(params?: { insurer_code?: string; status?: string; limit?: number; offset?: number }) {
    const qs = new URLSearchParams();
    if (params?.insurer_code) qs.set('insurer_code', params.insurer_code);
    if (params?.status) qs.set('status', params.status);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    const query = qs.toString();
    return this.request<unknown>(`/pipeline/runs${query ? `?${query}` : ''}`);
  }

  getPipelineRun(id: string) {
    return this.request<unknown>(`/pipeline/runs/${id}`);
  }

  getHealth() {
    return this.request<unknown>('/health');
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
export default apiClient;
