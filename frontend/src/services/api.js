/**
 * 运行时必需。前端调用 Flask /api 的 fetch 封装（分析任务、用户等）。
 */
const API_BASE = import.meta.env.VITE_ANALYSIS_API_BASE || '';
// 生产环境视频上传走独立子域名，绕过 Cloudflare 100MB 免费限制
const UPLOAD_BASE = import.meta.env.PROD ? 'https://upload.magic-cloak.com' : '';
const ACCOUNT_ID_KEY = 'ai_sport_lab.current_account_id';

function withAccountHeader(options = {}) {
  let accountId = '';
  try {
    accountId = window.localStorage.getItem(ACCOUNT_ID_KEY) || '';
  } catch {
    accountId = '';
  }
  if (!accountId) return options;
  return {
    ...options,
    headers: {
      ...(options.headers || {}),
      'X-Account-Id': accountId,
    },
  };
}

export async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, withAccountHeader(options));
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof payload === 'object' ? payload.error || payload.detail : payload;
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return payload;
}

export function createAnalysisJob(formData) {
  // 视频上传走独立子域名，绕过 Cloudflare 100MB 免费限制
  return request(`${UPLOAD_BASE}/api/analysis/jobs`, { method: 'POST', body: formData });
}

export function getAnalysisJob(jobId) {
  return request(`/api/analysis/jobs/${encodeURIComponent(jobId)}`);
}

export function getAnalysisResult(jobId) {
  return request(`/api/analysis/jobs/${encodeURIComponent(jobId)}/result`);
}

export function getArtifactUrl(jobId, filename) {
  return `${API_BASE}/api/analysis/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(filename)}`;
}

export function getReportUi(jobId) {
  return request(`/api/analysis/jobs/${encodeURIComponent(jobId)}/report-ui`);
}

export function getReportUiHistory() {
  return request('/api/analysis/report-ui/history');
}

export function triggerHardwareStart() {
  return request('/api/hardware/start', { method: 'POST' });
}

export function listUsers() {
  return request('/api/users');
}

export function createUser(payload) {
  return request('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function updateUser(userId, payload) {
  return request(`/api/users/${encodeURIComponent(userId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function listCustomFootworks() {
  return request('/api/custom-footworks');
}

export function listFootworkTypes() {
  return request('/api/v1/footwork-types');
}

export function createCustomFootwork(payload) {
  return request('/api/custom-footworks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function deleteCustomFootwork(itemId) {
  return request(`/api/custom-footworks/${encodeURIComponent(itemId)}`, { method: 'DELETE' });
}

// Auth
export function registerAccount(payload) {
  return request('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function loginAccount(payload) {
  return request('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function getAccountMe() {
  return request('/api/v1/auth/me');
}

export function changePassword(payload) {
  return request('/api/v1/auth/password', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
