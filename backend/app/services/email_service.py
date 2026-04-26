import email
import imaplib
import logging
import socket
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.email_log import EmailLog
from app.models.result import Result
from app.models.student import Student
from app.services.document_processor import process_document
from app.services.students import upsert_student
from app.services.storage import build_storage_path, validate_filename
from app.services.validation import is_row_acceptable, validate_extracted_fields

logger = logging.getLogger(__name__)


@dataclass
class EmailAttachment:
    filename: str
    content_type: str | None
    payload: bytes


@dataclass
class EmailSummary:
    email_id: str
    message_id: str
    subject: str | None
    sender: str | None
    date: str | None
    has_attachment: bool
    processed_flag: bool = False


class EmailSyncError(Exception):
    pass


class EmailConnectionError(Exception):
    pass


class IMAPEmailClient:
    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.connection: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    def connect(self) -> None:
        print('Connecting to email...')
        self.connection = (
            imaplib.IMAP4_SSL(self.host, self.port, timeout=20)
            if self.use_ssl
            else imaplib.IMAP4(self.host, self.port, timeout=20)
        )
        try:
            self.connection.login(self.username, self.password)
            print('Login success')
        except imaplib.IMAP4.error as exc:
            print('Login failure')
            raise EmailConnectionError(f'Invalid credentials or IMAP not enabled: {exc}') from exc

    def disconnect(self) -> None:
        if self.connection is not None:
            try:
                self.connection.logout()
            finally:
                self.connection = None

    def select_folder(self, folder: str) -> None:
        """Select folder with comprehensive error handling and fallback attempts"""
        if self.connection is None:
            raise EmailSyncError('IMAP connection is not established.')
        
        print(f'📁 [select_folder] Attempting to select folder: {folder}')
        
        # Try 1: Direct folder name
        status, data = self.connection.select(folder)
        if status == 'OK':
            print(f'✅ [select_folder] Successfully selected {folder}')
            print(f'   Folder info: {data[0].decode() if data and isinstance(data[0], bytes) else data[0]}')
            return
        
        print(f'⚠️  [select_folder] Failed to select {folder} directly (status: {status})')
        
        # Try 2: With quotes
        quoted_folder = f'"{folder}"'
        print(f'🔄 [select_folder] Trying with quotes: {quoted_folder}')
        status, data = self.connection.select(quoted_folder)
        if status == 'OK':
            print(f'✅ [select_folder] Successfully selected {quoted_folder}')
            print(f'   Folder info: {data[0].decode() if data and isinstance(data[0], bytes) else data[0]}')
            return
        
        print(f'⚠️  [select_folder] Failed with quotes (status: {status})')
        
        # Try 3: List available folders and try to find match
        print('🔄 [select_folder] Listing available folders...')
        try:
            status, mailboxes = self.connection.list()
            if status == 'OK' and mailboxes:
                print(f'   Found {len(mailboxes)} folders:')
                for mailbox in mailboxes[:10]:  # Show first 10
                    print(f'     • {mailbox}')
                
                # Try to extract and use first INBOX-like folder
                for mailbox in mailboxes:
                    mailbox_str = mailbox.decode() if isinstance(mailbox, bytes) else mailbox
                    if 'INBOX' in mailbox_str.upper():
                        # Extract folder name from mailbox string
                        if '"' in mailbox_str:
                            parts = mailbox_str.split('"')
                            if len(parts) >= 3:
                                extracted_folder = parts[1]
                                print(f'🔄 [select_folder] Trying extracted folder: {extracted_folder}')
                                status, data = self.connection.select(extracted_folder)
                                if status == 'OK':
                                    print(f'✅ [select_folder] Successfully selected {extracted_folder}')
                                    return
        except Exception as e:
            print(f'⚠️  [select_folder] Error listing folders: {e}')
        
        # All attempts failed
        raise EmailConnectionError(
            f'Unable to open folder {folder}. '
            f'Tried: {folder}, "{folder}", and available INBOX variations. '
            f'Please check folder name and IMAP settings.'
        )

    def fetch_all_messages(self, folder: str) -> list[dict]:
        """
        Fetch full email messages with comprehensive debug logging.
        
        CRITICAL FIX: This implementation:
        1. Uses mail.search(None, "ALL") - the correct search query
        2. Properly handles message IDs (they're bytes, must split())
        3. Fetches complete RFC822 messages
        4. Uses email.message_from_bytes() for parsing
        5. Includes comprehensive debug output
        6. Sorts by date (latest first)
        """
        if self.connection is None:
            raise EmailSyncError('IMAP connection is not established.')
        
        print(f'\n📧 [fetch_all_messages] Starting full email fetch from folder: {folder}')
        print('=' * 70)
        
        # Step 1: Select folder
        print(f'\n1️⃣  [STEP 1] Selecting folder: {folder}')
        self.select_folder(folder)
        
        # Step 2: Search for ALL emails
        print(f'\n2️⃣  [STEP 2] Searching for all emails using search(None, "ALL")')
        status, data = self.connection.search(None, 'ALL')
        
        print(f'   Search status: {status}')
        
        if status != 'OK':
            raise EmailConnectionError(
                f'Unable to search email folder. Status: {status}. '
                f'Response: {data}'
            )
        
        # Step 3: Parse message IDs
        print(f'\n3️⃣  [STEP 3] Parsing message IDs from response')
        
        # CRITICAL: data[0] is bytes, must split()
        raw_ids = data[0].split() if data and data[0] else []
        
        print(f'   Total emails found: {len(raw_ids)}')
        if raw_ids:
            print(f'   First 5 email IDs: {[id.decode() if isinstance(id, bytes) else id for id in raw_ids[:5]]}')
        
        # Step 4: Handle empty case
        if not raw_ids:
            print(f'\n⚠️  No emails found in search!')
            print(f'   Total emails fetched: 0')
            return []
        
        # Step 5: Reverse order for latest-first
        print(f'\n4️⃣  [STEP 4] Reversing order to get latest emails first')
        ordered_ids = list(reversed(raw_ids))
        
        # Step 6: Fetch emails
        print(f'\n5️⃣  [STEP 5] Fetching full email messages')
        messages: list[dict] = []
        successful_fetches = 0
        failed_fetches = 0
        
        for idx, raw_id in enumerate(ordered_ids, 1):
            email_id_str = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            
            # Show progress every 10 emails
            if idx % 10 == 0:
                print(f'   Progress: {idx}/{len(ordered_ids)} emails...')
            
            try:
                # Fetch full RFC822 message
                status, fetched = self.connection.fetch(raw_id, '(RFC822)')
                
                if status != 'OK' or not fetched or not fetched[0]:
                    failed_fetches += 1
                    continue
                
                # Extract and parse raw message
                raw_message = fetched[0][1]
                message = email.message_from_bytes(raw_message)
                
                # Extract headers
                message_id = normalize_message_id(message.get('Message-ID')) or email_id_str
                subject = decode_header_value(message.get('Subject', '[No Subject]'))
                sender = decode_header_value(message.get('From', '[No From]'))
                date_value = message.get('Date', '')
                has_attachment = message_has_attachment(message)
                
                messages.append({
                    'email_id': email_id_str,
                    'message_id': message_id,
                    'subject': subject,
                    'sender': sender,
                    'date': date_value,
                    'has_attachment': has_attachment,
                    'message': message,
                })
                
                successful_fetches += 1
                
            except Exception as e:
                failed_fetches += 1
                print(f'   ⚠️  Error fetching email {email_id_str}: {e}')
                continue
        
        # Step 7: Sort by date
        print(f'\n6️⃣  [STEP 6] Sorting emails by date (latest first)')
        messages.sort(key=lambda item: message_datetime(item['message']), reverse=True)
        
        # Step 8: Summary
        print(f'\n7️⃣  [STEP 7] Fetch summary')
        print(f'   ✅ Successfully fetched: {successful_fetches}')
        print(f'   ❌ Failed fetches: {failed_fetches}')
        print(f'   📊 Total emails fetched: {len(messages)}')
        print('=' * 70)
        
        return messages

    def fetch_matching_messages(self, folder: str, subject_keywords: Iterable[str]) -> list[dict]:
        if self.connection is None:
            raise EmailSyncError('IMAP connection is not established.')
        self.select_folder(folder)
        status, data = self.connection.search(None, 'ALL')
        if status != 'OK':
            raise EmailConnectionError('Unable to search email folder.')

        raw_ids = data[0].split() if data and data[0] else []
        messages: list[dict] = []
        for raw_id in reversed(raw_ids):
            status, fetched = self.connection.fetch(raw_id, '(RFC822)')
            if status != 'OK' or not fetched or not fetched[0]:
                continue
            raw_message = fetched[0][1]
            message = email.message_from_bytes(raw_message)
            subject = decode_header_value(message.get('Subject', ''))
            if not subject_matches(subject, subject_keywords):
                continue
            messages.append({'message': message, 'raw_id': raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)})

        messages.sort(key=lambda item: message_datetime(item['message']), reverse=True)
        return messages

    def fetch_email_summaries(self, folder: str) -> list[dict]:
        """
        Fetch email summaries with comprehensive debug logging.
        
        CRITICAL FIX: This implementation:
        1. Selects folder with multiple fallback attempts
        2. Uses mail.search(None, "ALL") - the correct search query
        3. Properly handles message IDs (they're bytes, must split())
        4. Fetches header and structure for efficiency
        5. Includes comprehensive debug output
        6. Handles empty inbox case gracefully
        """
        if self.connection is None:
            raise EmailSyncError('IMAP connection is not established.')
        
        print(f'\n📧 [fetch_email_summaries] Starting email fetch from folder: {folder}')
        print('=' * 70)
        
        # Step 1: Select folder
        print(f'\n1️⃣  [STEP 1] Selecting folder: {folder}')
        self.select_folder(folder)
        
        # Step 2: Search for ALL emails
        print(f'\n2️⃣  [STEP 2] Searching for all emails using search(None, "ALL")')
        status, data = self.connection.search(None, 'ALL')
        
        print(f'   Search status: {status}')
        print(f'   Raw response: {data}')
        
        if status != 'OK':
            raise EmailConnectionError(
                f'Unable to search email folder. Status: {status}. '
                f'Response: {data}'
            )
        
        # Step 3: Parse message IDs
        print(f'\n3️⃣  [STEP 3] Parsing message IDs from response')
        
        # CRITICAL: data[0] is bytes, must split()
        raw_ids = data[0].split() if data and data[0] else []
        
        print(f'   Raw IDs (bytes): {raw_ids[:10]}...' if len(raw_ids) > 10 else f'   Raw IDs: {raw_ids}')
        print(f'   Total emails found: {len(raw_ids)}')
        
        # Step 4: Handle empty case
        if not raw_ids:
            print(f'\n⚠️  [STEP 4] No emails found in search!')
            print(f'   Possible causes:')
            print(f'     • Inbox is actually empty')
            print(f'     • Connected to wrong folder')
            print(f'     • IMAP search is not working')
            print(f'     • Folder requires different selection method')
            
            # Try to list folders for debugging
            try:
                status, mailboxes = self.connection.list()
                if status == 'OK' and mailboxes:
                    print(f'\n   Available folders ({len(mailboxes)}):')
                    for mbox in mailboxes[:15]:
                        mbox_str = mbox.decode() if isinstance(mbox, bytes) else mbox
                        print(f'     • {mbox_str}')
            except Exception as e:
                print(f'   Could not list folders: {e}')
            
            print(f'\n   📝 DEBUG TIP: Run IMAP_DIAGNOSTIC.py to diagnose the issue')
            print(f'   Total emails fetched: 0')
            return []
        
        # Step 5: Reverse order for latest-first
        print(f'\n4️⃣  [STEP 4] Reversing order to get latest emails first')
        ordered_ids = list(reversed(raw_ids))
        print(f'   First 5 IDs to fetch: {[id.decode() if isinstance(id, bytes) else id for id in ordered_ids[:5]]}')
        
        # Step 6: Fetch emails
        print(f'\n5️⃣  [STEP 5] Fetching email headers and structure')
        summaries: list[dict] = []
        successful_fetches = 0
        failed_fetches = 0
        
        for idx, raw_id in enumerate(ordered_ids, 1):
            email_id_str = raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)
            
            # Show progress every 10 emails
            if idx % 10 == 0:
                print(f'   Progress: {idx}/{len(ordered_ids)} emails...')
            
            try:
                # Fetch with BODY.PEEK to avoid marking as read
                status, header_data = self.connection.fetch(raw_id, '(BODY.PEEK[HEADER] BODYSTRUCTURE)')
                
                if status != 'OK' or not header_data:
                    failed_fetches += 1
                    continue
                
                # Parse header and bodystructure
                header_bytes = b''
                bodystructure_blob = ''
                
                for item in header_data:
                    if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
                        header_bytes = bytes(item[1])
                    elif isinstance(item, bytes):
                        bodystructure_blob += item.decode('utf-8', errors='ignore')
                    else:
                        bodystructure_blob += str(item)
                
                # Parse email headers
                message = email.message_from_bytes(header_bytes)
                message_id = normalize_message_id(message.get('Message-ID')) or email_id_str
                subject = decode_header_value(message.get('Subject', '[No Subject]'))
                sender = decode_header_value(message.get('From', '[No From]'))
                date_value = message.get('Date', '')
                has_attachment = detect_attachment_from_bodystructure(bodystructure_blob)
                
                summaries.append({
                    'email_id': email_id_str,
                    'message_id': message_id,
                    'subject': subject,
                    'sender': sender,
                    'date': date_value,
                    'has_attachment': has_attachment,
                })
                
                successful_fetches += 1
                
            except Exception as e:
                failed_fetches += 1
                print(f'   ⚠️  Error fetching email {email_id_str}: {e}')
                continue
        
        # Step 7: Summary
        print(f'\n6️⃣  [STEP 6] Fetch summary')
        print(f'   ✅ Successfully fetched: {successful_fetches}')
        print(f'   ❌ Failed fetches: {failed_fetches}')
        print(f'   📊 Total emails fetched: {len(summaries)}')
        print('=' * 70)
        
        return summaries


def normalize_message_id(message_id: str | None) -> str | None:
    if not message_id:
        return None
    cleaned = message_id.strip()
    if cleaned.startswith('<') and cleaned.endswith('>'):
        cleaned = cleaned[1:-1].strip()
    return cleaned or None


def decode_header_value(value: str) -> str:
    return str(email.header.make_header(email.header.decode_header(value)))


def message_has_attachment(message: Message) -> bool:
    for part in message.walk():
        content_disposition = part.get_content_disposition()
        filename = part.get_filename()
        if content_disposition == 'attachment' or filename:
            return True
    return False


def detect_attachment_from_bodystructure(bodystructure_blob: str) -> bool:
    lowered = bodystructure_blob.lower()
    return 'attachment' in lowered or 'filename=' in lowered or 'name=' in lowered


def subject_matches(subject: str, subject_keywords: Iterable[str]) -> bool:
    keywords = [keyword.strip().lower() for keyword in subject_keywords if keyword and keyword.strip()]
    if not keywords:
        return True
    lowered = subject.lower()
    return any(keyword in lowered for keyword in keywords)


def fetch_recent_messages(client: IMAPEmailClient, folder: str, limit: int = 25) -> list[dict]:
    if client.connection is None:
        raise EmailSyncError('IMAP connection is not established.')
    status, _ = client.connection.select(folder)
    if status != 'OK':
        raise EmailSyncError(f'Unable to open folder {folder}.')
    status, data = client.connection.search(None, 'ALL')
    if status != 'OK':
        raise EmailSyncError('Unable to search email folder.')

    raw_ids = data[0].split()
    selected_ids = raw_ids[-limit:]
    messages: list[dict] = []
    for raw_id in selected_ids:
        status, fetched = client.connection.fetch(raw_id, '(RFC822)')
        if status != 'OK' or not fetched or not fetched[0]:
            continue
        raw_message = fetched[0][1]
        message = email.message_from_bytes(raw_message)
        messages.append({'message': message, 'raw_id': raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)})
    messages.sort(key=lambda item: message_datetime(item['message']), reverse=True)
    return messages


def message_datetime(message: Message) -> datetime:
    raw_date = message.get('Date')
    if not raw_date:
        return datetime.min
    try:
        return parsedate_to_datetime(raw_date)
    except Exception:
        return datetime.min


def extract_attachments(message: Message) -> list[EmailAttachment]:
    attachments: list[EmailAttachment] = []
    for part in message.walk():
        content_disposition = part.get_content_disposition()
        filename = part.get_filename()
        if content_disposition != 'attachment' and not filename:
            continue
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        attachments.append(EmailAttachment(filename=filename, content_type=part.get_content_type(), payload=payload))
    return attachments


def fetch_and_store_email_index(session: Session, client: IMAPEmailClient, folder: str) -> list[EmailSummary]:
    fetched_messages = client.fetch_all_messages(folder)
    summaries: list[EmailSummary] = []

    for message_data in fetched_messages:
        message = message_data['message']
        email_id = message_data['email_id']
        message_id = message_data['message_id']
        subject = message_data['subject']
        sender = message_data['sender']
        received_at = message_data['date']
        has_attachment = message_data['has_attachment']

        existing_log = session.scalar(select(EmailLog).where(EmailLog.message_id == message_id))
        if existing_log is None:
            session.add(
                EmailLog(
                    email_id=email_id,
                    message_id=message_id,
                    subject=subject,
                    sender=sender,
                    received_at=received_at,
                    status='fetched',
                    processed_flag=False,
                )
            )
        summaries.append(
            EmailSummary(
                email_id=email_id,
                message_id=message_id,
                subject=subject,
                sender=sender,
                date=received_at,
                has_attachment=has_attachment,
                processed_flag=bool(existing_log.processed_flag) if existing_log is not None else False,
            )
        )

    session.commit()
    return summaries


def test_email_connection(host: str, port: int, username: str, password: str, use_ssl: bool) -> dict:
    """Test email connection - returns IMMEDIATELY after login, does NOT fetch emails"""
    print(f'🔌 [test_email_connection] Testing connection to {host}:{port}')
    print(f'🔑 [test_email_connection] Username: {username}')
    
    connection = None
    try:
        # Create connection with timeout
        print('📱 [test_email_connection] Creating IMAP connection...')
        if use_ssl:
            connection = imaplib.IMAP4_SSL(host, port, timeout=10)
        else:
            connection = imaplib.IMAP4(host, port, timeout=10)
        
        print('✅ [test_email_connection] Connection created')
        
        # Test login
        print('🔐 [test_email_connection] Attempting login...')
        connection.login(username, password)
        print('✅ [test_email_connection] Login successful')
        
        # Return immediately without fetching
        print('🔄 [test_email_connection] Logging out...')
        connection.logout()
        print('✅ [test_email_connection] Logged out successfully')
        
        return {'status': 'success', 'message': 'Email connection verified'}
        
    except imaplib.IMAP4.error as e:
        print(f'❌ [test_email_connection] IMAP error: {e}')
        return {'status': 'failed', 'message': f'Invalid credentials or IMAP not enabled: {e}'}
    except socket.timeout as e:
        print(f'❌ [test_email_connection] Connection timeout: {e}')
        return {'status': 'failed', 'message': f'Connection timeout: {e}'}
    except Exception as e:
        print(f'❌ [test_email_connection] Unexpected error: {e}')
        return {'status': 'failed', 'message': f'Connection error: {e}'}
    finally:
        if connection is not None:
            try:
                print('🔌 [test_email_connection] Closing connection...')
                connection.close()
            except Exception as e:
                print(f'⚠️ [test_email_connection] Error closing connection: {e}')


def fetch_and_store_emails(session: Session, host: str, port: int, username: str, password: str, use_ssl: bool, folder: str) -> list[EmailSummary]:
    """Fetch emails and store in database - run separately from connection test"""
    print(f'📧 [fetch_and_store_emails] Starting fetch from {host}:{port}')
    
    try:
        with IMAPEmailClient(host, port, username, password, use_ssl) as client:
            print(f'📨 [fetch_and_store_emails] Fetching email summaries from {folder}...')
            summaries = client.fetch_email_summaries(folder)
            print(f'✅ [fetch_and_store_emails] Fetched {len(summaries)} emails')
            
            stored: list[EmailSummary] = []
            for item in summaries:
                existing_log = session.scalar(select(EmailLog).where(EmailLog.message_id == item['message_id']))
                if existing_log is None:
                    session.add(
                        EmailLog(
                            email_id=item['email_id'],
                            message_id=item['message_id'],
                            subject=item['subject'],
                            sender=item['sender'],
                            received_at=item['date'],
                            status='fetched',
                            processed_flag=False,
                        )
                    )
                stored.append(
                    EmailSummary(
                        email_id=item['email_id'],
                        message_id=item['message_id'],
                        subject=item['subject'],
                        sender=item['sender'],
                        date=item['date'],
                        has_attachment=item['has_attachment'],
                        processed_flag=bool(existing_log.processed_flag) if existing_log is not None else False,
                    )
                )
            session.commit()
            print(f'✅ [fetch_and_store_emails] Stored {len(stored)} emails')
            return stored
    except Exception as e:
        print(f'❌ [fetch_and_store_emails] Error: {e}')
        raise


def sync_email_documents(session: Session, client: IMAPEmailClient, folder: str, subject_keywords: Iterable[str], storage_dir: Path) -> dict:
    fetched = 0
    processed_documents = 0
    skipped_duplicates = 0
    errors = 0
    matched_messages = 0
    fallback_used = False

    messages = client.fetch_matching_messages(folder, subject_keywords)
    matched_messages = len(messages)
    print('Fetched emails:', matched_messages)
    if not messages:
        fallback_used = True
        logger.info('No messages matched subject keywords; falling back to recent inbox messages with attachments')
        messages = fetch_recent_messages(client, folder, limit=25)
    for message_data in messages:
        message = message_data['message']
        message_id = str(message.get('Message-ID', '')).strip() or message_data.get('raw_id', '')
        subject = str(message.get('Subject', '')).strip()
        sender = str(message.get('From', '')).strip()
        print('Processing email:', subject)
        if not message_id:
            logger.warning('Skipping email without Message-ID')
            continue
        fetched += 1
        existing_log = session.scalar(select(EmailLog).where(EmailLog.message_id == message_id))
        if existing_log:
            skipped_duplicates += 1
            continue
        try:
            attachments = extract_attachments(message)
            if not attachments:
                session.add(EmailLog(email_id=message_id, message_id=message_id, subject=subject, sender=sender, received_at=str(message.get('Date', '')), status='no_attachments', processed_flag=False))
                session.commit()
                continue
            message_status = 'processed'
            for attachment in attachments:
                extension = Path(attachment.filename).suffix.lower()
                try:
                    validate_filename(attachment.filename)
                except Exception as exc:
                    logger.warning('Skipping unsupported email attachment %s: %s', attachment.filename, exc)
                    errors += 1
                    continue
                saved_path = build_storage_path(attachment.filename)
                saved_path.write_bytes(attachment.payload)
                document = Document(
                    filename=saved_path.name,
                    original_name=attachment.filename,
                    content_type=attachment.content_type,
                    file_type=extension.lstrip('.') or 'unknown',
                    file_path=str(saved_path),
                    source_type='email',
                    source_message_id=message_id,
                    status='pending',
                )
                session.add(document)
                session.flush()
                try:
                    text, extracted, processed_type, extracted_rows = process_document(saved_path)
                    print('EXTRACTED DATA:', asdict(extracted))
                    validation = validate_extracted_fields(extracted)
                    print('VALIDATED DATA:', {'status': validation.status, 'is_valid': validation.is_valid, 'messages': validation.messages})
                    print('INSERTING INTO DB:', asdict(extracted))

                    session.execute(update(Document).values(is_latest=False))
                    document.is_latest = True

                    document.extracted_text = text
                    document.file_type = processed_type
                    all_rows = extracted_rows or [extracted]
                    inserted = 0
                    total_rows = len(all_rows)
                    failed_rows = 0
                    skipped_rows = 0
                    for row in all_rows:
                        try:
                            row_validation = validate_extracted_fields(row)
                            if not is_row_acceptable(row):
                                skipped_rows += 1
                                continue
                            student = upsert_student(session, row.usn, row.student_name)
                            result = Result(
                                document_id=document.id,
                                student_id=student.id if student else None,
                                student_name=row.student_name,
                                usn=row.usn,
                                subject=row.subject or row.subject_name,
                                subject_code=row.subject_code,
                                subject_name=row.subject_name or row.subject,
                                grade=row.grade,
                                grade_points=row.grade_points,
                                sgpa=row.sgpa,
                                raw_text=text,
                                validation_status='validated' if row_validation.is_valid else row_validation.status,
                                validation_message='; '.join(row_validation.messages) if row_validation.messages else None,
                            )
                            session.add(result)
                            print('INSERTING:', {'name': row.student_name, 'usn': row.usn, 'subject_code': row.subject_code, 'subject_name': row.subject_name or row.subject, 'grade': row.grade, 'grade_points': row.grade_points, 'sgpa': row.sgpa})
                            inserted += 1
                        except Exception:
                            failed_rows += 1
                            continue
                    processed_ratio = (inserted / total_rows) if total_rows else 0.0
                    if inserted == 0:
                        document.status = 'failed'
                    elif processed_ratio > 0.8:
                        document.status = 'success'
                    else:
                        document.status = 'completed_with_errors'
                    print('Total rows:', total_rows)
                    print('Inserted:', inserted)
                    print('Failed:', failed_rows)
                    print('Skipped:', skipped_rows)
                    document.error_message = '; '.join(validation.messages) if validation.messages else None
                    processed_documents += 1
                    students_rows = session.execute(select(Student.id, Student.name, Student.usn)).all()
                    print('SELECT * FROM students:', [dict(row._mapping) for row in students_rows])
                    print('DB INSERT SUCCESS')
                except Exception as exc:
                    document.status = 'failed'
                    document.error_message = str(exc)
                    errors += 1
                    message_status = 'failed'
            session.add(EmailLog(email_id=message_id, message_id=message_id, subject=subject, sender=sender, received_at=str(message.get('Date', '')), status=message_status, processed_flag=message_status == 'processed'))
            session.commit()
        except Exception as exc:
            session.rollback()
            session.add(EmailLog(email_id=message_id, message_id=message_id, subject=subject, sender=sender, received_at=str(message.get('Date', '')), status='failed', processed_flag=False, error_message=str(exc)))
            session.commit()
            errors += 1
    return {
        'fetched': fetched,
        'processed_documents': processed_documents,
        'skipped_duplicates': skipped_duplicates,
        'errors': errors,
        'matched_messages': matched_messages,
        'fallback_used': fallback_used,
        'message': 'Email sync completed' if processed_documents or skipped_duplicates or errors else 'No processable emails were found',
    }
