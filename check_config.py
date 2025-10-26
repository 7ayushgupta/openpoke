#!/usr/bin/env python3
"""Configuration diagnostic script for OpenPoke."""

import os
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent / "server"))

def check_config():
    """Check OpenPoke configuration and provide diagnostic information."""
    print("🔍 OpenPoke Configuration Diagnostic")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
        try:
            with open(env_file) as f:
                content = f.read()
                print(f"📄 .env file size: {len(content)} characters")
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
    else:
        print("❌ .env file not found")
        print("💡 Create a .env file with your API keys")
    
    # Check environment variables
    print("\n🔧 Environment Variables:")
    llm_provider = os.getenv("LLM_PROVIDER", "openrouter")
    print(f"   LLM_PROVIDER: {llm_provider}")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if llm_provider.lower() == "openai":
        if openai_key:
            print(f"   OPENAI_API_KEY: ✅ Set (length: {len(openai_key)})")
            if not openai_key.startswith("sk-"):
                print("   ⚠️  Warning: OpenAI key should start with 'sk-'")
        else:
            print("   OPENAI_API_KEY: ❌ Not set")
    else:
        if openrouter_key:
            print(f"   OPENROUTER_API_KEY: ✅ Set (length: {len(openrouter_key)})")
        else:
            print("   OPENROUTER_API_KEY: ❌ Not set")
    
    # Try to import and check settings
    print("\n⚙️  Settings Check:")
    try:
        from server.config import get_settings
        settings = get_settings()
        
        print(f"   App Name: {settings.app_name}")
        print(f"   App Version: {settings.app_version}")
        print(f"   LLM Provider: {settings.llm_provider}")
        print(f"   Interaction Model: {settings.interaction_agent_model}")
        print(f"   Execution Model: {settings.execution_agent_model}")
        
        # Check API keys in settings
        if settings.llm_provider.lower() == "openai":
            if settings.openai_api_key:
                print(f"   OpenAI API Key: ✅ Configured")
            else:
                print(f"   OpenAI API Key: ❌ Not configured")
        else:
            if settings.openrouter_api_key:
                print(f"   OpenRouter API Key: ✅ Configured")
            else:
                print(f"   OpenRouter API Key: ❌ Not configured")
                
    except Exception as e:
        print(f"   ❌ Error loading settings: {e}")
    
    # Test LLM client
    print("\n🤖 LLM Client Test:")
    try:
        from server.llm_client.client import _get_provider, _log_provider_initialization
        provider = _get_provider()
        print(f"   Provider: {provider}")
        
        # This will show the detailed configuration
        _log_provider_initialization()
        
    except Exception as e:
        print(f"   ❌ Error testing LLM client: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Quick Fixes:")
    
    if llm_provider.lower() == "openai" and not openai_key:
        print("   • Set OPENAI_API_KEY in your .env file")
        print("   • Or switch to OpenRouter: LLM_PROVIDER=openrouter")
    elif llm_provider.lower() == "openrouter" and not openrouter_key:
        print("   • Set OPENROUTER_API_KEY in your .env file")
        print("   • Or switch to OpenAI: LLM_PROVIDER=openai")
    else:
        print("   • Configuration looks good!")
        print("   • Try restarting the server to see detailed logs")

if __name__ == "__main__":
    check_config()
