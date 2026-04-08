#!/usr/bin/env python3
"""
IMAP EMAIL DEBUGGING SCRIPT
============================
This script diagnoses IMAP connection and email fetching issues.

Usage: python IMAP_DIAGNOSTIC.py
"""

import imaplib
import email
import sys
from email.utils import parsedate_to_datetime

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(title):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}{title:^70}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def test_imap_connection():
    """Test basic IMAP connection"""
    print_header("STEP 1: TESTING IMAP CONNECTION")
    
    # Configure these with your credentials
    host = input("Enter Gmail IMAP host (default: imap.gmail.com): ").strip() or "imap.gmail.com"
    port = input("Enter IMAP port (default: 993): ").strip() or "993"
    port = int(port)
    username = input("Enter your Gmail address: ").strip()
    password = input("Enter your Gmail app password (not regular password!): ").strip()
    
    if not username or not password:
        print_error("Missing credentials!")
        return None
    
    print_info(f"Connecting to {host}:{port} as {username}...")
    
    try:
        connection = imaplib.IMAP4_SSL(host, port, timeout=10)
        print_success("IMAP4_SSL connection created")
    except Exception as e:
        print_error(f"Failed to create connection: {e}")
        return None
    
    try:
        connection.login(username, password)
        print_success(f"Login successful as {username}")
        return connection
    except imaplib.IMAP4.error as e:
        print_error(f"Login failed: {e}")
        print_warning("Make sure IMAP is enabled in Gmail settings")
        print_warning("Use an app-specific password, not your regular password")
        connection.close()
        return None

def list_folders(connection):
    """List all available IMAP folders"""
    print_header("STEP 2: LISTING AVAILABLE FOLDERS")
    
    try:
        status, mailboxes = connection.list()
        if status != 'OK':
            print_error(f"Failed to list folders: {status}")
            return []
        
        print_info(f"Found {len(mailboxes)} folders:\n")
        folders = []
        for mailbox in mailboxes:
            mailbox_str = mailbox.decode() if isinstance(mailbox, bytes) else mailbox
            print(f"  • {mailbox_str}")
            
            # Extract folder name (after the quotes)
            if mailbox_str:
                parts = mailbox_str.split('"')
                if len(parts) >= 3:
                    folder_name = parts[2]
                elif '/' in mailbox_str:
                    folder_name = mailbox_str.split('/')[-1].strip()
                else:
                    folder_name = mailbox_str.strip()
                folders.append(folder_name)
        
        return folders
    except Exception as e:
        print_error(f"Error listing folders: {e}")
        return []

def select_folder_and_check(connection, folder_name):
    """Select a folder and check for emails"""
    print_header(f"STEP 3: SELECTING FOLDER '{folder_name}'")
    
    try:
        status, data = connection.select(folder_name)
        if status != 'OK':
            print_error(f"Failed to select folder '{folder_name}': {status}")
            
            # Try with quotes
            print_info(f"Trying with quotes: '\"{folder_name}\"'...")
            try:
                status, data = connection.select(f'"{folder_name}"')
                if status != 'OK':
                    print_error(f"Still failed with quotes")
                    return False
                else:
                    print_success(f"Selected with quotes!")
            except Exception as e:
                print_error(f"Error with quotes: {e}")
                return False
        else:
            print_success(f"Selected folder '{folder_name}'")
        
        # Get folder info
        folder_info = data[0].decode() if isinstance(data[0], bytes) else data[0]
        print_info(f"Folder info: {folder_info}")
        
        return True
    except Exception as e:
        print_error(f"Error selecting folder: {e}")
        return False

def test_search_and_fetch(connection):
    """Test email search and fetching"""
    print_header("STEP 4: TESTING EMAIL SEARCH")
    
    try:
        # Test 1: Search with 'ALL'
        print_info("Testing: search(None, 'ALL')...")
        status, data = connection.search(None, 'ALL')
        
        if status != 'OK':
            print_error(f"Search failed: {status}")
            return False
        
        print_success(f"Search status: {status}")
        
        # Parse raw IDs
        raw_ids = data[0].split() if data and data[0] else []
        print_info(f"Raw message data: {data}")
        print_info(f"Raw IDs: {raw_ids}")
        print_success(f"Found {len(raw_ids)} emails in search result")
        
        if not raw_ids:
            print_warning("No emails found! This might mean:")
            print_warning("  • Inbox is actually empty")
            print_warning("  • Selected folder is wrong")
            print_warning("  • IMAP search has issues")
            
            # Try alternative search
            print_info("\nTrying alternative search: search(None, 'ALL')...")
            status2, data2 = connection.search(None, 'ALL')
            print_info(f"Alternative search result: status={status2}, data={data2}")
            
            return False
        
        return raw_ids
        
    except Exception as e:
        print_error(f"Error during search: {e}")
        return False

def fetch_and_parse_emails(connection, raw_ids, limit=5):
    """Fetch and parse first N emails"""
    print_header(f"STEP 5: FETCHING AND PARSING EMAILS (first {limit})")
    
    if not raw_ids:
        print_warning("No email IDs to fetch")
        return False
    
    # Limit the number of emails to fetch
    ids_to_fetch = list(reversed(raw_ids))[:limit]
    print_info(f"Fetching {len(ids_to_fetch)} emails (reversed order, latest first)...\n")
    
    successful_fetches = 0
    
    for idx, email_id in enumerate(ids_to_fetch, 1):
        email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
        print_info(f"[{idx}/{len(ids_to_fetch)}] Fetching email ID: {email_id_str}")
        
        try:
            status, fetched = connection.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                print_error(f"  Fetch failed: {status}")
                continue
            
            if not fetched or not fetched[0]:
                print_error(f"  No data returned")
                continue
            
            # Extract raw message
            raw_message = fetched[0][1]
            print_success(f"  Retrieved {len(raw_message)} bytes")
            
            # Parse email
            msg = email.message_from_bytes(raw_message)
            
            # Extract headers
            subject = msg.get('Subject', '[No Subject]')
            from_addr = msg.get('From', '[No From]')
            date = msg.get('Date', '[No Date]')
            
            print_info(f"  Subject: {subject}")
            print_info(f"  From: {from_addr}")
            print_info(f"  Date: {date}")
            
            # Check for attachments
            has_attachment = False
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    has_attachment = True
                    filename = part.get_filename()
                    print_info(f"  Attachment: {filename}")
            
            if not has_attachment:
                print_info(f"  No attachments")
            
            print_success(f"  ✓ Successfully parsed\n")
            successful_fetches += 1
            
        except Exception as e:
            print_error(f"  Error parsing: {e}\n")
            continue
    
    if successful_fetches > 0:
        print_success(f"Successfully fetched and parsed {successful_fetches}/{len(ids_to_fetch)} emails")
        return True
    else:
        print_error(f"Failed to fetch any emails")
        return False

def main():
    """Main diagnostic flow"""
    print_header("IMAP EMAIL DIAGNOSTIC TOOL")
    print("This tool will help diagnose IMAP connection and email fetching issues.\n")
    
    # Step 1: Connect
    connection = test_imap_connection()
    if not connection:
        print_error("Cannot proceed without connection")
        return False
    
    try:
        # Step 2: List folders
        folders = list_folders(connection)
        if not folders:
            print_error("No folders found")
            return False
        
        # Step 3: Select folder
        folder_choice = input(f"\nEnter folder to check (e.g., 'INBOX'): ").strip() or "INBOX"
        
        if not select_folder_and_check(connection, folder_choice):
            print_error("Cannot proceed without valid folder")
            return False
        
        # Step 4: Search
        raw_ids = test_search_and_fetch(connection)
        if not raw_ids:
            print_error("Search returned no results")
            return False
        
        # Step 5: Fetch and parse
        fetch_and_parse_emails(connection, raw_ids, limit=5)
        
        # Summary
        print_header("DIAGNOSTIC SUMMARY")
        print_success("✓ Connection successful")
        print_success("✓ Folder selection successful")
        print_success("✓ Email search successful")
        print_success(f"✓ Found {len(raw_ids)} total emails")
        
        return True
        
    finally:
        print_info("Closing connection...")
        connection.logout()
        print_success("Disconnected")

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
