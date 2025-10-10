
import mimetypes
import os

# Raw file extensions and their mime types
RAW_MIME_MAP = {
    '.cr2': 'image/x-canon-cr2',
    '.nef': 'image/x-nikon-nef',
    '.arw': 'image/x-sony-arw',
    '.raf': 'image/x-fuji-raf',
    '.dng': 'image/x-adobe-dng',
    '.orf': 'image/x-olympus-orf',
    '.rw2': 'image/x-panasonic-rw2'
}

def get_mime_type(file: str) -> str:

    # Map RAW mime types
    content_type = (None, None)
    ext = os.path.splitext(file)[1].lower()
    if ext in RAW_MIME_MAP:
        content_type = (RAW_MIME_MAP[ext], None)

    # Get file mime type
    else:
        content_type = mimetypes.guess_type(file)

    # Ignore non-image files
    if content_type[0] and not content_type[0].startswith('image'):
        return None

    return content_type[0]

def is_image_file(content_type: str) -> bool:
    return content_type and content_type.startswith('image')

def is_raw_image_file(content_type: str) -> bool:
    return content_type and 'image/x-' in content_type