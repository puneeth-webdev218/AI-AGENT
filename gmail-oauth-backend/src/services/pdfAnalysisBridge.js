import { oauthConfig } from '../config/oauth.js';

const backendApiBaseUrl = process.env.BACKEND_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function analyzePDF(file) {
  console.log('[email] Analyzing PDF...');

  const formData = new FormData();
  const blob = new Blob([file.buffer], { type: 'application/pdf' });
  formData.append('file', blob, file.filename);

  const response = await fetch(`${backendApiBaseUrl}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || payload.error || 'PDF analysis failed';
    throw new Error(message);
  }

  // Existing upload pipeline marks the analyzed file as latest,
  // which keeps chatbot context aligned with recent analysis.
  console.log('[email] Chatbot context updated');
  return payload;
}
