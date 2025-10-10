import mimetypes
import os

import logging

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

    # Avoid processing invalid file types
    if get_magic_type(file) != content_type[0]:
        return None

    return content_type[0]

def is_image_file(content_type: str) -> bool:
    return content_type and content_type.startswith('image')

def is_raw_image_file(content_type: str) -> bool:
    return content_type and content_type.startswith('image/x-')

MAGIC_BYTE_SIGNATURES = {
    # JPEG
    (b'\xFF\xD8\xFF', 'image/jpeg', (-1,)),  # JPEG files start with FF D8 FF

    # PNG
    (b'\x89PNG\r\n\x1a\n', 'image/png', (0,)),  # PNG files start at offset 0

    # Fuji RAF
    (b'FUJIFILMCCD-RAW', 'image/x-fuji-raf', (0,)),  # Fuji RAF (starts at offset 0)

    # Canon CR2 (TIFF-based, but with 'CR' at offset 8)
    (b'CR', 'image/x-canon-cr2', (8,)),

    # Nikon NEF (TIFF-based, but with 'NEF' at offset 8)
    (b'NEF', 'image/x-nikon-nef', (8,)),

    # Sony ARW (TIFF-based, but with 'SONY' at offset 0 or 8)
    (b'SONY', 'image/x-sony-arw', (0, 8)),

    # Adobe DNG (TIFF-based, but with 'DNG' at offset 0 or 8)
    (b'DNG', 'image/x-adobe-dng', (0, 8)),

    # Olympus ORF (TIFF-based, but with 'OLYMPUS' at offset 8)
    (b'OLYMPUS', 'image/x-olympus-orf', (8,)),

    # Panasonic RW2 (TIFF-based, but with 'RW2' at offset 8)
    (b'RW2', 'image/x-panasonic-rw2', (8,)),

    # TIFF (used by some RAW)
    (b'II*\x00', 'image/x-tiff', (-1,)),        # TIFF (little-endian)
    (b'MM\x00*', 'image/x-tiff', (-1,)),        # TIFF (big-endian)

    # HEIC/HEIF (ISO Base Media File Format, 'ftypheic' or 'ftypheix' at offset 4)
    (b'ftypheic', 'image/heic', (4,)),
    (b'ftypheix', 'image/heic', (4,)),
    (b'ftyphevc', 'image/heic', (4,)),
    (b'ftypmif1', 'image/heic', (4,)),
    (b'ftypmsf1', 'image/heic', (4,)),
}

def get_magic_type(file_path):

    with open(file_path, 'rb') as f:

        # Read enough bytes for most signatures
        header = f.read(32)

        #iterate magic byte signatures
        for sig, mime, offsets in MAGIC_BYTE_SIGNATURES:

            logging.debug(f"Checking signature for {mime} at offsets {offsets}")

            # iterate all offsets
            for offset in offsets:
                # signature present at any offset
                if offset == -1:
                    if sig in header:
                        return mime

                # signature present at specific offset
                else:
                    if header[offset:offset+len(sig)] == sig:
                        return mime

    # no signature matched
    return None
