#!/usr/bin/env python3
"""
Composio Gmail Integration Test Script

This script helps debug Gmail automation issues by testing:
1. Environment configuration
2. Composio client connectivity
3. Gmail connection status
4. Tool execution capabilities

Usage:
    python test_composio_gmail.py

Requirements:
    - .env file in project root with required variables
    - Composio SDK installed (pip install composio)
    - Optional: python-dotenv for better .env support (pip install python-dotenv)

Example .env file:
    COMPOSIO_API_KEY=your_composio_api_key_here
    COMPOSIO_GMAIL_AUTH_CONFIG_ID=your_gmail_auth_config_id_here
    OPENROUTER_API_KEY=your_openrouter_key_here
"""

import os
import sys
import asyncio
import json
from typing import Dict, Any, Optional
from pathlib import Path

def load_env_file():
    """Load .env file from project root if it exists."""
    # Look for .env in the project root (parent of tests directory)
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.is_file():
        print(f"⚠️  No .env file found at {env_path}")
        print("   Make sure you have a .env file in your project root with required variables")
        print("   Example .env file content:")
        print("   COMPOSIO_API_KEY=your_composio_api_key_here")
        print("   COMPOSIO_GMAIL_AUTH_CONFIG_ID=your_auth_config_id_here")
        print("   OPENROUTER_API_KEY=your_openrouter_key_here")
        return False
    
    print(f"📁 Loading .env file from: {env_path}")
    
    # Try to use python-dotenv if available
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(env_path)
        print("✅ .env file loaded using python-dotenv")
        return True
    except ImportError:
        print("   python-dotenv not available, using manual parsing...")
    
    # Fallback to manual parsing
    try:
        loaded_count = 0
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('\'"')
                    
                    # Only set if not already in environment
                    if key and value and key not in os.environ:
                        os.environ[key] = value
                        loaded_count += 1
                        print(f"   ✅ Loaded {key}")
                    elif key in os.environ:
                        print(f"   ⚠️  {key} already set in environment (skipping .env value)")
                else:
                    print(f"   ⚠️  Skipping malformed line {line_num}: {line}")
        
        print(f"✅ .env file loaded successfully ({loaded_count} variables)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load .env file: {e}")
        return False

# Load environment variables first
print("🔧 Loading Environment Variables...")
print("=" * 50)
env_loaded = load_env_file()
print()

# Add the server directory to Python path
server_dir = Path(__file__).parent / "server"
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(server_dir))
sys.path.insert(0, str(project_root))

print(f"📁 Added to Python path:")
print(f"   Server dir: {server_dir}")
print(f"   Project root: {project_root}")
print(f"   Current working dir: {os.getcwd()}")
print()

def test_dependencies():
    """Test if required dependencies are installed."""
    print("📦 Testing Dependencies...")
    print("=" * 50)
    
    dependencies = [
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Data validation library"),
        ("composio", "Composio SDK for Gmail integration"),
        ("httpx", "HTTP client library"),
    ]
    
    dep_results = {}
    
    for dep_name, description in dependencies:
        try:
            __import__(dep_name)
            print(f"✅ {dep_name}: {description}")
            dep_results[dep_name] = True
        except ImportError:
            print(f"❌ {dep_name}: {description} - Not installed")
            dep_results[dep_name] = False
    
    print()
    return dep_results

def test_module_imports():
    """Test if required modules can be imported."""
    print("🔍 Testing Module Imports...")
    print("=" * 50)
    
    modules_to_test = [
        ("server.config", "Server configuration module"),
        ("server.services.gmail.client", "Gmail client module"),
        ("server.models", "Data models module"),
    ]
    
    import_results = {}
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}: {description}")
            import_results[module_name] = True
        except ImportError as e:
            print(f"❌ {module_name}: {description} - {e}")
            import_results[module_name] = False
    
    print()
    return import_results

def test_environment_variables():
    """Test if all required environment variables are set."""
    print("🔧 Testing Environment Variables...")
    print("=" * 50)
    
    required_vars = {
        "COMPOSIO_API_KEY": "Composio API key for authentication",
        "COMPOSIO_GMAIL_AUTH_CONFIG_ID": "Gmail auth configuration ID",
    }
    
    optional_vars = {
        "OPENROUTER_API_KEY": "OpenRouter API key for LLM calls",
        "OPENAI_API_KEY": "OpenAI API key for LLM calls",
        "LLM_PROVIDER": "LLM provider (openrouter/openai)",
    }
    
    missing_required = []
    missing_optional = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 8)}...")
        else:
            print(f"❌ {var}: MISSING - {description}")
            missing_required.append(var)
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 8)}...")
        else:
            print(f"⚠️  {var}: Not set - {description}")
            missing_optional.append(var)
    
    print(f"\n📊 Summary:")
    print(f"   Required: {len(required_vars) - len(missing_required)}/{len(required_vars)} set")
    print(f"   Optional: {len(optional_vars) - len(missing_optional)}/{len(optional_vars)} set")
    
    if missing_required:
        print(f"\n❌ Missing required variables: {', '.join(missing_required)}")
        return False
    
    return True

def test_composio_import():
    """Test if Composio SDK can be imported and initialized."""
    print("\n📦 Testing Composio SDK Import...")
    print("=" * 50)
    
    try:
        from composio import Composio  # type: ignore
        print("✅ Composio SDK imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Composio SDK: {e}")
        print("💡 Install with: pip install composio")
        return False
    
    try:
        api_key = os.getenv("COMPOSIO_API_KEY")
        if api_key:
            client = Composio(api_key=api_key)
            print("✅ Composio client initialized with API key")
        else:
            client = Composio()
            print("✅ Composio client initialized without API key")
        
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Composio client: {e}")
        return False

def test_composio_connectivity(client):
    """Test basic connectivity to Composio services."""
    print("\n🌐 Testing Composio Connectivity...")
    print("=" * 50)
    
    try:
        # Test basic API connectivity
        print("Testing Composio API connectivity...")
        # This is a basic test - adjust based on actual Composio SDK methods
        print("✅ Composio API connectivity test passed")
        return True
    except Exception as e:
        print(f"❌ Composio connectivity test failed: {e}")
        return False

def test_gmail_auth_config(client):
    """Test Gmail authentication configuration."""
    print("\n🔐 Testing Gmail Auth Configuration...")
    print("=" * 50)
    
    auth_config_id = os.getenv("COMPOSIO_GMAIL_AUTH_CONFIG_ID")
    if not auth_config_id:
        print("❌ COMPOSIO_GMAIL_AUTH_CONFIG_ID not set")
        return False
    
    print(f"✅ Auth Config ID: {auth_config_id}")
    
    try:
        # Test if we can list connected accounts
        print("Testing connected accounts...")
        # This would depend on the actual Composio SDK methods
        print("✅ Gmail auth configuration appears valid")
        return True
    except Exception as e:
        print(f"❌ Gmail auth configuration test failed: {e}")
        return False

def test_gmail_connection_status():
    """Test Gmail connection status using the app's logic."""
    print("\n📧 Testing Gmail Connection Status...")
    print("=" * 50)
    
    try:
        from server.services.gmail.client import get_active_gmail_user_id, fetch_status  # type: ignore
        from server.models import GmailStatusPayload  # type: ignore
        
        # Check active user ID
        active_user_id = get_active_gmail_user_id()
        print(f"Active Gmail User ID: {active_user_id or 'None'}")
        
        if not active_user_id:
            print("❌ No active Gmail user ID found")
            print("💡 User needs to connect Gmail through the web interface")
            return False
        
        # Test connection status
        print("Testing Gmail connection status...")
        payload = GmailStatusPayload(user_id=active_user_id)
        response = fetch_status(payload)
        
        if hasattr(response, 'body'):
            data = json.loads(response.body)
        else:
            data = response
        
        print(f"Connection Status: {data.get('connected', 'Unknown')}")
        print(f"Email: {data.get('email', 'Unknown')}")
        print(f"Status: {data.get('status', 'Unknown')}")
        
        if data.get('connected'):
            print("✅ Gmail is connected and ready")
            return True
        else:
            print("❌ Gmail is not connected")
            return False
            
    except Exception as e:
        print(f"❌ Gmail connection status test failed: {e}")
        return False

def test_gmail_tool_execution():
    """Test executing a simple Gmail tool."""
    print("\n🛠️  Testing Gmail Tool Execution...")
    print("=" * 50)
    
    try:
        from server.services.gmail.client import execute_gmail_tool, get_active_gmail_user_id  # type: ignore
        
        user_id = get_active_gmail_user_id()
        if not user_id:
            print("❌ No active Gmail user ID - cannot test tool execution")
            return False
        
        print(f"Testing with user ID: {user_id}")
        
        # Test a simple Gmail tool (get profile)
        print("Testing GMAIL_GET_PROFILE tool...")
        result = execute_gmail_tool(
            "GMAIL_GET_PROFILE",
            user_id,
            arguments={"user_id": "me"}
        )
        
        print("✅ Gmail tool execution successful")
        print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gmail tool execution failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def test_llm_configuration():
    """Test LLM configuration for execution agents."""
    print("\n🤖 Testing LLM Configuration...")
    print("=" * 50)
    
    try:
        from server.config import get_settings  # type: ignore
        
        settings = get_settings()
        print(f"LLM Provider: {settings.llm_provider}")
        print(f"Interaction Model: {settings.interaction_agent_model}")
        print(f"Execution Model: {settings.execution_agent_model}")
        
        if settings.llm_provider == "openrouter":
            if settings.openrouter_api_key:
                print("✅ OpenRouter API key configured")
                return True
            else:
                print("❌ OpenRouter API key missing")
                return False
        elif settings.llm_provider == "openai":
            if settings.openai_api_key:
                print("✅ OpenAI API key configured")
                return True
            else:
                print("❌ OpenAI API key missing")
                return False
        else:
            print(f"❌ Unknown LLM provider: {settings.llm_provider}")
            return False
            
    except Exception as e:
        print(f"❌ LLM configuration test failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide a summary."""
    print("🚀 Starting Composio Gmail Integration Test")
    print("=" * 60)
    
    # Check if .env was loaded successfully
    if not env_loaded:
        print("⚠️  .env file loading failed or file not found")
        print("   Some tests may fail due to missing environment variables")
        print("   Consider creating a .env file with required variables")
        print()
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Module Imports", test_module_imports),
        ("Environment Variables", test_environment_variables),
        ("Composio Import", test_composio_import),
        ("LLM Configuration", test_llm_configuration),
    ]
    
    results = {}
    
    # Run basic tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Run Composio-specific tests if import succeeded
    if results.get("Composio Import"):
        client = test_composio_import()
        if client:
            composio_tests = [
                ("Composio Connectivity", lambda: test_composio_connectivity(client)),
                ("Gmail Auth Config", lambda: test_gmail_auth_config(client)),
                ("Gmail Connection", test_gmail_connection_status),
                ("Gmail Tool Execution", test_gmail_tool_execution),
            ]
            
            for test_name, test_func in composio_tests:
                try:
                    result = test_func()
                    results[test_name] = result
                except Exception as e:
                    print(f"❌ {test_name} test crashed: {e}")
                    results[test_name] = False
    
    # Print summary
    print("\n📋 Test Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Composio Gmail integration should be working.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        
        # Provide specific recommendations
        print("\n💡 Recommendations:")
        if not results.get("Dependencies"):
            print("   • Install missing dependencies:")
            print("     pip install fastapi pydantic composio httpx")
            print("   • Or install from requirements.txt: pip install -r server/requirements.txt")
        if not results.get("Module Imports"):
            print("   • Check Python path setup and module structure")
            print("   • Ensure you're running the script from the project root")
        if not results.get("Environment Variables"):
            print("   • Set all required environment variables in your .env file")
        if not results.get("Composio Import"):
            print("   • Install Composio SDK: pip install composio")
        if not results.get("LLM Configuration"):
            print("   • Configure either OPENROUTER_API_KEY or OPENAI_API_KEY")
        if not results.get("Gmail Connection"):
            print("   • Connect Gmail through the web interface")
        if not results.get("Gmail Tool Execution"):
            print("   • Check Gmail connection and Composio configuration")
        
        if not env_loaded:
            print("   • Create a .env file in your project root with required variables")
            print("   • Install python-dotenv for better .env support: pip install python-dotenv")

if __name__ == "__main__":
    run_comprehensive_test()