# Email Integration Setup Guide

## ✅ What's Fixed

You reported that the Email Connect page was showing "Checking..." and not returning success or error. We've now:

1. ✅ **Fixed the connection timeout** - Increased timeout to 3 minutes (180 seconds) for slow IMAP connections
2. ✅ **Improved error handling** - All errors now display clearly with specific error messages
3. ✅ **Enhanced UI** - Connection status card now shows color-coded feedback:
   - 🟢 Green when connected
   - 🔴 Red when failed  
   - 🔵 Blue when checking
   - ⚪ Gray when not connected
4. ✅ **Added debug logging** - Open your browser console to see detailed logs of what's happening
5. ✅ **Fixed error messages** - Failed connections now show the exact error reason below the form

---

## 🔧 Setting Up Gmail with App Password

### Step 1: Enable 2-Step Verification
1. Go to https://myaccount.google.com/security
2. Click on "2-Step Verification"
3. Follow the setup steps

### Step 2: Get Your App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or your device)
3. Google will generate a 16-character app password
4. **Copy this password carefully** - you'll need it, and you can only see it once

### Step 3: Use App Password in Email Connect
- **Username**: Your full Gmail address (e.g., `youremail@gmail.com`)
- **Password**: The 16-character app password (paste it, don't type it manually)
- **IMAP Host**: `imap.gmail.com`
- **Port**: `993`
- **Folder**: `INBOX`
- **Use SSL**: ✅ Checked

### Example:
```
Username: john.doe@gmail.com
Password: abcd efgh ijkl mnop
Host: imap.gmail.com
Port: 993
Use SSL: ✅
```

---

## 🧪 Testing the Connection

### Quick Test
1. Navigate to "Email integration" page
2. Fill in your credentials
3. Click "Connect and fetch emails"
4. Wait for result (up to 3 minutes if mailbox is large)

### Expected Outcomes:

**✅ Success**
- Status card shows "✅ Connected"
- "Fetched emails" count shows a number > 0
- Email list appears below with Subject, From, Date, Attachment flag

**❌ Failed**
- Status card shows "❌ Failed"
- Error message displays below the form with reason:
  - "Invalid credentials or IMAP not enabled" → Check username/password
  - "Unable to open folder INBOX" → Folder doesn't exist (try "All Mail" instead)
  - "Email connection timed out" → IMAP server too slow or your network is slow

---

## 🐛 Troubleshooting

### "Invalid credentials or IMAP not enabled"
**Solution:**
- Double-check the app password (not your Google password!)
- Verify you enabled 2-Step Verification
- Go to https://myaccount.google.com/apppasswords and generate a new one
- Make sure you're using a fresh password (not a saved one)

### "Email connection timed out"
**Solution:**
- Check your internet connection
- Gmail might be slow - wait a moment and try again
- If you have 50,000+ emails, it might take a few minutes
- Try a smaller folder like "Drafts" to test

### "Unable to open folder INBOX"
**Solution:**
- Gmail might not have created the INBOX folder yet
- Try alternative folder names: "All Mail", "[Gmail]/All Mail", "INBOX"
- Or use a label name if you have custom labels

### Page shows "🔄 Checking..." but never updates
**Troubleshooting:**
1. **Open browser console** (F12 or Ctrl+Shift+I, click "Console" tab)
2. Look for log messages starting with 🔌, ✅, or ❌
3. Check if you see:
   - `🔌 Sending email connect request:` - Request was sent
   - `✅ Email connect response:` - Got response from backend
   - `❌ Email connect error:` - Error occurred

If you see no logs:
- The request might not be reaching the backend
- Check the "Network" tab in browser console
- Refresh the page and try again

---

## 🔍 How to Debug

### Browser Console (F12)
The system now logs everything to the console:

```
🔌 Sending email connect request: {host: 'imap.gmail.com', username: 'john@gmail.com', folder: 'INBOX'}
✅ Email connect response: {status: 'success', email_count: 42, emails: [...]}
```

Or on error:
```
❌ Email connect error: Invalid credentials or IMAP not enabled: [AUTHENTICATIONFAILED]
```

### Missing Logs?
1. Make sure the backend is running (check terminal)
2. Make sure the frontend is running (check terminal)  
3. Refresh the page (Ctrl+R)
4. Try again

---

## 📋 What Gets Synced

When you click "Connect and fetch emails", the system:
1. ✅ Connects to your IMAP mailbox
2. ✅ Fetches the last 50 emails (or all if fewer)
3. ✅ Stores metadata (subject, sender, date, attachment flag)
4. ✅ Shows you a preview list in the UI
5. ⏳ In the background, processes attachments (PDF, Excel) for data extraction

The actual document processing happens separately - the connect preview is just to verify your credentials work.

---

## ❓ Still Not Working?

Please share:
1. The exact error message from the "❌ Failed:" section
2. Browser console logs (F12 > Console tab, take a screenshot)
3. Your Gmail security settings (2FA enabled? App password visible?)
4. Terminal output from the backend (any error messages there?)

---

## ✨ Next Steps

Once connected:
- Email list will show preview of fetched messages
- Click "Refresh logs" to update the "Recent synced emails" list
- Documents from email attachments will be processed automatically
- Check the "Documents" page to see extracted results

Happy emailing! 📧
