/**
 * Backend API client — centralized HTTP calls.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string) {
    this.token = token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // ── Insurees ──────────────────────────────
  getInsurees() { return this.request('/insurees'); }
  createInsuree(data: unknown) { return this.request('/insurees', { method: 'POST', body: JSON.stringify(data) }); }
  updateInsuree(id: string, data: unknown) { return this.request(`/insurees/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
  testSftp(id: string) { return this.request(`/insurees/${id}/test-sftp`, { method: 'POST' }); }
  triggerPoll(id: string) { return this.request(`/insurees/${id}/trigger-poll`, { method: 'POST' }); }

  // ── Files ─────────────────────────────────
  getFiles() { return this.request('/files'); }
  getFile(id: string) { return this.request(`/files/${id}`); }

  // ── Endorsements ──────────────────────────
  getEndorsements() { return this.request('/endorsements'); }
  getEndorsement(id: string) { return this.request(`/endorsements/${id}`); }
  approveEndorsement(id: string) { return this.request(`/endorsements/${id}/approve`, { method: 'POST' }); }
  rejectEndorsement(id: string) { return this.request(`/endorsements/${id}/reject`, { method: 'POST' }); }
  retrySubmission(id: string) { return this.request(`/endorsements/${id}/retry-submission`, { method: 'POST' }); }

  // ── Submissions ───────────────────────────
  getSubmissions() { return this.request('/submissions'); }

  // ── Review ────────────────────────────────
  getReviewQueue() { return this.request('/review'); }

  // ── Reports ───────────────────────────────
  getVolumeReport() { return this.request('/reports/volume'); }
  getSlaReport() { return this.request('/reports/sla'); }
  getErrorReport() { return this.request('/reports/errors'); }

  // ── Pipeline ───────────────────────────────
  triggerPipeline() { return this.request<any>('/pipeline/trigger', { method: 'POST' }); }
  getPipelineRuns(params?: { insurer_code?: string; status?: string; limit?: number; offset?: number }) {
    const qs = new URLSearchParams();
    if (params?.insurer_code) qs.set('insurer_code', params.insurer_code);
    if (params?.status) qs.set('status', params.status);
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    const query = qs.toString();
    return this.request<any>(`/pipeline/runs${query ? '?' + query : ''}`);
  }
  getPipelineRun(id: string) { return this.request<any>(`/pipeline/runs/${id}`); }

  // ── Health ────────────────────────────────
  getHealth() { return this.request('/health'); }
}

export const apiClient = new ApiClient(API_BASE_URL);
export default apiClient;
