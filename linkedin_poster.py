import os
from linkedin_api import Linkedin
from typing import Optional, Dict

class LinkedInPoster:
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize LinkedInPoster with optional credentials.
        
        Args:
            email (str, optional): LinkedIn email
            password (str, optional): LinkedIn password
        """
        self.email = email or os.getenv("LINKEDIN_EMAIL")
        self.password = password or os.getenv("LINKEDIN_PASSWORD")
        self.api = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with LinkedIn API.
        
        Returns:
            bool: True if authentication is successful
        """
        try:
            if not self.email or not self.password:
                raise Exception("LinkedIn credentials not provided")
            
            self.api = Linkedin(self.email, self.password)
            return True
        except Exception as e:
            raise Exception(f"LinkedIn authentication failed: {str(e)}")
    
    def post_content(self, content: str, visibility: str = "PUBLIC") -> Dict:
        """
        Post content to LinkedIn.
        
        Args:
            content (str): The content to post
            visibility (str): Post visibility (PUBLIC, CONNECTIONS)
            
        Returns:
            Dict: Response from LinkedIn API
        """
        try:
            if not self.api:
                self.authenticate()
            
            # Prepare the post data
            post_data = {
                "author": f"urn:li:person:{self.api.get_profile()['id']}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }
            
            # Post the content
            response = self.api.post_share(post_data)
            return response
            
        except Exception as e:
            raise Exception(f"Failed to post to LinkedIn: {str(e)}")

def post_to_linkedin(content: str, visibility: str = "PUBLIC") -> Dict:
    """
    Helper function to post content to LinkedIn.
    
    Args:
        content (str): The content to post
        visibility (str): Post visibility (PUBLIC, CONNECTIONS)
        
    Returns:
        Dict: Response from LinkedIn API
    """
    poster = LinkedInPoster()
    return poster.post_content(content, visibility) 