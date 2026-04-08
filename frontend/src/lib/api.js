const inferredHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const defaultBaseUrl = `http://${inferredHost}:8000/api/v1`;
const baseUrl = import.meta.env.VITE_API_BASE_URL || defaultBaseUrl;
const gmailOAuthBaseUrl = import.meta.env.VITE_GMAIL_OAUTH_BASE_URL || `http://${inferredHost}:8001`;

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 180000;
  const operationLabel = options.operationLabel || 'Request';
  const { timeoutMs: _timeoutMs, operationLabel: _operationLabel, ...fetchOptions } = options;
  const fullUrl = `${baseUrl}${path}`;
  
  console.log(`🌐 [${options.method || 'GET'}] ${fullUrl}`);
  
  const timeoutId = setTimeout(() => {
    console.warn(`⏱️ REQUEST TIMEOUT after ${timeoutMs}ms`);
    controller.abort('request_timeout');
  }, timeoutMs);

  try {
    console.log('📡 Sending fetch request...');
    const response = await fetch(fullUrl, {
      ...fetchOptions,
      headers: {
        ...(fetchOptions.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(fetchOptions.headers || {}),
      },
      signal: controller.signal,
    });

    console.log(`📥 Got response: status=${response.status} (${response.statusText})`);
    
    const contentType = response.headers.get('content-type') || '';
    let payload;
    
    try {
      payload = contentType.includes('application/json') ? await response.json() : await response.text();
      console.log('✅ Parsed response payload');
    } catch (parseError) {
      console.error('❌ Failed to parse response:', parseError.message);
      throw new Error(`Failed to parse server response: ${parseError.message}`);
    }

    if (!response.ok) {
      const message = typeof payload === 'string' ? payload : payload.detail || payload.error || 'Request failed';
      console.error(`❌ HTTP ${response.status}:`, message);
      throw new Error(message);
    }

    console.log('✅ Response successful');
    return payload;
  } catch (error) {
    console.error('🔴 Fetch error:', error.message, error.name);
    
    if (error?.name === 'AbortError') {
      const msg = `${operationLabel} timed out. Please try again.`;
      console.error('⏱️ ABORT:', msg);
      throw new Error(msg);
    }
    
    if (error.message.includes('fetch')) {
      const msg = 'Cannot reach backend server. Make sure the API is running on ' + baseUrl;
      console.error('🚨 NETWORK:', msg);
      throw new Error(msg);
    }
    
    throw error;
  } finally {
    clearTimeout(timeoutId);
    console.log('🔚 Request cleanup complete');
  }
}

export function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  return request('/documents/upload', { method: 'POST', body: formData });
}

export function listDocuments() {
  return request('/documents');
}

export function getLatestDocument() {
  return request('/documents/latest');
}

export function listResults() {
  return request('/results');
}

export function syncEmail(payload) {
  return request('/emails/sync', { method: 'POST', body: JSON.stringify(payload) });
}

export function connectEmail(payload) {
  console.log('═══════════════════════════════════════════════');
  console.log('🔌 EMAIL CONNECT REQUEST START');
  console.log('═══════════════════════════════════════════════');
  console.log('Credentials:', { 
    host: payload.host, 
    port: payload.port,
    username: payload.username, 
    folder: payload.folder,
    use_ssl: payload.use_ssl 
  });
  
  return request('/email/connect', { 
    method: 'POST', 
    body: JSON.stringify(payload), 
    timeoutMs: 180000,
    operationLabel: 'Email connection'
  })
    .then(response => {
      console.log('═══════════════════════════════════════════════');
      console.log('✅ EMAIL CONNECT SUCCESS');
      console.log('═══════════════════════════════════════════════');
      console.log('Response:', response);
      return response;
    })
    .catch(error => {
      console.log('═══════════════════════════════════════════════');
      console.error('❌ EMAIL CONNECT FAILED');
      console.log('═══════════════════════════════════════════════');
      console.error('Error:', error.message);
      throw error;
    });
}

export function getEmailSyncJob(jobId) {
  return request(`/emails/jobs/${jobId}`);
}

export function listEmailLogs() {
  return request('/emails/logs');
}

export function beginGmailOAuth(redirectUri) {
  const params = new URLSearchParams();
  if (redirectUri) {
    params.set('redirect_uri', redirectUri);
  }
  const target = `${gmailOAuthBaseUrl}/auth/google${params.toString() ? `?${params.toString()}` : ''}`;
  window.location.href = target;
}

export async function getGmailConnectionStatus() {
  try {
    // The OAuth module intentionally exposes only /auth/google, /auth/google/callback, and /emails.
    // Use /emails as a practical connection probe.
    const response = await fetch(`${gmailOAuthBaseUrl}/emails?maxResults=1`);
    if (response.status === 401) {
      return { connected: false };
    }
    if (!response.ok) {
      throw new Error(`Status check failed with HTTP ${response.status}`);
    }
    return { connected: true };
  } catch {
    // Keep Email page usable even when OAuth backend is not running.
    return { connected: false };
  }
}

export async function fetchGmailEmails({ maxResults = 10, pageToken } = {}) {
  const params = new URLSearchParams();
  params.set('maxResults', String(maxResults));
  if (pageToken) {
    params.set('pageToken', pageToken);
  }

  const response = await fetch(`${gmailOAuthBaseUrl}/emails?${params.toString()}`);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || payload.error || 'Failed to fetch Gmail emails';
    throw new Error(message);
  }

  return payload;
}

export async function fetchResultEmails({ maxResults = 30 } = {}) {
  const params = new URLSearchParams();
  params.set('maxResults', String(maxResults));

  const response = await fetch(`${gmailOAuthBaseUrl}/emails/results?${params.toString()}`);
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || payload.error || 'Failed to fetch result emails';
    throw new Error(message);
  }

  return payload;
}

export async function analyzeResultEmail(messageId) {
  const response = await fetch(`${gmailOAuthBaseUrl}/emails/analyze/${encodeURIComponent(messageId)}`, {
    method: 'POST',
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || payload.error || 'Failed to analyze email';
    throw new Error(message);
  }

  return payload;
}

export function sendChatQuery(query) {
  return request('/chat/query', {
    method: 'POST',
    body: JSON.stringify({ query }),
    operationLabel: 'Chat request',
  });
}

export function healthCheck() {
  const normalizedBase = baseUrl.replace(/\/$/, '');
  const rootBase = normalizedBase.endsWith('/api/v1') ? normalizedBase.slice(0, -7) : normalizedBase;
  const candidates = [
    `${normalizedBase}/health`,
    `${rootBase}/api/v1/health`,
    `${rootBase}/health`,
  ];

  return (async () => {
    for (const url of candidates) {
      try {
        const response = await fetch(url);
        if (!response.ok) continue;
        const payload = await response.json();
        return payload;
      } catch {
        // Try the next health endpoint variant.
      }
    }
    throw new Error('Health check failed. Verify backend API URL and server status.');
  })();
}
