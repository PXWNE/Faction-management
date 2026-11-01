/** Thin client for The Bonfire's separate persistent API. The prototype does not
 * enable this adapter automatically; wire it only after the backend URL and
 * authenticated leadership flow are configured for the deployment. */
const TOKEN_KEY = 'bonfire-session-v1';
let apiBase = '';
export function configureBonfireApi(baseUrl) { apiBase = String(baseUrl || '').replace(/\/$/, ''); }
export function hasBonfireSession() { return Boolean(sessionStorage.getItem(TOKEN_KEY)); }
export function clearBonfireSession() { sessionStorage.removeItem(TOKEN_KEY); }
export async function bonfireRequest(path, options = {}) {
  if (!apiBase) throw new Error('Bonfire API URL is not configured.');
  const token = sessionStorage.getItem(TOKEN_KEY);
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
  });
  const payload = response.headers.get('content-type')?.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload?.detail || `Bonfire API request failed (${response.status}).`);
  return payload;
}
export async function signIn(username, password) {
  const result = await bonfireRequest('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
  sessionStorage.setItem(TOKEN_KEY, result.token);
  return result.user;
}
export const bonfireApi = {
  me: () => bonfireRequest('/api/auth/me'),
  members: () => bonfireRequest('/api/members'),
  wars: () => bonfireRequest('/api/wars'),
  audit: () => bonfireRequest('/api/audit'),
  syncRoster: () => bonfireRequest('/api/sync/roster', { method: 'POST' }),
  syncGiveFunds: () => bonfireRequest('/api/sync/give-funds', { method: 'POST' }),
  saveSettlement: (body) => bonfireRequest('/api/settlements', { method: 'POST', body: JSON.stringify(body) }),
  approveSettlement: (id) => bonfireRequest(`/api/settlements/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
  createPaymentIntent: (body, idempotencyKey) => bonfireRequest('/api/payment-intents', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ ...body, idempotency_key: idempotencyKey }) }),
  payments: (warId) => bonfireRequest(`/api/payments${warId ? `?war_id=${encodeURIComponent(warId)}` : ''}`),
};
