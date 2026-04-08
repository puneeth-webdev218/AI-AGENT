import express from 'express';
import { fetchEmails } from '../services/gmailService.js';

export const emailRouter = express.Router();

emailRouter.get('/emails', async (req, res) => {
  try {
    console.log('[email] Fetch started');
    const payload = await fetchEmails({
      maxResults: req.query.maxResults,
      pageToken: req.query.pageToken,
    });
    console.log(`[email] Emails fetched count: ${payload.count}`);
    return res.json(payload);
  } catch (error) {
    const statusCode = error.statusCode || 500;
    return res.status(statusCode).json({ error: error.message || 'Failed to fetch emails' });
  }
});
