import { google } from 'googleapis';
import { oauthConfig } from '../config/oauth.js';
import { tokenStore } from '../store/tokenStore.js';

export function createOAuthClient() {
  return new google.auth.OAuth2(
    oauthConfig.clientId,
    oauthConfig.clientSecret,
    oauthConfig.redirectUri,
  );
}

export function buildAuthUrl(redirectUri) {
  const oauth2Client = createOAuthClient();
  const statePayload = redirectUri ? { redirectUri } : null;
  const state = statePayload
    ? Buffer.from(JSON.stringify(statePayload), 'utf8').toString('base64url')
    : undefined;

  return oauth2Client.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: [oauthConfig.scope],
    state,
  });
}

export async function exchangeCodeForTokens(code) {
  const oauth2Client = createOAuthClient();
  const { tokens } = await oauth2Client.getToken(code);
  tokenStore.set(tokens);
  return tokenStore.get();
}

export function parseRedirectFromState(state) {
  if (!state) {
    return null;
  }

  try {
    const decoded = Buffer.from(state, 'base64url').toString('utf8');
    const parsed = JSON.parse(decoded);
    return parsed?.redirectUri || null;
  } catch {
    return null;
  }
}

export function getAuthenticatedGmailClient() {
  if (!tokenStore.hasTokens()) {
    const error = new Error('Not authenticated. Start OAuth at /auth/google');
    error.statusCode = 401;
    throw error;
  }

  const oauth2Client = createOAuthClient();
  oauth2Client.setCredentials(tokenStore.get());
  return google.gmail({ version: 'v1', auth: oauth2Client });
}

function headerValue(headers, name) {
  return headers.find((item) => item.name?.toLowerCase() === name.toLowerCase())?.value || '';
}

export async function getMessageMetadata(gmail, messageId) {
  const message = await gmail.users.messages.get({
    userId: 'me',
    id: messageId,
    format: 'metadata',
    metadataHeaders: ['Subject', 'From', 'Date'],
  });

  const headers = message.data.payload?.headers || [];
  return {
    id: messageId,
    messageId,
    subject: headerValue(headers, 'Subject'),
    from: headerValue(headers, 'From'),
    date: headerValue(headers, 'Date'),
    snippet: message.data.snippet || '',
  };
}

export async function fetchEmails({ maxResults = 10, pageToken } = {}) {
  const gmail = getAuthenticatedGmailClient();

  const listResponse = await gmail.users.messages.list({
    userId: 'me',
    maxResults: Number(maxResults) || 10,
    pageToken,
    includeSpamTrash: true,
  });

  const refs = listResponse.data.messages || [];
  if (refs.length === 0) {
    return {
      count: 0,
      nextPageToken: listResponse.data.nextPageToken || null,
      emails: [],
      message: 'No emails found in Gmail inbox.',
    };
  }

  const emails = [];
  for (const ref of refs) {
    emails.push(await getMessageMetadata(gmail, ref.id));
  }

  return {
    count: emails.length,
    nextPageToken: listResponse.data.nextPageToken || null,
    emails,
  };
}

export async function fetchResultCandidateEmails({ maxResults = 25 } = {}) {
  const gmail = getAuthenticatedGmailClient();
  const listResponse = await gmail.users.messages.list({
    userId: 'me',
    maxResults: Number(maxResults) || 25,
    includeSpamTrash: true,
  });

  const refs = listResponse.data.messages || [];
  const emails = [];
  for (const ref of refs) {
    emails.push(await getMessageMetadata(gmail, ref.id));
  }
  return emails;
}

function collectParts(part, output = []) {
  if (!part) {
    return output;
  }

  output.push(part);
  for (const child of part.parts || []) {
    collectParts(child, output);
  }
  return output;
}

function decodeBase64Url(data) {
  if (!data) {
    return Buffer.alloc(0);
  }
  const normalized = data.replace(/-/g, '+').replace(/_/g, '/');
  return Buffer.from(normalized, 'base64');
}

export async function extractSupportedAttachments(gmail, messageId) {
  console.log('[email] Fetching attachments...');

  const message = await gmail.users.messages.get({
    userId: 'me',
    id: messageId,
    format: 'full',
  });

  const parts = collectParts(message.data.payload, []);
  const supportedExtensions = ['.pdf', '.xlsx', '.xls'];
  const supportedParts = parts.filter((part) => {
    const filename = (part.filename || '').toLowerCase();
    return supportedExtensions.some(ext => filename.endsWith(ext));
  });

  const files = [];
  for (const part of supportedParts) {
    const attachmentId = part.body?.attachmentId;
    const filename = part.filename || `attachment-${messageId}`;

    let buffer;
    if (attachmentId) {
      const attachment = await gmail.users.messages.attachments.get({
        userId: 'me',
        messageId,
        id: attachmentId,
      });
      buffer = decodeBase64Url(attachment.data.data || '');
    } else {
      buffer = decodeBase64Url(part.body?.data || '');
    }

    if (buffer.length > 0) {
      const ext = filename.toLowerCase().endsWith('.pdf') ? 'PDF' : 'Excel';
      console.log(`[email] ${ext} attachment found: ${filename}`);
      files.push({ filename, buffer });
    }
  }

  return files;
}

export async function fetchAndExtractPdfAttachments(messageId) {
  const gmail = getAuthenticatedGmailClient();
  const email = await getMessageMetadata(gmail, messageId);
  const pdfAttachments = await extractSupportedAttachments(gmail, messageId);
  return { email, pdfAttachments };
}
