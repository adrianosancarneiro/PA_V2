#!/usr/bin/env python3
"""
Test script for database query capabilities
Demonstrates what the LLM can now do with direct database access
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.database.database_query_service import DatabaseQueryService

def test_database_queries():
    """Test various database queries that the LLM can now perform"""
    
    # Set database credentials
    os.environ['POSTGRES_USER'] = 'postgres_user'
    os.environ['POSTGRES_PASSWORD'] = 'postgres_pass'
    
    db_service = DatabaseQueryService()
    
    print("🔍 Testing Database Query Capabilities for LLM")
    print("=" * 60)
    
    # Test queries that users might ask
    test_requests = [
        "How many emails do I have from the last week?",
        "Show me email statistics by provider",
        "Who are my top 5 senders?", 
        "How many unread emails do I have?",
        "Show me recent emails from Gmail",
        "What's my daily email breakdown for the last 7 days?"
    ]
    
    for request in test_requests:
        print(f"\n📝 Request: '{request}'")
        print("-" * 40)
        
        try:
            # Parse natural language to query
            query_name, params = db_service.natural_language_to_query(request)
            print(f"🔧 Parsed to: {query_name} with params {params}")
            
            # Execute query
            result = db_service.execute_query(query_name, params)
            
            # Format for display
            formatted = db_service.format_results_for_llm(result)
            print(f"📊 Result:\n{formatted}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Database integration complete!")
    print(f"The LLM can now:")
    print(f"  - Query email statistics and counts")
    print(f"  - Analyze data by provider, sender, date")
    print(f"  - Search emails with complex filters")
    print(f"  - Provide data-driven insights")

if __name__ == "__main__":
    test_database_queries()
