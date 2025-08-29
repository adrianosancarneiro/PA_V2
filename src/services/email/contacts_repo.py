"""Repository for managing email contacts."""
from typing import List, Tuple, Optional
import sys
import pathlib

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.database import get_conn


class ContactsRepo:
    """Repository for managing email contacts and recipients."""
    
    def search_contacts(self, query: str, limit: int = 10) -> List[Tuple[int, str, str]]:
        """
        Search contacts by name or email.
        
        Args:
            query: Search term (name or email fragment)
            limit: Maximum number of results
            
        Returns:
            List of tuples: (id, name, email)
        """
        with get_conn() as conn, conn.cursor() as cur:
            # Search in email_messages for frequent contacts
            search_term = f"%{query.lower()}%"
            cur.execute("""
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY email_count DESC) as id,
                    display_name as name,
                    from_email as email
                FROM (
                    SELECT 
                        COALESCE(from_display, split_part(from_email, '@', 1)) as display_name,
                        from_email,
                        COUNT(*) as email_count
                    FROM email_messages 
                    WHERE (LOWER(from_display) LIKE %s OR LOWER(from_email) LIKE %s)
                      AND from_email IS NOT NULL 
                      AND from_email != ''
                    GROUP BY from_display, from_email
                ) subq
                ORDER BY email_count DESC
                LIMIT %s
            """, (search_term, search_term, limit))
            
            return cur.fetchall()
    
    def get_frequent_contacts(self, limit: int = 20) -> List[Tuple[int, str, str]]:
        """Get most frequent email contacts."""
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY email_count DESC) as id,
                    display_name as name,
                    from_email as email
                FROM (
                    SELECT 
                        COALESCE(from_display, split_part(from_email, '@', 1)) as display_name,
                        from_email,
                        COUNT(*) as email_count
                    FROM email_messages 
                    WHERE from_email IS NOT NULL 
                      AND from_email != ''
                      AND from_email NOT LIKE '%noreply%'
                      AND from_email NOT LIKE '%no-reply%'
                    GROUP BY from_display, from_email
                    HAVING COUNT(*) > 1
                ) subq
                ORDER BY email_count DESC
                LIMIT %s
            """, (limit,))
            
            return cur.fetchall()
    
    def add_contact(self, name: str, email: str) -> int:
        """Add a new contact (for future use)."""
        # For now, just return a placeholder ID
        # In the future, you might want a dedicated contacts table
        return 1


# Convenience function to match the expected interface
def search_contacts(query: str, limit: int = 10) -> List[Tuple[int, str, str]]:
    """Search contacts by name or email."""
    repo = ContactsRepo()
    return repo.search_contacts(query, limit)
