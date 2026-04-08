import express from 'express';
import {
  buildAuthUrl,
  exchangeCodeForTokens,
  parseRedirectFromState,
} from '../services/gmailService.js';

export const googleAuthRouter = express.Router();

googleAuthRouter.get('/auth/google', (req, res) => {
  const redirectUri = req.query.redirect_uri;
  console.log('[email] OAuth start');
  const authUrl = buildAuthUrl(redirectUri);
  res.redirect(authUrl);
});

googleAuthRouter.get('/auth/google/callback', async (req, res) => {
  const { code, state } = req.query;
  if (!code) {
    return res.status(400).json({ error: 'Missing OAuth code' });
  }

  try {
    const tokens = await exchangeCodeForTokens(code);
    console.log('[email] Token received');
    const redirectUri = parseRedirectFromState(state) || 'http://localhost:5173/email';
    const separator = redirectUri.includes('?') ? '&' : '?';
    return res.redirect(`${redirectUri}${separator}gmail_connected=true`);
  } catch (error) {
    return res.status(500).json({ error: error.message || 'Failed to exchange OAuth code' });
  }
});
