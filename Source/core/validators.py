from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os
from PIL import Image
from django.core.validators import URLValidator
from urllib.parse import urlparse
import re

def validate_image_size(image):
    max_size = 10 * 1024 * 1024  # 10MB
    if image.size > max_size:
        raise ValidationError(f'Image size cannot exceed {max_size/1024/1024}MB')
    return image

def validate_image_type(image):
    if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        raise ValidationError('Unsupported file extension. Please use PNG, JPG, JPEG, GIF or BMP')
    return image

def validate_image_dimensions(image):
    max_width = 4096
    max_height = 4096
    min_width = 100
    min_height = 100
    
    width = image.width
    height = image.height
    
    if width > max_width or height > max_height:
        raise ValidationError(f'Image dimensions cannot exceed {max_width}x{max_height} pixels')
    if width < min_width or height < min_height:
        raise ValidationError(f'Image dimensions must be at least {min_width}x{min_height} pixels')
    return image

def validate_url(url):
    if url and not url.startswith(('http://', 'https://')):
        raise ValidationError('URL must start with http:// or https://')

def validate_image_size(value):
    """
    Validates that the image size is not greater than 10MB
    """
    if value.size > 10 * 1024 * 1024:  # 10MB in bytes
        raise ValidationError(
            _('Image size cannot be greater than 10MB.'),
            code='image_size'
        )

def validate_image_type(value):
    """
    Validates that the file is a valid image type
    """
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError(
            _('Invalid image format. Supported formats: JPG, JPEG, PNG, GIF, WEBP'),
            code='invalid_image_type'
        )

def validate_image_dimensions(value):
    """
    Validates that the image dimensions are reasonable
    """
    try:
        img = Image.open(value)
        width, height = img.size
        if width > 5000 or height > 5000:  # Maximum dimensions
            raise ValidationError(
                _('Image dimensions are too large. Maximum allowed: 5000x5000 pixels'),
                code='image_dimensions'
            )
    except Exception as e:
        raise ValidationError(
            _('Invalid image file.'),
            code='invalid_image'
        )

def validate_url(value):
    """
    Validates URLs to ensure they are not from blocked domains or contain inappropriate content.
    """
    # List of blocked domains and patterns
    BLOCKED_DOMAINS = [
        'adult', 'porn', 'xxx', 'sex', 'scam', 'fraud', 'malware', 'virus',
        'hack', 'crack', 'torrent', 'warez', 'illegal', 'gambling', 'casino',
        'betting', 'drugs', 'pharmacy', 'viagra', 'cialis', 'levitra'
    ]
    
    BLOCKED_PATTERNS = [
        r'\.(adult|porn|xxx|sex|scam|fraud|malware|virus|hack|crack|torrent|warez|illegal|gambling|casino|betting|drugs|pharmacy|viagra|cialis|levitra)\.[a-z]+$',
        r'[^a-zA-Z0-9\-\.]',  # Only allow alphanumeric, hyphens, and dots
    ]

    # Basic URL validation
    validator = URLValidator()
    try:
        validator(value)
    except ValidationError:
        raise ValidationError('Please enter a valid URL.')

    # Parse the URL
    parsed_url = urlparse(value)
    domain = parsed_url.netloc.lower()

    # Check for blocked domains
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            raise ValidationError('This URL is not allowed due to inappropriate content.')

    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, domain):
            raise ValidationError('This URL is not allowed due to inappropriate content.')

    # Additional security checks
    if not parsed_url.scheme in ['http', 'https']:
        raise ValidationError('Only HTTP and HTTPS URLs are allowed.')

    return value

def validate_audio_size(value):
    if value:
        if value.size > 15 * 1024 * 1024:  # 15MB limit for 3-minute voice messages
            raise ValidationError('Audio file size should not exceed 15MB.')

def validate_audio_type(value):
    if value:
        if not value.name.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
            raise ValidationError('Please upload a valid audio file (MP3, WAV, OGG, or M4A).') 