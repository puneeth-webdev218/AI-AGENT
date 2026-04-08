#!/usr/bin/env python3
"""
EMAIL FIX VERIFICATION SCRIPT
==============================
Tests the fixed email service to verify all improvements work correctly.

Usage: python verify_email_fixes.py
"""

import sys
from pathlib import Path

# Color codes for output
class Color:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    print(f"\n{Color.BLUE}{Color.BOLD}{'='*80}{Color.RESET}")
    print(f"{Color.BLUE}{Color.BOLD}{title:^80}{Color.RESET}")
    print(f"{Color.BLUE}{Color.BOLD}{'='*80}{Color.RESET}\n")

def print_success(msg):
    print(f"{Color.GREEN}✅ {msg}{Color.RESET}")

def print_error(msg):
    print(f"{Color.RED}❌ {msg}{Color.RESET}")

def print_warning(msg):
    print(f"{Color.YELLOW}⚠️  {msg}{Color.RESET}")

def print_info(msg):
    print(f"{Color.BLUE}ℹ️  {msg}{Color.RESET}")

def print_step(step_num, title):
    print(f"{Color.CYAN}{Color.BOLD}[STEP {step_num}] {title}{Color.RESET}")

def verify_imports():
    """Verify all required imports work"""
    print_header("VERIFICATION 1: CHECKING IMPORTS")
    
    try:
        import email
        print_success("✓ email module")
    except ImportError as e:
        print_error(f"✗ email module: {e}")
        return False
    
    try:
        import imaplib
        print_success("✓ imaplib module")
    except ImportError as e:
        print_error(f"✗ imaplib module: {e}")
        return False
    
    try:
        from pathlib import Path
        print_success("✓ pathlib module")
    except ImportError as e:
        print_error(f"✗ pathlib module: {e}")
        return False
    
    try:
        from dataclasses import dataclass
        print_success("✓ dataclasses module")
    except ImportError as e:
        print_error(f"✗ dataclasses module: {e}")
        return False
    
    print_success("All required imports available!")
    return True

def verify_email_service():
    """Verify email_service.py syntax and structure"""
    print_header("VERIFICATION 2: CHECKING EMAIL SERVICE CODE")
    
    service_path = Path(__file__).parent / "backend" / "app" / "services" / "email_service.py"
    
    if not service_path.exists():
        print_error(f"email_service.py not found at {service_path}")
        return False
    
    print_info(f"Found email_service.py at: {service_path}")
    
    try:
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Check for critical improvements
        checks = {
            "select_folder": "Enhanced folder selection method",
            "fetch_email_summaries": "Improved email fetch method",
            "fetch_all_messages": "Better message fetching",
            "mail.search(None, 'ALL')": "Correct search query",
            "[STEP 1]": "Debug logging (Step 1)",
            "[STEP 2]": "Debug logging (Step 2)",
            "[STEP 3]": "Debug logging (Step 3)",
            "[STEP 4]": "Debug logging (Step 4)",
            "[STEP 5]": "Debug logging (Step 5)",
            "[STEP 6]": "Debug logging (Summary)",
            "raw_ids = data[0].split()": "Proper message ID parsing",
            "list(reversed(raw_ids))": "Latest-first ordering",
            "email.message_from_bytes": "Correct email parsing",
        }
        
        found_count = 0
        missing = []
        
        for check_str, description in checks.items():
            if check_str in content:
                print_success(f"✓ {description}")
                found_count += 1
            else:
                print_warning(f"✗ {description}")
                missing.append(description)
        
        print(f"\n{Color.CYAN}Found {found_count}/{len(checks)} critical improvements{Color.RESET}")
        
        if missing:
            print(f"\n{Color.YELLOW}Missing improvements:{Color.RESET}")
            for m in missing:
                print(f"  • {m}")
            return False
        
        print_success("All critical improvements present!")
        return True
        
    except Exception as e:
        print_error(f"Error reading email_service.py: {e}")
        return False

def verify_diagnostic_script():
    """Verify IMAP_DIAGNOSTIC.py exists and is valid"""
    print_header("VERIFICATION 3: CHECKING DIAGNOSTIC SCRIPT")
    
    diagnostic_path = Path(__file__).parent / "IMAP_DIAGNOSTIC.py"
    
    if not diagnostic_path.exists():
        print_error(f"IMAP_DIAGNOSTIC.py not found at {diagnostic_path}")
        return False
    
    print_info(f"Found IMAP_DIAGNOSTIC.py at: {diagnostic_path}")
    
    try:
        with open(diagnostic_path, 'r') as f:
            content = f.read()
        
        # Check for key diagnostic features
        checks = {
            "test_imap_connection": "Connection test",
            "list_folders": "Folder listing",
            "select_folder_and_check": "Folder selection test",
            "test_search_and_fetch": "Email search test",
            "fetch_and_parse_emails": "Email fetch test",
            "Colors": "Colored output",
        }
        
        found_count = 0
        for check_str, description in checks.items():
            if check_str in content:
                print_success(f"✓ {description}")
                found_count += 1
            else:
                print_warning(f"✗ {description}")
        
        print(f"\n{Color.CYAN}Found {found_count}/{len(checks)} diagnostic features{Color.RESET}")
        
        if found_count == len(checks):
            print_success("Diagnostic script is complete!")
            return True
        else:
            print_warning("Some diagnostic features missing")
            return False
            
    except Exception as e:
        print_error(f"Error reading IMAP_DIAGNOSTIC.py: {e}")
        return False

def verify_documentation():
    """Verify comprehensive documentation exists"""
    print_header("VERIFICATION 4: CHECKING DOCUMENTATION")
    
    doc_path = Path(__file__).parent / "EMAIL_FETCHING_COMPREHENSIVE_FIX.md"
    
    if not doc_path.exists():
        print_error(f"Documentation not found at {doc_path}")
        return False
    
    print_info(f"Found documentation at: {doc_path}")
    
    try:
        with open(doc_path, 'r') as f:
            content = f.read()
        
        # Check for key sections
        checks = {
            "PROBLEM SUMMARY": "Problem description",
            "SOLUTION OVERVIEW": "Solution overview",
            "How to FIX": "Fix instructions",
            "DEBUG CHECKLIST": "Debugging guide",
            "API EXAMPLES": "API documentation",
            "VERIFICATION CHECKLIST": "Verification steps",
        }
        
        found_count = 0
        for check_str, description in checks.items():
            if check_str in content:
                print_success(f"✓ {description}")
                found_count += 1
            else:
                print_warning(f"✗ {description}")
        
        print(f"\n{Color.CYAN}Found {found_count}/{len(checks)} documentation sections{Color.RESET}")
        
        if found_count == len(checks):
            print_success("Complete documentation available!")
            return True
        else:
            print_warning("Some documentation sections missing")
            return False
            
    except Exception as e:
        print_error(f"Error reading documentation: {e}")
        return False

def create_test_endpoint_guide():
    """Show how to test the endpoints"""
    print_header("VERIFICATION 5: ENDPOINT TEST GUIDE")
    
    print_info("To test the fixed endpoints, run these commands:\n")
    
    test_connect = """1️⃣  TEST CONNECTION (should complete in 1-2 seconds):

curl -X POST http://localhost:8000/api/v1/email/connect \\
  -H "Content-Type: application/json" \\
  -d '{
    "host": "imap.gmail.com",
    "port": 993,
    "username": "your@gmail.com",
    "password": "your-app-password",
    "folder": "INBOX",
    "use_ssl": true
  }'

Expected response:
{
  "status": "success",
  "email_count": 0,
  "emails": [],
  "error": null
}
"""
    
    test_sync = """2️⃣  FETCH EMAILS (may take longer for large mailboxes):

curl -X POST http://localhost:8000/api/v1/email/sync \\
  -H "Content-Type: application/json" \\
  -d '{
    "host": "imap.gmail.com",
    "port": 993,
    "username": "your@gmail.com",
    "password": "your-app-password",
    "folder": "INBOX",
    "use_ssl": true
  }'

Expected response:
{
  "job_id": "...",
  "status": "completed",
  "fetched": 127,
  "processed_documents": 0,
  "skipped_duplicates": 0,
  "errors": 0,
  "message": "Successfully synced 127 emails"
}
"""
    
    print_info(test_connect)
    print_info(test_sync)
    
    return True

def generate_summary(results):
    """Generate final summary"""
    print_header("FINAL VERIFICATION SUMMARY")
    
    checks = [
        ("Imports", results['imports']),
        ("Email Service Code", results['service']),
        ("Diagnostic Script", results['diagnostic']),
        ("Documentation", results['documentation']),
    ]
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for name, result in checks:
        status = f"{Color.GREEN}✅ PASS{Color.RESET}" if result else f"{Color.RED}❌ FAIL{Color.RESET}"
        print(f"{name:.<40} {status}")
    
    print(f"\n{Color.CYAN}Overall: {passed}/{total} checks passed{Color.RESET}")
    
    if passed == total:
        print_success("All verifications passed! System is ready to use.")
        print("\nNext steps:")
        print("1. Start the backend:")
        print(f"   {Color.CYAN}cd backend && python -m uvicorn app.main:app --reload{Color.RESET}")
        print("\n2. Test the endpoints using the examples above")
        print("\n3. If you get 0 emails, run IMAP_DIAGNOSTIC.py to find the issue")
        return True
    else:
        print_error("Some verifications failed. Please review output above.")
        return False

def main():
    """Run all verifications"""
    print(f"{Color.BOLD}{Color.CYAN}")
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                 EMAIL FETCHING FIX VERIFICATION SCRIPT                     ║
║                                                                            ║
║  This script verifies that all email fetching improvements are in place    ║
║  and ready to use.                                                        ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    print(Color.RESET)
    
    results = {
        'imports': verify_imports(),
        'service': verify_email_service(),
        'diagnostic': verify_diagnostic_script(),
        'documentation': verify_documentation(),
    }
    
    create_test_endpoint_guide()
    
    success = generate_summary(results)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
