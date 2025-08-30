#!/usr/bin/env python3
"""
Test the new intelligent LLM tool system
Shows how LLM can decide what tools to use instead of hardcoded keyword matching
"""
import sys
import os
sys.path.insert(0, '/home/mentorius/AI_Services/PA_V2/src')

from shared.llm_client import LLMClient

def test_intelligent_llm():
    print("🧠 Testing New Intelligent LLM Tool System")
    print("=" * 60)
    
    # Initialize LLM client
    llm = LLMClient()
    
    # Test cases that show how LLM decides what to do
    test_cases = [
        {
            "message": "how many emails do I have from Gmail this week?",
            "expected_behavior": "Should automatically route to database query tool"
        },
        {
            "message": "find emails from john@company.com about the project",
            "expected_behavior": "Should automatically route to local email search tool"
        },
        {
            "message": "show me email details for ID 12345",
            "expected_behavior": "Should automatically route to get email details tool"
        },
        {
            "message": "what's the weather like today?",
            "expected_behavior": "Should respond normally as general conversation"
        },
        {
            "message": "search directly in Gmail for recent messages",
            "expected_behavior": "Should route to provider search tool"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test['message']}")
        print(f"Expected: {test['expected_behavior']}")
        print("-" * 40)
        
        try:
            # Send message to LLM
            response = llm.chat(test['message'], user_id="test_user")
            print(f"📤 LLM Response: {response[:200]}{'...' if len(response) > 200 else ''}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    print("\n💡 Key Improvements:")
    print("• LLM now decides what tools to use based on context")
    print("• No more hardcoded keyword matching")
    print("• Supports both local database search AND provider direct search")
    print("• Intelligent tool inference even without explicit tool calls")
    print("• Better conversation flow and memory")

if __name__ == "__main__":
    test_intelligent_llm()
