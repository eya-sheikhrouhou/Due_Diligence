import re
import urllib.parse

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def is_valid_url(url):
    """Validate URL format."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

def sanitize_input(text):
    """Sanitize input to prevent invalid characters."""
    return re.sub(r'[^\w\-]', '', text.replace('..', '').replace('/', '').replace('\\', ''))