const RESULT_KEYWORDS = ['result', 'scorecard', 'marks', 'grade', 'exam', 'report'];

export function filterResultEmails(emails) {
  console.log('[email] Filtering result emails...');
  const filtered = (emails || []).filter((email) => {
    const haystack = `${email.subject || ''} ${email.snippet || ''}`.toLowerCase();
    return RESULT_KEYWORDS.some((keyword) => haystack.includes(keyword));
  });
  console.log(`[email] Result emails found: ${filtered.length}`);
  return filtered;
}
