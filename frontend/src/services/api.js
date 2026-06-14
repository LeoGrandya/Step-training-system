/**
 * 运行时必需。前端调用 Flask /api 的 fetch 封装（分析任务、用户等）。
 */
const API_BASE = import.meta.env.VITE_ANALYSIS_API_BASE || '';
// 视频上传统一走同源请求。upload.magic-cloak.com 子域名原用于绕过 Cloudflare 100MB 限制，
// 但 Cloudflare 代理配置不稳定，实际极少有乒乓球视频超 100MB，同源足够。
const UPLOAD_BASE = '';
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
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    let message;
    if (typeof payload === 'object') {
      message = payload.error || payload.detail || `Request failed: ${response.status}`;
    } else {
      message = `Server error (${response.status})`;
      if (typeof payload === 'string' && payload.length > 0 && payload.length < 200) {
        message = payload.substring(0, 200);
      }
    }
    throw new Error(message);
  }
  return payload;
}

export function createAnalysisJob(formData, extraOptions = {}) {
  // 视频上传走独立子域名，绕过 Cloudflare 100MB 免费限制
  return request(`${UPLOAD_BASE}/api/analysis/jobs`, { method: 'POST', body: formData, ...extraOptions });
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
