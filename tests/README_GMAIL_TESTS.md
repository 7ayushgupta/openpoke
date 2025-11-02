# Gmail/Composio Integration Tests

## 🚀 Quick Start (Step-by-Step)

Just run this command with no arguments for a **guided step-by-step flow**:

```bash
cd /Users/ayushgupta/Projects/playground/openpoke
source ~/anaconda3/bin/activate python311
python tests/test_gmail_full.py
```

### What happens:

1. **STEP 1**: Checks if Gmail is connected
   - If not connected → walks you through OAuth connection
   - If connected → confirms and continues

2. **STEP 2**: Gets Gmail tools for the user
   - Retrieves: `GMAIL_FETCH_EMAILS`, `GMAIL_SEND_EMAIL`, `GMAIL_GET_PROFILE`
   - These can be passed to AI agents

3. **STEP 3**: Fetches and displays your recent emails
   - Shows last 5 emails from your inbox
   - Displays: sender, subject, date, preview

4. **OPTIONAL**: Create a trigger to monitor new emails
   - Press ENTER to create, or Ctrl+C to skip

---

## Individual Commands

If you want to run specific steps:

### Check Connection Only
```bash
python tests/test_gmail_full.py --check
```

### Connect Gmail (OAuth Flow)
```bash
python tests/test_gmail_full.py --connect
```
Opens OAuth URL in your terminal - visit it to authorize.

### Get Gmail Tools
```bash
python tests/test_gmail_full.py --get-tools
```
Retrieves Gmail tools that can be used by AI agents.

### Fetch Recent Emails
```bash
python tests/test_gmail_full.py --fetch-emails
```
Fetches and displays your last 5 emails.

### Create Gmail Trigger
```bash
python tests/test_gmail_full.py --create-trigger
```
Creates a trigger to watch for new inbox messages.

### List All Triggers
```bash
python tests/test_gmail_full.py --list-triggers
```
Shows all active triggers for the user.

### Run All Tests
```bash
python tests/test_gmail_full.py --all
```
Runs all checks and tests in sequence.

---

## What This Tests

### ✅ Connection Management
- Check if user has Gmail connected in Composio
- Initiate OAuth connection if needed
- Verify connection status

### ✅ Gmail Tools (for AI Agents)
```python
# This is what the test does internally:
tools = composio.tools.get(
    user_id="7ayushgupta",
    tools=["GMAIL_FETCH_EMAILS", "GMAIL_SEND_EMAIL", "GMAIL_GET_PROFILE"]
)
# These tools can be passed to AI agents to perform actions
```

### ✅ Email Fetching
```python
# Fetch recent emails:
result = composio.client.tools.execute(
    "GMAIL_FETCH_EMAILS",
    user_id="7ayushgupta",
    arguments={
        "user_id": "me",
        "max_results": 5,
        "label_ids": ["INBOX"]
    }
)
# Displays: sender, subject, date, preview
```

### ✅ Trigger Creation (for monitoring)
```python
# Create trigger to watch inbox:
trigger = composio.triggers.create(
    user_id="7ayushgupta",
    slug="GMAIL_NEW_GMAIL_MESSAGE",
    trigger_config={
        "labelIds": "INBOX",
        "userId": "me",
        "interval": 1  # Check every 1 minute
    }
)
```

---

## Configuration

Edit `USER_ID` in the test file if needed:
```python
USER_ID = "7ayushgupta"  # Change to your user ID
```

Environment variables (`.env` file):
```bash
COMPOSIO_API_KEY=your_api_key
COMPOSIO_GMAIL_AUTH_CONFIG_ID=your_auth_config_id
```

---

## Using in Your App

The patterns in this test file can be directly used in your app:

### 1. Check Connection
```python
from server.services.gmail.client import get_all_connected_gmail_users
connected = get_all_connected_gmail_users()
```

### 2. Get Tools for AI Agent
```python
from composio import Composio
composio = Composio(api_key=settings.composio_api_key)

tools = composio.tools.get(
    user_id=user_id,
    tools=["GMAIL_FETCH_EMAILS", "GMAIL_SEND_EMAIL"]
)
# Pass tools to your execution agent
```

### 3. Fetch Emails
```python
result = composio.client.tools.execute(
    "GMAIL_FETCH_EMAILS",
    user_id=user_id,
    arguments={"user_id": "me", "max_results": 10}
)
```

### 4. Create Trigger
```python
trigger = composio.triggers.create(
    user_id=user_id,
    slug="GMAIL_NEW_GMAIL_MESSAGE",
    trigger_config={"labelIds": "INBOX", "interval": 1}
)
```

---

## Typical Workflow

```bash
# First time: Just run with no args for guided setup
python tests/test_gmail_full.py

# Later: Quick checks
python tests/test_gmail_full.py --fetch-emails
python tests/test_gmail_full.py --list-triggers
```

The step-by-step flow is perfect for first-time setup and testing!
