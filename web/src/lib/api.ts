/**
 * API client for Dawai Yaad backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

export class ApiError extends Error {
  statusCode: number;
  constructor(statusCode: number, message: string) {
    super(message);
    this.statusCode = statusCode;
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(resp: Response) {
  if (resp.ok) return resp.json();
  const body = await resp.json().catch(() => ({ detail: 'Request failed' }));
  throw new ApiError(resp.status, body.detail || 'Request failed');
}

export const api = {
  // Auth
  async sendOtp(phone: string) {
    const resp = await fetch(`${API_BASE}/auth/send-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
    });
    return handleResponse(resp);
  },

  async verifyOtp(phone: string, otp: string, name?: string) {
    const body: Record<string, string> = { phone, otp };
    if (name) body.name = name;
    const resp = await fetch(`${API_BASE}/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await handleResponse(resp);
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user_id', data.user_id);
    localStorage.setItem('user_name', data.name || '');
    localStorage.setItem('user_role', data.role || '');
    return data;
  },

  async getProfile() {
    const resp = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  // Medications
  async todaySchedule(userId?: string) {
    const params = userId ? `?user_id=${userId}` : '';
    const resp = await fetch(`${API_BASE}/medications/schedule/today${params}`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async listMedications(userId?: string) {
    const params = userId ? `?user_id=${userId}` : '';
    const resp = await fetch(`${API_BASE}/medications${params}`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async markTaken(medId: string) {
    const resp = await fetch(`${API_BASE}/medications/${medId}/taken`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'taken' }),
    });
    return handleResponse(resp);
  },

  // Family
  async listFamilies() {
    const resp = await fetch(`${API_BASE}/families`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async linkedPatients() {
    const resp = await fetch(`${API_BASE}/families/linked-patients`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  // Hospital
  async nurseDashboard(hospitalId: string) {
    const resp = await fetch(`${API_BASE}/hospitals/${hospitalId}/dashboard`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async listHospitals() {
    const resp = await fetch(`${API_BASE}/hospitals`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async listAssignments(hospitalId: string) {
    const resp = await fetch(`${API_BASE}/hospitals/${hospitalId}/assignments`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async administerDose(hospitalId: string, medId: string) {
    const resp = await fetch(`${API_BASE}/hospitals/${hospitalId}/administer/${medId}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    return handleResponse(resp);
  },

  // SOS
  async activeAlerts() {
    const resp = await fetch(`${API_BASE}/sos/active`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async acknowledgeAlert(alertId: string, notes?: string) {
    const resp = await fetch(`${API_BASE}/sos/${alertId}/acknowledge`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse(resp);
  },

  async resolveAlert(alertId: string, notes?: string) {
    const resp = await fetch(`${API_BASE}/sos/${alertId}/resolve`, {
      method: 'PUT',
      headers: { ...authHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    return handleResponse(resp);
  },

  // Notifications
  async notifications(limit = 20) {
    const resp = await fetch(`${API_BASE}/notifications?limit=${limit}`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  async unreadCount() {
    const resp = await fetch(`${API_BASE}/notifications/unread-count`, { headers: authHeaders() });
    return handleResponse(resp);
  },

  // Reports
  adherenceReportUrl(userId?: string, days = 30) {
    const params = [`days=${days}`];
    if (userId) params.push(`user_id=${userId}`);
    return `${API_BASE}/documents/report/adherence?${params.join('&')}`;
  },

  // WebSocket
  sosWebSocketUrl(userId: string) {
    const wsBase = API_BASE.replace('http', 'ws');
    return `${wsBase}/sos/ws/${userId}`;
  },

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
  },

  isLoggedIn(): boolean {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem('access_token');
  },
};
