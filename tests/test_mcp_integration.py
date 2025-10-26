#!/usr/bin/env python3
"""Test script for MCP integration with Zomato server."""

import asyncio
import json
from pathlib import Path

# Add the server directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent / "server"))

from mcp_client.models import MCPServerConfig
from mcp_client.registry import MCPRegistry


async def test_zomato_mcp_integration():
    """Test MCP integration with Zomato server."""
    print("🧪 Testing MCP Integration with Zomato Server")
    print("=" * 50)
    
    # Create MCP registry
    registry = MCPRegistry()
    
    # Configure Zomato server
    zomato_config = MCPServerConfig(
        name="zomato",
        url="https://mcp-server.zomato.com/mcp",
        auth_type=None,  # No auth required for testing
        enabled=True,
    )
    
    print(f"📡 Adding Zomato server: {zomato_config.url}")
    registry.add_server(zomato_config)
    
    # Initialize registry
    print("🔄 Initializing MCP registry...")
    await registry.initialize()
    
    if not registry.is_initialized():
        print("❌ Failed to initialize MCP registry")
        return False
    
    print("✅ MCP registry initialized successfully")
    
    # List available tools
    tools = registry.get_tools()
    print(f"\n🔧 Found {len(tools)} MCP tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # Test a simple tool call (if available)
    if tools:
        test_tool = tools[0]
        print(f"\n🧪 Testing tool call: {test_tool.name}")
        
        try:
            # Try to call the tool with minimal arguments
            result = await registry.call_tool(test_tool.name, {})
            
            if result.success:
                print(f"✅ Tool call successful: {result.data}")
            else:
                print(f"⚠️  Tool call failed: {result.error}")
                
        except Exception as exc:
            print(f"❌ Tool call error: {exc}")
    
    print("\n🎉 MCP integration test completed!")
    return True


async def test_mcp_client_direct():
    """Test MCP client directly with Zomato server."""
    print("\n🔬 Testing MCP Client Direct Connection")
    print("=" * 50)
    
    from mcp_client.client import MCPClient
    from mcp_client.models import MCPServerConfig, MCPToolCall
    
    config = MCPServerConfig(
        name="zomato",
        url="https://mcp-server.zomato.com/mcp",
        auth_type=None,
        enabled=True,
    )
    
    try:
        async with MCPClient(config) as client:
            print("📡 Testing connection...")
            if await client.test_connection():
                print("✅ Connection test successful")
            else:
                print("❌ Connection test failed")
                return False
            
            print("🔍 Discovering tools...")
            tools = await client.list_tools()
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Test a tool call if available
            if tools:
                test_tool = tools[0]
                print(f"\n🧪 Testing tool: {test_tool.name}")
                
                tool_call = MCPToolCall(
                    name=test_tool.name,
                    arguments={}
                )
                
                result = await client.call_tool(tool_call)
                if result.success:
                    print(f"✅ Tool call successful: {result.data}")
                else:
                    print(f"⚠️  Tool call failed: {result.error}")
    
    except Exception as exc:
        print(f"❌ Direct client test failed: {exc}")
        return False
    
    return True


async def main():
    """Run all MCP integration tests."""
    print("🚀 Starting MCP Integration Tests")
    print("=" * 60)
    
    # Test 1: Direct MCP client
    success1 = await test_mcp_client_direct()
    
    # Test 2: MCP registry
    success2 = await test_zomato_mcp_integration()
    
    print("\n📊 Test Results:")
    print(f"  Direct Client Test: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Registry Test:      {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All MCP integration tests passed!")
        print("\n💡 Next steps:")
        print("  1. Start the OpenPoke server")
        print("  2. Open the web interface")
        print("  3. Go to Settings > MCP Servers")
        print("  4. Add Zomato server: https://mcp-server.zomato.com/mcp")
        print("  5. Try asking: 'Find Italian restaurants near me'")
    else:
        print("\n❌ Some tests failed. Check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())
