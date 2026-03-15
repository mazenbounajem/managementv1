from category import category_content
from session_storage import session_storage

def category_content_method():
    """Content method for category management that can be used in tabs"""
    user = session_storage.get('user')
    category_content(standalone=True, user=user)
