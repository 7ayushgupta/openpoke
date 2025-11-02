#!/usr/bin/env python3
"""
Comprehensive Gmail/Composio integration test.
Tests connection, tools, fetching emails, and triggers.

Usage:
    python tests/test_gmail_full.py                  # Step-by-step guided flow (default)
    python tests/test_gmail_full.py --check          # Just check connection
    python tests/test_gmail_full.py --connect        # Connect Gmail if needed
    python tests/test_gmail_full.py --fetch-emails   # Fetch and display recent emails
    python tests/test_gmail_full.py --create-trigger # Test creating a trigger
    python tests/test_gmail_full.py --all            # Run all tests
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
from composio import Composio

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
AUTH_CONFIG_ID = os.getenv("COMPOSIO_GMAIL_AUTH_CONFIG_ID")
USER_ID = "7ayushgupta"  # User ID in your system

# Validate environment
if not COMPOSIO_API_KEY:
    print("❌ COMPOSIO_API_KEY not found in .env file")
    exit(1)

# Initialize Composio client
composio = Composio(api_key=COMPOSIO_API_KEY)

# ============================================================================
# 1. CONNECTION CHECK & SETUP
# ============================================================================

def check_connection():
    """Check if user has Gmail connected."""
    print("🔍 Checking Gmail connection...")
    print("=" * 60)
    print(f"[DEBUG] User ID: {USER_ID}")
    
    try:
        print(f"[DEBUG] Calling composio.connected_accounts.list()")
        print(f"[DEBUG]   user_ids=['{USER_ID}']")
        print(f"[DEBUG]   toolkit_slugs=['GMAIL']")
        
        accounts = composio.connected_accounts.list(
            user_ids=[USER_ID],
            toolkit_slugs=["GMAIL"]
        )
        
        print(f"[DEBUG] Response type: {type(accounts)}")
        
        # Fix: Composio API returns 'items', not 'data'
        data = getattr(accounts, "items", None) or (accounts.get("items") if isinstance(accounts, dict) else None)
        
        print(f"[DEBUG] Data extracted: {data is not None}")
        print(f"[DEBUG] Data type: {type(data)}")
        print(f"[DEBUG] Data length: {len(data) if data else 0}")
        
        if data:
            print(f"\n📋 Found {len(data)} Gmail account(s):\n")
            for idx, acc in enumerate(data):
                print(f"   --- Account #{idx + 1} ---")
                print(f"   [DEBUG] Account type: {type(acc)}")
                
                acc_id = getattr(acc, "id", None) or (acc.get("id") if isinstance(acc, dict) else None)
                acc_status = getattr(acc, "status", None) or (acc.get("status") if isinstance(acc, dict) else None)
                acc_user_id = getattr(acc, "user_id", None) or (acc.get("user_id") if isinstance(acc, dict) else None)
                
                print(f"   Account ID: {acc_id}")
                print(f"   Status: {acc_status}")
                print(f"   Status type: {type(acc_status)}")
                print(f"   User ID: {acc_user_id}")
                
                # Try to extract all fields
                if isinstance(acc, dict):
                    print(f"   [DEBUG] All fields: {list(acc.keys())}")
                    for key, value in acc.items():
                        if key not in ['id', 'status', 'user_id']:
                            print(f"   [DEBUG] {key}: {value}")
                
                # Check status
                valid_statuses = {"CONNECTED", "ACTIVE", "SUCCESS", "SUCCESSFUL", "COMPLETED"}
                print(f"\n   [DEBUG] Valid statuses: {valid_statuses}")
                
                if acc_status:
                    status_upper = str(acc_status).upper()
                    print(f"   [DEBUG] Status (uppercase): '{status_upper}'")
                    print(f"   [DEBUG] Is in valid list?: {status_upper in valid_statuses}")
                    
                    if status_upper in valid_statuses:
                        print(f"\n   ✅ This connection is ACTIVE and valid!")
                        print(f"   Returning: connected=True, account_id={acc_id}")
                        return True, acc_id
                    else:
                        print(f"\n   ⚠️  Connection exists but status '{acc_status}' is not in valid list")
                        print(f"   Need one of: {valid_statuses}")
                else:
                    print(f"   ⚠️  No status field found in account")
                
                print()  # Blank line between accounts
            
            print("[DEBUG] No accounts had valid status")
        else:
            print("⚠️  No data returned from Composio API")
            print(f"[DEBUG] Raw accounts object: {accounts}")
        
        print("\n❌ No active Gmail connection found")
        print("[DEBUG] Returning: connected=False, account_id=None")
        return False, None
        
    except Exception as e:
        print(f"❌ Error checking connection: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        import traceback
        print("[DEBUG] Full traceback:")
        traceback.print_exc()
        return False, None


def connect_gmail():
    """Initiate Gmail connection for the user."""
    print("🔗 Initiating Gmail connection...")
    print("=" * 60)
    print(f"[DEBUG] User ID: {USER_ID}")
    print(f"[DEBUG] Auth Config ID: {AUTH_CONFIG_ID}")
    
    if not AUTH_CONFIG_ID:
        print("❌ COMPOSIO_GMAIL_AUTH_CONFIG_ID not found in .env file")
        return False
    
    # Check if already connected
    print("\n[DEBUG] Checking if already connected...")
    is_connected, existing_acc_id = check_connection()
    if is_connected:
        print(f"\n✅ Gmail already connected! Account ID: {existing_acc_id}")
        return True
    
    try:
        # Create connection request
        print("\n[DEBUG] Creating connection request via composio.connected_accounts.initiate()")
        connection_request = composio.connected_accounts.initiate(
            user_id=USER_ID,
            auth_config_id=AUTH_CONFIG_ID,
            allow_multiple=True
        )
        
        print(f"[DEBUG] Connection request type: {type(connection_request)}")
        
        redirect_url = getattr(connection_request, "redirect_url", None) or getattr(connection_request, "redirectUrl", None)
        connection_id = getattr(connection_request, "id", None)
        
        print(f"[DEBUG] Redirect URL extracted: {redirect_url is not None}")
        print(f"[DEBUG] Connection ID extracted: {connection_id}")
        
        print("\n🔗 Please authorize Gmail by visiting this URL:")
        print("=" * 60)
        print(f"\n{redirect_url}\n")
        print("=" * 60)
        print(f"Connection Request ID: {connection_id}")
        print("\n[DEBUG] Calling wait_for_connection(timeout=300)...")
        print("Waiting for you to complete OAuth in your browser...")
        
        # Wait for connection
        connected_account = connection_request.wait_for_connection(timeout=300)
        
        print(f"\n[DEBUG] wait_for_connection() returned!")
        print(f"[DEBUG] Connected account type: {type(connected_account)}")
        
        acc_id = getattr(connected_account, "id", None) or (connected_account.get("id") if isinstance(connected_account, dict) else None)
        acc_status = getattr(connected_account, "status", None) or (connected_account.get("status") if isinstance(connected_account, dict) else None)
        
        print(f"[DEBUG] Connected account ID: {acc_id}")
        print(f"[DEBUG] Connected account status: {acc_status}")
        
        # Try to get all fields
        if isinstance(connected_account, dict):
            print(f"[DEBUG] All fields in connected_account: {list(connected_account.keys())}")
            for key, value in connected_account.items():
                print(f"[DEBUG]   {key}: {value}")
        elif hasattr(connected_account, '__dict__'):
            print(f"[DEBUG] Object attributes:")
            for key, value in vars(connected_account).items():
                print(f"[DEBUG]   {key}: {value}")
        
        print("\n✅ Gmail connected successfully!")
        print(f"   Account ID: {acc_id}")
        print(f"   Status: {acc_status}")
        
        # Add a small delay before re-checking
        print("\n[DEBUG] Waiting 2 seconds before verification...")
        import time
        time.sleep(2)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  Connection cancelled")
        return False
    except Exception as e:
        print(f"❌ Error connecting Gmail: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        import traceback
        print("[DEBUG] Full traceback:")
        traceback.print_exc()
        return False


# ============================================================================
# 2. GET GMAIL TOOLS
# ============================================================================

def get_gmail_tools():
    """Get Gmail tools for the user."""
    print("\n🔧 Getting Gmail Tools...")
    print("=" * 60)
    
    # Check connection first
    is_connected, account_id = check_connection()
    if not is_connected:
        print("❌ Gmail not connected. Cannot get tools.")
        return False, None
    
    try:
        # Get Gmail tools for the user
        print(f"Fetching tools for user: {USER_ID}")
        tools = composio.tools.get(
            user_id=USER_ID,
            tools=["GMAIL_FETCH_EMAILS", "GMAIL_SEND_EMAIL", "GMAIL_GET_PROFILE"]
        )
        
        print(f"✅ Successfully retrieved Gmail tools!")
        print(f"   User ID: {USER_ID}")
        print(f"   Account ID: {account_id}")
        print(f"   Available tools: GMAIL_FETCH_EMAILS, GMAIL_SEND_EMAIL, GMAIL_GET_PROFILE")
        
        return True, tools
        
    except Exception as e:
        print(f"❌ Error getting Gmail tools: {e}")
        return False, None


# ============================================================================
# 3. FETCH AND DISPLAY EMAILS
# ============================================================================

def fetch_emails(max_results=5):
    """Fetch and display recent emails from the user's inbox."""
    print(f"\n📬 Fetching Recent Emails (last {max_results})...")
    print("=" * 60)
    
    # Check connection first
    is_connected, account_id = check_connection()
    if not is_connected:
        print("❌ Gmail not connected. Cannot fetch emails.")
        return False
    
    try:
        # Execute Gmail tool to fetch emails
        print(f"Fetching emails for user: {USER_ID}")
        
        result = composio.client.tools.execute(
            "GMAIL_FETCH_EMAILS",
            user_id=USER_ID,
            arguments={
                "user_id": "me",
                "max_results": max_results,
                "label_ids": ["INBOX"]
            }
        )
        
        # Debug: Show the raw result
        print(f"[DEBUG] Result type: {type(result)}")
        print(f"[DEBUG] Result attributes: {dir(result) if hasattr(result, '__dir__') else 'N/A'}")
        if isinstance(result, dict):
            print(f"[DEBUG] Result keys: {list(result.keys())}")
            print(f"[DEBUG] Full result: {result}")
        elif hasattr(result, '__dict__'):
            print(f"[DEBUG] Result vars: {vars(result)}")

        # Parse the result - extract the actual messages
        emails = None
        if hasattr(result, "data"):
            data = result.data
            print(f"[DEBUG] data type: {type(data)}")
            
            # If data is a dict, get the messages from it
            if isinstance(data, dict):
                emails = data.get("messages")
                print(f"[DEBUG] Extracted messages from data dict")
            elif hasattr(data, "messages"):
                emails = data.messages
                print(f"[DEBUG] Extracted messages from data.messages")
            else:
                emails = data
                print(f"[DEBUG] Using data directly as emails")
        elif isinstance(result, dict):
            data = result.get("data")
            if data and isinstance(data, dict):
                emails = data.get("messages")
            else:
                emails = result.get("messages") or result.get("emails")

        if not emails:
            print("📭 No emails found or unable to parse response")
            print(f"   Raw result: {result}")
            return True

        # Convert to list if it's a generator or iterator
        emails_list = list(emails) if not isinstance(emails, list) else emails
        print(f"✅ Found {len(emails_list)} email(s):\n")

        for idx, email in enumerate(emails_list[:max_results]):
            print(f"[DEBUG] Email #{idx + 1} type: {type(email)}")
            print(f"[DEBUG] Email #{idx + 1} repr: {repr(email)[:200]}")

            # Try to parse if it's a string (might be JSON)
            if isinstance(email, str):
                try:
                    import json
                    email = json.loads(email)
                    print(f"[DEBUG] Successfully parsed email as JSON")
                except:
                    print(f"[DEBUG] Email is a plain string, not JSON")
                    print(f"[DEBUG] String value: {email[:200]}")
                    continue

            # Debug: Print all available fields
            if isinstance(email, dict):
                print(f"[DEBUG] Email is dict with keys: {list(email.keys())}")
                subject = email.get("subject", "No subject")
                sender = email.get("sender", email.get("from", "Unknown sender"))
                snippet = email.get("preview", {}).get("body", email.get("snippet", ""))
                date = email.get("messageTimestamp", email.get("date", ""))
            else:
                print(f"[DEBUG] Email is object with attributes: {dir(email)}")
                if hasattr(email, '__dict__'):
                    print(f"[DEBUG] Email object dict: {vars(email)}")
                subject = getattr(email, "subject", "No subject")
                sender = getattr(email, "sender", getattr(email, "from", "Unknown sender"))
                snippet = getattr(email, "snippet", "")
                date = getattr(email, "messageTimestamp", getattr(email, "date", ""))

            print(f"   Email #{idx + 1}")
            print(f"   From: {sender}")
            print(f"   Subject: {subject}")
            if date:
                print(f"   Date: {date}")
            if snippet:
                print(f"   Preview: {snippet[:100]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 4. TRIGGER CREATION TEST
# ============================================================================

def test_create_trigger():
    """Test creating a Gmail trigger for new messages."""
    print("\n⚡ Testing Trigger Creation...")
    print("=" * 60)
    
    # Check connection first
    is_connected, account_id = check_connection()
    if not is_connected:
        print("❌ Gmail not connected. Run with --connect first.")
        return False
    
    try:
        print(f"🔧 Creating trigger for user: {USER_ID}")
        
        # Create trigger for new Gmail messages
        trigger = composio.triggers.create(
            user_id=USER_ID,
            slug="GMAIL_NEW_GMAIL_MESSAGE",
            trigger_config={
                "labelIds": "INBOX",
                "userId": "me",
                "interval": 1  # Check every 1 minute
            }
        )
        
        trigger_id = getattr(trigger, "trigger_id", None) or (trigger.get("trigger_id") if isinstance(trigger, dict) else None)
        
        print(f"✅ Trigger created successfully!")
        print(f"   Trigger ID: {trigger_id}")
        print(f"   Slug: GMAIL_NEW_GMAIL_MESSAGE")
        print(f"   Config: Check INBOX every 1 minute")
        
        print("\n📝 To subscribe to this trigger in your app:")
        print(f"   subscription = composio.triggers.subscribe()")
        print(f"   @subscription.handle(trigger_id='{trigger_id}')")
        print(f"   def handle_gmail_event(data):")
        print(f"       print(data)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating trigger: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


# ============================================================================
# 5. LIST ALL TRIGGERS
# ============================================================================

def list_triggers():
    """List all triggers for the user."""
    print("\n📋 Listing Triggers...")
    print("=" * 60)
    
    try:
        # List all triggers for the user
        triggers = composio.triggers.list(user_id=USER_ID)
        
        # Handle response
        if hasattr(triggers, '__len__'):
            trigger_list = triggers
        elif hasattr(triggers, 'data'):
            trigger_list = triggers.data
        elif isinstance(triggers, dict):
            trigger_list = triggers.get('data', [])
        else:
            trigger_list = []
        
        if not trigger_list:
            print("No triggers found for this user")
            return True
        
        print(f"Found {len(trigger_list)} trigger(s):\n")
        for idx, trigger in enumerate(trigger_list):
            trigger_id = getattr(trigger, "trigger_id", None) or (trigger.get("trigger_id") if isinstance(trigger, dict) else None)
            slug = getattr(trigger, "slug", None) or (trigger.get("slug") if isinstance(trigger, dict) else None)
            status = getattr(trigger, "status", None) or (trigger.get("status") if isinstance(trigger, dict) else None)
            
            print(f"   Trigger #{idx + 1}:")
            print(f"     ID: {trigger_id}")
            print(f"     Slug: {slug}")
            print(f"     Status: {status}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing triggers: {e}")
        return False


# ============================================================================
# 6. STEP-BY-STEP GUIDED FLOW
# ============================================================================

def step_by_step_flow():
    """Guided step-by-step flow: connect → get tools → fetch emails."""
    print("🚀 Gmail/Composio Step-by-Step Test")
    print("=" * 60)
    print(f"User ID: {USER_ID}\n")
    
    # Step 1: Check/Connect
    print("STEP 1: Check Gmail Connection")
    print("-" * 60)
    is_connected, account_id = check_connection()
    
    if not is_connected:
        print("\n❌ Gmail is not connected. Let's connect it now...")
        print("\nPress ENTER to start OAuth connection, or Ctrl+C to cancel")
        try:
            input()
        except KeyboardInterrupt:
            print("\n\n⚠️  Cancelled. Run again when ready to connect.")
            return
        
        success = connect_gmail()
        if not success:
            print("\n❌ Failed to connect Gmail. Cannot continue.")
            return
        
        # Re-check connection
        is_connected, account_id = check_connection()
        if not is_connected:
            print("\n❌ Connection verification failed. Please try again.")
            return
    
    print("\n✅ Step 1 Complete: Gmail is connected!")
    input("\nPress ENTER to continue to Step 2...")
    
    # Step 2: Get Tools
    print("\n" + "=" * 60)
    print("STEP 2: Get Gmail Tools")
    print("-" * 60)
    success, tools = get_gmail_tools()
    
    if not success:
        print("\n❌ Failed to get Gmail tools. Cannot continue.")
        return
    
    print("\n✅ Step 2 Complete: Gmail tools retrieved!")
    input("\nPress ENTER to continue to Step 3...")
    
    # Step 3: Fetch Emails
    print("\n" + "=" * 60)
    print("STEP 3: Fetch Recent Emails")
    print("-" * 60)
    success = fetch_emails(max_results=5)
    
    if not success:
        print("\n❌ Failed to fetch emails.")
        return
    
    print("\n✅ Step 3 Complete: Emails fetched successfully!")
    
    # Optional: Create trigger
    print("\n" + "=" * 60)
    print("OPTIONAL: Create Gmail Trigger")
    print("-" * 60)
    print("Would you like to create a trigger to monitor new emails?")
    print("Press ENTER to create trigger, or Ctrl+C to skip")
    try:
        input()
        test_create_trigger()
    except KeyboardInterrupt:
        print("\n⚠️  Skipped trigger creation")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 All Steps Complete!")
    print("=" * 60)
    print("✅ Gmail is connected")
    print("✅ Tools are available")
    print("✅ Can fetch emails")
    print("\nYou can now use Gmail in your app!")


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Gmail/Composio integration test")
    parser.add_argument("--check", action="store_true", help="Check Gmail connection status")
    parser.add_argument("--connect", action="store_true", help="Connect Gmail if not connected")
    parser.add_argument("--get-tools", action="store_true", help="Get Gmail tools")
    parser.add_argument("--fetch-emails", action="store_true", help="Fetch and display recent emails")
    parser.add_argument("--create-trigger", action="store_true", help="Test creating a Gmail trigger")
    parser.add_argument("--list-triggers", action="store_true", help="List all triggers")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Default to step-by-step flow if no args
    if not any(vars(args).values()):
        step_by_step_flow()
        return
    
    print("🚀 Gmail/Composio Integration Test")
    print("=" * 60)
    print(f"User ID: {USER_ID}\n")
    
    results = []
    
    if args.check or args.all:
        is_connected, _ = check_connection()
        results.append(("Connection Check", is_connected))
        if not is_connected and not args.connect:
            print("\n💡 Run with --connect to set up Gmail connection")
    
    if args.connect:
        success = connect_gmail()
        results.append(("Gmail Connection", success))
    
    if args.get_tools or args.all:
        success, _ = get_gmail_tools()
        results.append(("Get Gmail Tools", success))
    
    if args.fetch_emails or args.all:
        success = fetch_emails()
        results.append(("Fetch Emails", success))
    
    if args.create_trigger or args.all:
        success = test_create_trigger()
        results.append(("Trigger Creation", success))
    
    if args.list_triggers or args.all:
        success = list_triggers()
        results.append(("List Triggers", success))
    
    # Summary
    if len(results) > 1:
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        passed = sum(1 for _, result in results if result)
        print(f"\n{passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()

