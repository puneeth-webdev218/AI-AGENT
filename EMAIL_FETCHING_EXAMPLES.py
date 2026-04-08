"""
COMPLETE WORKING EMAIL FETCHING EXAMPLE
========================================

This file shows the CORRECT way to implement IMAP email fetching.
Use this as a reference when implementing similar functionality.

✅ CORRECT PATTERNS
❌ INCORRECT PATTERNS
"""

import email
import imaplib
from email.utils import parsedate_to_datetime
from datetime import datetime
from typing import Optional, List

# ============================================================================
# EXAMPLE 1: BASIC CONNECTION & LOGIN
# ============================================================================

def example_1_basic_connection():
    """✅ CORRECT: Basic connection setup"""
    
    host = "imap.gmail.com"
    port = 993
    username = "user@gmail.com"
    password = "app-password"  # ✅ Use app password, not regular password
    
    # ✅ CORRECT: Use SSL with timeout
    connection = imaplib.IMAP4_SSL(host, port, timeout=20)
    
    # ✅ CORRECT: Try-except for login
    try:
        connection.login(username, password)
        print("✅ Login successful")
    except imaplib.IMAP4.error as e:
        print(f"❌ Login failed: {e}")
        return None
    
    return connection


# ❌ INCORRECT EXAMPLES
def example_1_incorrect():
    """❌ INCORRECT patterns to AVOID"""
    
    # ❌ NO TIMEOUT (will hang forever if connection fails)
    # connection = imaplib.IMAP4_SSL(host, port)
    
    # ❌ NO ERROR HANDLING (crashes if password wrong)
    # connection = imaplib.IMAP4_SSL(host, port, timeout=20)
    # connection.login(username, password)  # Can fail!
    
    # ❌ WRONG IMAP TYPE (unencrypted)
    # connection = imaplib.IMAP4(host, port)  # No SSL!
    
    pass


# ============================================================================
# EXAMPLE 2: CORRECT FOLDER SELECTION
# ============================================================================

def example_2_select_folder_correct(connection):
    """✅ CORRECT: Robust folder selection with fallbacks"""
    
    folder = "INBOX"
    
    # Try 1: Direct
    status, _ = connection.select(folder)
    if status == 'OK':
        print(f"✅ Selected {folder}")
        return True
    
    # Try 2: With quotes
    status, _ = connection.select(f'"{folder}"')
    if status == 'OK':
        print(f"✅ Selected \"{folder}\"")
        return True
    
    # Try 3: List and find variant
    status, mailboxes = connection.list()
    if status == 'OK':
        print("📋 Available folders:")
        for mbox in mailboxes:
            print(f"  • {mbox}")
    
    print(f"❌ Could not select {folder}")
    return False


def example_2_select_folder_incorrect(connection):
    """❌ INCORRECT: Single attempt, no fallback"""
    
    # ❌ This will fail if folder needs quotes or different naming
    status, _ = connection.select("INBOX")
    if status != 'OK':
        raise Exception("Failed to select folder!")  # ❌ No helpful info


# ============================================================================
# EXAMPLE 3: CORRECT EMAIL SEARCH
# ============================================================================

def example_3_search_correct(connection):
    """✅ CORRECT: Search for ALL emails"""
    
    # ✅ CRITICAL: This is the ONLY way to search for all emails
    status, data = connection.search(None, 'ALL')
    
    if status != 'OK':
        print(f"❌ Search failed: {status}")
        return []
    
    # ✅ CRITICAL: data[0] is bytes, must split()
    raw_ids = data[0].split() if data and data[0] else []
    
    print(f"✅ Found {len(raw_ids)} emails")
    print(f"Raw IDs (first 5): {raw_ids[:5]}")
    
    return raw_ids


def example_3_search_incorrect(connection):
    """❌ INCORRECT: Filtered searches (wrong!)"""
    
    # ❌ NO! This only gets UNREAD emails
    status, data = connection.search(None, 'UNSEEN')
    
    # ❌ NO! This filters by subject (incomplete search)
    status, data = connection.search(None, 'SUBJECT "Important"')
    
    # ❌ NO! This filters by date (incomplete search)
    status, data = connection.search(None, 'SINCE "2024-01-01"')
    
    # ❌ NO! Treating data[0] as string
    # raw_ids = data[0].decode().split()  # Wrong! decode() happens at wrong place
    
    # ✅ CORRECT: Get ALL then filter in Python if needed
    status, data = connection.search(None, 'ALL')
    raw_ids = data[0].split()
    return raw_ids


# ============================================================================
# EXAMPLE 4: PARSE MESSAGE IDs CORRECTLY
# ============================================================================

def example_4_parse_message_ids_correct(connection):
    """✅ CORRECT: Handle bytes message IDs"""
    
    status, data = connection.search(None, 'ALL')
    
    # ✅ CRITICAL: data[0] is bytes, split() gives bytes
    raw_ids = data[0].split() if data and data[0] else []
    
    print(f"✅ Total emails: {len(raw_ids)}")
    print(f"✅ First 3 IDs (bytes): {raw_ids[:3]}")
    
    # ✅ Reverse for latest first
    ordered_ids = list(reversed(raw_ids))
    print(f"✅ First 3 reversed: {ordered_ids[:3]}")
    
    # ✅ Each item is bytes
    for email_id in ordered_ids[:5]:
        email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
        print(f"  Email ID: {email_id_str}")
    
    return ordered_ids


def example_4_parse_message_ids_incorrect(connection):
    """❌ INCORRECT: Wrong message ID handling"""
    
    status, data = connection.search(None, 'ALL')
    
    # ❌ WRONG: decode() before split() - wrong structure
    # raw_ids = data[0].decode().split()
    
    # ❌ WRONG: Using forward order (oldest first)
    # ordered_ids = raw_ids  # No reversal!
    
    # ❌ WRONG: Assuming string type
    # for email_id in ordered_ids:
    #     mail.fetch(email_id, '(RFC822)')  # Works but inconsistent
    
    pass


# ============================================================================
# EXAMPLE 5: FETCH EMAILS CORRECTLY
# ============================================================================

def example_5_fetch_emails_correct(connection, email_ids: List[bytes]):
    """✅ CORRECT: Fetch full RFC822 messages"""
    
    emails = []
    
    for email_id in email_ids[:5]:  # First 5 for example
        email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
        
        # ✅ CORRECT: RFC822 gets full message
        status, msg_data = connection.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            print(f"⚠️  Failed to fetch {email_id_str}")
            continue
        
        if not msg_data or not msg_data[0]:
            print(f"⚠️  No data for {email_id_str}")
            continue
        
        try:
            # ✅ CRITICAL: msg_data[0][1] is raw bytes
            raw_message = msg_data[0][1]
            
            # ✅ CRITICAL: Use message_from_bytes(), NOT message_from_string()
            message = email.message_from_bytes(raw_message)
            
            emails.append({
                'id': email_id_str,
                'message': message,
                'subject': message.get('Subject', '[No Subject]'),
                'from': message.get('From', '[No From]'),
                'date': message.get('Date', '[No Date]'),
            })
            
            print(f"✅ Fetched: {message.get('Subject')}")
            
        except Exception as e:
            print(f"❌ Error parsing {email_id_str}: {e}")
            continue
    
    return emails


def example_5_fetch_emails_incorrect(connection, email_ids):
    """❌ INCORRECT: Wrong fetch patterns"""
    
    # ❌ WRONG: Using BODY instead of RFC822 (incomplete message)
    # status, msg_data = connection.fetch(email_id, '(BODY)')
    
    # ❌ WRONG: Using message_from_string() with bytes
    # msg = email.message_from_string(msg_data[0][1])
    
    # ❌ WRONG: Accessing wrong index
    # raw_message = msg_data[1][1]  # Wrong index!
    
    # ✅ CORRECT:
    # status, msg_data = connection.fetch(email_id, '(RFC822)')
    # raw_message = msg_data[0][1]
    # msg = email.message_from_bytes(raw_message)
    
    pass


# ============================================================================
# EXAMPLE 6: EXTRACT EMAIL INFORMATION
# ============================================================================

def example_6_extract_info_correct(message):
    """✅ CORRECT: Extract headers from message"""
    
    # ✅ CORRECT: Simple get() calls
    subject = message.get('Subject', '[No Subject]')
    sender = message.get('From', '[No From]')
    to = message.get('To', '[No To]')
    date_str = message.get('Date', '')
    message_id = message.get('Message-ID', '')
    
    print(f"Subject: {subject}")
    print(f"From: {sender}")
    print(f"To: {to}")
    print(f"Date: {date_str}")
    print(f"Message-ID: {message_id}")
    
    # ✅ CORRECT: Parse date if present
    if date_str:
        try:
            date_obj = parsedate_to_datetime(date_str)
            print(f"Parsed date: {date_obj}")
        except Exception as e:
            print(f"Could not parse date: {e}")
    
    return {
        'subject': subject,
        'from': sender,
        'to': to,
        'date': date_str,
        'message_id': message_id,
    }


def example_6_extract_info_incorrect(message):
    """❌ INCORRECT: Wrong extraction patterns"""
    
    # ❌ WRONG: Assuming headers always exist
    # subject = message['Subject']  # KeyError if missing!
    
    # ❌ WRONG: Not handling encoding
    # subject = str(message.get('Subject', ''))
    
    pass


# ============================================================================
# EXAMPLE 7: HANDLE ATTACHMENTS
# ============================================================================

def example_7_attachments_correct(message):
    """✅ CORRECT: Extract attachments"""
    
    attachments = []
    
    # ✅ CORRECT: walk() through all parts
    for part in message.walk():
        # Skip non-attachment content types
        if part.get_content_disposition() != 'attachment':
            continue
        
        filename = part.get_filename()
        if not filename:
            continue
        
        # ✅ Get decoded payload (bytes)
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        
        attachments.append({
            'filename': filename,
            'size': len(payload),
            'content_type': part.get_content_type(),
        })
        
        print(f"✅ Attachment: {filename} ({len(payload)} bytes)")
    
    return attachments


def example_7_attachments_incorrect(message):
    """❌ INCORRECT: Wrong attachment handling"""
    
    # ❌ WRONG: Not using walk()
    # for part in message.get_payload():  # Works but incomplete
    
    # ❌ WRONG: Not checking disposition
    # if 'attachment' in part.keys():
    
    # ❌ WRONG: Not decoding payload
    # payload = part.get_payload()  # Still base64!
    
    # ✅ CORRECT:
    # for part in message.walk():
    #     if part.get_content_disposition() == 'attachment':
    #         payload = part.get_payload(decode=True)
    
    pass


# ============================================================================
# EXAMPLE 8: COMPLETE FETCH CYCLE
# ============================================================================

def example_8_complete_cycle():
    """✅ CORRECT: Complete email fetching workflow"""
    
    # 1. Connect
    print("Step 1: Connecting...")
    conn = example_1_basic_connection()
    if not conn:
        return
    
    try:
        # 2. Select folder
        print("\nStep 2: Selecting folder...")
        if not example_2_select_folder_correct(conn):
            print("Using INBOX anyway...")
            conn.select("INBOX")
        
        # 3. Search for all emails
        print("\nStep 3: Searching for emails...")
        raw_ids = example_3_search_correct(conn)
        
        if not raw_ids:
            print("No emails found!")
            return
        
        # 4. Order (latest first)
        print("\nStep 4: Reversing order...")
        ordered_ids = list(reversed(raw_ids))
        
        # 5. Fetch emails
        print("\nStep 5: Fetching emails...")
        emails = example_5_fetch_emails_correct(conn, ordered_ids)
        
        # 6. Extract info
        print("\nStep 6: Extracting information...")
        for email_data in emails:
            print(f"\n--- Email ---")
            info = example_6_extract_info_correct(email_data['message'])
            attachments = example_7_attachments_correct(email_data['message'])
            
            if attachments:
                print(f"Attachments: {len(attachments)}")
                for att in attachments:
                    print(f"  • {att['filename']}")
        
        print(f"\n✅ COMPLETE: Fetched and processed {len(emails)} emails")
        
    finally:
        # 7. Disconnect
        print("\nStep 7: Closing connection...")
        conn.logout()


# ============================================================================
# EXAMPLE 9: ERROR HANDLING
# ============================================================================

def example_9_error_handling():
    """✅ CORRECT: Comprehensive error handling"""
    
    try:
        # Try to connect
        conn = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=20)
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP error: {e}")
        return
    except TimeoutError as e:
        print(f"❌ Connection timeout: {e}")
        return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    try:
        # Try to login
        conn.login("user@gmail.com", "app-password")
    except imaplib.IMAP4.error as e:
        print(f"❌ Login failed: {e}")
        print("Hint: Check credentials and IMAP settings")
        conn.close()
        return
    
    try:
        # Try to search
        status, data = conn.search(None, 'ALL')
        if status != 'OK':
            print(f"❌ Search failed: {status}")
            conn.close()
            return
        
        raw_ids = data[0].split() if data and data[0] else []
        print(f"✅ Found {len(raw_ids)} emails")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Always disconnect
        try:
            conn.logout()
        except:
            conn.close()


# ============================================================================
# QUICK REFERENCE
# ============================================================================

"""
✅ CORRECT PATTERNS:
  status, data = connection.search(None, 'ALL')
  raw_ids = data[0].split()
  for email_id in list(reversed(raw_ids)):
      status, msg_data = connection.fetch(email_id, '(RFC822)')
      msg = email.message_from_bytes(msg_data[0][1])
      subject = msg.get('Subject', '')

❌ INCORRECT PATTERNS:
  connection.search(None, 'UNSEEN')              ← Wrong search
  raw_ids = data[0].decode().split()            ← Wrong order
  for email_id in raw_ids:                      ← Wrong order
  connection.fetch(email_id, '(BODY)')          ← Wrong format
  email.message_from_string(raw_message)        ← Use bytes!

🔑 KEY RULES:
  1. Always use search(None, 'ALL')
  2. Always use RFC822 for full message
  3. Always use message_from_bytes()
  4. Always reverse for latest first
  5. Always handle errors and timeouts
"""

if __name__ == '__main__':
    print("Complete Email Fetching Examples")
    print("=" * 50)
    print("\nRun example functions individually:")
    print("  - example_1_basic_connection()")
    print("  - example_2_select_folder_correct(conn)")
    print("  - example_3_search_correct(conn)")
    print("  - example_4_parse_message_ids_correct(conn)")
    print("  - example_5_fetch_emails_correct(conn, ids)")
    print("  - example_6_extract_info_correct(msg)")
    print("  - example_7_attachments_correct(msg)")
    print("  - example_8_complete_cycle()")
    print("  - example_9_error_handling()")
