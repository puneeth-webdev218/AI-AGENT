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

export async function fetchEmails({ maxResults = 10, pageToken } = {}) {
  if (!tokenStore.hasTokens()) {
    const error = new Error('Not authenticated. Start OAuth at /auth/google');
    error.statusCode = 401;
    throw error;
  }

  const oauth2Client = createOAuthClient();
  oauth2Client.setCredentials(tokenStore.get());

  const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

  const listResponse = await gmail.users.messages.list({
    userId: 'me',
    maxResults: Number(maxResults) || 10,
    pageToken,
    includeSpamTrash: true,
  });

  const messageRefs = listResponse.data.messages || [];
  if (messageRefs.length === 0) {
    return {
      count: 0,
      nextPageToken: listResponse.data.nextPageToken || null,
      emails: [],
      message: 'No emails found in Gmail inbox.',
    };
  }

  const emails = [];
  for (const messageRef of messageRefs) {
    const message = await gmail.users.messages.get({
      userId: 'me',
      id: messageRef.id,
      format: 'metadata',
      metadataHeaders: ['Subject', 'From', 'Date'],
    });

    const headers = message.data.payload?.headers || [];
    const headerValue = (name) =>
      headers.find((item) => item.name?.toLowerCase() === name.toLowerCase())?.value || '';

    emails.push({
      subject: headerValue('Subject'),
      from: headerValue('From'),
      date: headerValue('Date'),
      snippet: message.data.snippet || '',
    });
  }

  return {
    count: emails.length,
    nextPageToken: listResponse.data.nextPageToken || null,
    emails,
  };
}
