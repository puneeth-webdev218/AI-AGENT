import fs from 'node:fs';
import path from 'node:path';

const dataFilePath = path.join(process.cwd(), 'src', 'store', 'email_results.json');

function readAll() {
  if (!fs.existsSync(dataFilePath)) {
    return [];
  }

  try {
    const content = fs.readFileSync(dataFilePath, 'utf8');
    return content ? JSON.parse(content) : [];
  } catch {
    return [];
  }
}

function writeAll(entries) {
  fs.writeFileSync(dataFilePath, JSON.stringify(entries, null, 2), 'utf8');
}

export function addEmailResult(entry) {
  const existing = readAll();
  existing.unshift(entry);
  writeAll(existing);
  console.log('[email] Stored in DB');
  return entry;
}

export function listEmailResults() {
  return readAll();
}
