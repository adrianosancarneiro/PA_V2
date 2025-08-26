"""
Example email provider plugin for sending emails via a fake/dummy provider.
This serves as a template for creating new email provider plugins.
"""

class DummyProvider:
    """
    Dummy email provider for testing and demonstration purposes.
    In a real plugin, this would implement the actual sending logic.
    """
    
    @staticmethod
    def get_name():
        """Return the provider name"""
        return "dummy"
    
    @staticmethod
    def send_email(to_addr, subject, body, html_body=None, **kwargs):
        """
        Simulate sending an email (doesn't actually send anything)
        
        Args:
            to_addr (str): Recipient email address
            subject (str): Email subject
            body (str): Plain text email body
            html_body (str, optional): HTML email body
            **kwargs: Additional arguments for future extensions
            
        Returns:
            dict: Result with success status and message
        """
        print(f"DUMMY PROVIDER - Would send email:")
        print(f"  To: {to_addr}")
        print(f"  Subject: {subject}")
        print(f"  Body: {body[:50]}..." if len(body) > 50 else f"  Body: {body}")
        
        if html_body:
            print(f"  HTML: {html_body[:50]}..." if len(html_body) > 50 else f"  HTML: {html_body}")
            
        # You can access any custom parameters passed in kwargs
        for key, value in kwargs.items():
            print(f"  {key}: {value}")
            
        return {
            "success": True,
            "message": f"Dummy: Email simulation sent to {to_addr}",
            "provider": "dummy"
        }
