import express from 'express';
import { fetchAndExtractPdfAttachments, fetchEmails, fetchResultCandidateEmails } from '../services/gmailService.js';
import { filterResultEmails } from '../services/resultEmailFilter.js';
import { analyzePDF } from '../services/pdfAnalysisBridge.js';
import { addEmailResult } from '../store/emailResultsStore.js';

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

emailRouter.get('/emails/results', async (req, res) => {
  try {
    const emails = await fetchResultCandidateEmails({ maxResults: req.query.maxResults || 30 });
    const filtered = filterResultEmails(emails);

    if (filtered.length === 0) {
      return res.json({ count: 0, emails: [], message: 'No result-related emails found.' });
    }

    return res.json({
      count: filtered.length,
      emails: filtered.map((email) => ({
        messageId: email.messageId,
        subject: email.subject,
        from: email.from,
        date: email.date,
        snippet: email.snippet,
        status: 'Result Email Found',
      })),
    });
  } catch (error) {
    const statusCode = error.statusCode || 500;
    return res.status(statusCode).json({ error: error.message || 'Failed to filter result emails' });
  }
});

emailRouter.post('/emails/analyze/:messageId', async (req, res) => {
  try {
    const { messageId } = req.params;
    const { email, pdfAttachments } = await fetchAndExtractPdfAttachments(messageId);

    if (!pdfAttachments.length) {
      return res.status(404).json({ error: 'No supported attachments found (PDF/Excel).' });
    }

    const analyses = [];
    for (const file of pdfAttachments) {
      const analysis = await analyzePDF(file);
      analyses.push({ filename: file.filename, analysis });
    }

    const stored = addEmailResult({
      emailId: messageId,
      subject: email.subject,
      sender: email.from,
      extractedData: analyses,
      timestamp: new Date().toISOString(),
    });

    return res.json({
      message: 'Email attachments analyzed successfully.',
      email: {
        messageId,
        subject: email.subject,
        from: email.from,
        date: email.date,
      },
      analyses,
      stored,
    });
  } catch (error) {
    const statusCode = error.statusCode || 500;
    return res.status(statusCode).json({ error: error.message || 'Failed to analyze email PDF' });
  }
});
