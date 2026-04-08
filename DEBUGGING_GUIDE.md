# 🧪 Email Connection Debugging - Step by Step

## ⚠️ Current Issue
You're seeing "🔄 Checking..." but connection never completes or shows error.

## 🔧 What to Do Now

### Step 1: Open Browser Console
1. Press **F12** (or Ctrl+Shift+I on Windows)
2. Click the **Console** tab
3. You should see the enhanced debug logs with emojis

### Step 2: Try to Connect
1. Fill in email form with test credentials
2. Click "Connect and fetch emails"
3. **Watch the console** for logs (should see many 🌐, 📡, 🔴, etc.)

### Step 3: What to Look For in Console

**Expected successful flow:**
```
═══════════════════════════════════════════════
🧪 EMAIL FORM SUBMISSION
═══════════════════════════════════════════════
Form data: {host: 'imap.gmail.com', username: 'test@...', folder: 'INBOX'}
📤 Calling connectEmail API...
═══════════════════════════════════════════════
🔌 EMAIL CONNECT REQUEST START
═══════════════════════════════════════════════
Credentials: {host: 'imap.gmail.com', port: 993, ...}
🌐 [POST] http://127.0.0.1:8000/api/v1/email/connect
📡 Sending fetch request...
📥 Got response: status=200 (OK)
✅ Parsed response payload
✅ Response successful
📨 API returned payload: {status: 'failed', error: '...'}
❌ CONNECTION FAILED: Invalid credentials...
═══════════════════════════════════════════════
✅ EMAIL CONNECT SUCCESS
═══════════════════════════════════════════════
```

### Step 4: If Stuck on "🔄 Checking..."

**Look for these signs in console:**

1. **If you DON'T see any logs:**
   - Problem: Frontend code not running
   - Fix: Hard refresh the page (Ctrl+Shift+R)
   - Then try again

2. **If you see logs up to "📡 Sending fetch request..." but nothing after:**
   - Problem: Backend not responding
   - Fix: Check if backend is running
   - Run: `Get-NetTCPConnection -LocalPort 8000 -State Listen`
   - Should show port 8000 listening
   - If not, restart backend

3. **If you see "🌐" and "📡" but then "⏱️ REQUEST TIMEOUT":**
   - Problem: Backend taking too long
   - Check backend for errors
   - Try simpler test (just check credentials, not full sync)

4. **If you see "🚨 NETWORK:" error:**
   - Problem: Can't reach backend
   - Backend URL is wrong
   - Fix: Ensure backend is running on http://127.0.0.1:8000

### Step 5: Direct Backend Test (In Console)

Paste this code in your browser console (F12 > Console):

```javascript
// Quick test
fetch('http://127.0.0.1:8000/api/v1/email/connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    host: 'imap.gmail.com',
    port: 993,
    username: 'test@test.com',
    password: 'wrong',
    folder: 'INBOX',
    use_ssl: true
  })
}).then(r => {
  console.log('Status:', r.status);
  return r.json();
}).then(d => {
  console.log('Response:', d);
}).catch(e => {
  console.error('Error:', e.message);
});
```

Press Enter and **immediately watch the console** for response.

### Step 6: Check Server Status

**In PowerShell, check if both servers are running:**

```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in @(8000, 5173) }
```

Should show TWO entries:
- Port 8000 (Backend)
- Port 5173 (Frontend)

If either is missing, restart that server.

---

## 🔄 Restart Servers (If Needed)

### Kill All Processes
```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in @(8000, 5173) } | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
```

### Start Backend
```powershell
Set-Location "C:\Users\puneeth nagaraj\Downloads\AI AGENT\AI-AGENT\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Wait for:** `Application startup complete`

### Start Frontend (In New Terminal)
```powershell
Set-Location "C:\Users\puneeth nagaraj\Downloads\AI AGENT\AI-AGENT\frontend"
npm run dev -- --host 0.0.0.0 --port 5173
```

**Wait for:** `VITE ... ready in XXX ms`

---

## 📊 What the Logs Tell You

| Log Message | Meaning | Action |
|------------|---------|--------|
| `📤 Calling connectEmail API...` | Request being sent | ✅ Normal |
| `📡 Sending fetch request...` | Frontend contacting backend | ✅ Normal |
| `📥 Got response: status=200` | Backend responded | ✅ Normal |
| `✅ Parsed response payload` | Response is valid JSON | ✅ Normal |
| `❌ CONNECTION FAILED: ...` | IMAP auth failed (expected for test creds) | ✅ Normal |
| `⏱️ REQUEST TIMEOUT` | Backend took >180s to respond | ❌ Backend issue |
| `🚨 NETWORK: Cannot reach backend` | Can't connect to backend | ❌ Backend not running |
| No logs appear | Code not executing | ❌ Hard refresh needed |

---

## 🆘 Still Stuck?

**Collect this info and share:**

1. **Screenshot of console logs** (F12, Console tab)
2. **Terminal output** where you started backend
3. **Count seconds** - How long does it stay on "Checking..."?
4. **Error message** - Is there a red error box below the form?

This will help identify exactly where it's hanging.

---

## 💡 Quick Checklist

- [ ] Backend running on port 8000?
- [ ] Frontend running on port 5173?
- [ ] F12 console open?
- [ ] Console shows detailed logs (with emojis)?
- [ ] Form submission shows "Checking..." state?
- [ ] Check console for where logs stop

Once you run through this and share what you see in the console, I can pinpoint the exact issue!
