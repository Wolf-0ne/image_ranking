import os
import logging
import re
from xml.sax.saxutils import escape

import xml.etree.ElementTree as ET

# EXIF date tags in order of preference
DATE_TAGS = ('EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime')

EXIF_NS = 'http://ns.adobe.com/exif/1.0/'

# characters not allowed in XMP/Lightroom tag values
_TAG_STRIP = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def sanitize_tag(value: str) -> str:
    """
    Normalise a value for use as a darktable/Lightroom tag.

    Tags are a flat namespace keyed by name; absolute paths produce unusable
    tags (and a drive colon breaks lr:hierarchicalSubject), so keep only the
    file name and strip characters darktable would reject.
    """
    name = os.path.basename(value.replace('\\', '/')).strip()
    name = _TAG_STRIP.sub('_', name).strip('_ ')
    return name


def get_photo_datetime(file: str) -> str | None:
    """
    Read the capture date from the image EXIF data.

    Returns a darktable/XMP compatible timestamp string, e.g.
    "2026:10:17 11:51:32.000", or None when no usable date is found.
    """
    try:
        import exifread
        with open(file, 'rb') as f:
            tags = exifread.process_file(
                f, details=False, stop_tag='DateTimeOriginal'
            )
    except Exception as e:
        logging.debug(f"Unable to read EXIF date from {file}: {e}")
        return None

    for tag in DATE_TAGS:
        if tag in tags:
            value = str(tags[tag]).strip()
            # EXIF uses "YYYY:MM:DD HH:MM:SS"; skip placeholders/zero dates
            if not value or value.startswith('0000') or len(value) < 19:
                continue
            return value if '.' in value else f"{value}.000"

    return None


def get_rating_datetime(file: str, date_source: str | None = None) -> str | None:
    """
    Resolve a capture date for `file`, falling back to `date_source`.

    RAW formats (e.g. Fuji RAF) are not readable by exifread, so the paired
    JPEG is preferred as the date source when one is available.
    """
    from image_ranking.content_type import RAW_MIME_MAP

    # exifread cannot parse most RAW containers; prefer the paired image
    if os.path.splitext(file)[1].lower() in RAW_MIME_MAP:
        if date_source:
            captured = get_photo_datetime(date_source)
            if captured:
                return captured
        return None

    return get_photo_datetime(file) or (
        get_photo_datetime(date_source) if date_source else None
    )


def darktable_set_rating(file: str, rating: int, parent: str, silent: bool = False,
                         date_source: str | None = None):
    """
    Sets the darktable star rating in an XMP file.
    Creates the file if it does not exist.

    Args:
        file (str): The path to the file to be rated.
        rating (int): The desired star rating (0-5).
        parent (str): Group/parent path written to the subject tags.
        silent (bool): Suppress debug logging.
        date_source (str): Optional path to read the capture date from
            (e.g. the paired JPEG when rating a RAW file).
    """

    # clamp to darktable's valid range; -1 means rejected
    rating = max(-1, min(5, int(rating)))

    # derive file info
    filename = os.path.basename(file)
    xmp_filepath = f"{file}.xmp"

    # define xml namespace
    ns = {
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }
    ET.register_namespace('xmp', ns['xmp'])
    ET.register_namespace('rdf', ns['rdf'])
    # keep standard prefixes when ElementTree rewrites an existing sidecar
    ET.register_namespace('exif', EXIF_NS)
    ET.register_namespace('xmpMM', 'http://ns.adobe.com/xap/1.0/mm/')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
    ET.register_namespace('lr', 'http://ns.adobe.com/lightroom/1.0/')
    ET.register_namespace('darktable', 'http://darktable.sf.net/')

    # create if file does not exist
    if not os.path.exists(xmp_filepath):

        # set group tag if provided. darktable reads tags from dc:subject and
        # interprets "/" as the hierarchy separator in lr:hierarchicalSubject,
        # so a full path would create a bogus multi-level tag.
        xml_parent = ''
        tag = sanitize_tag(parent) if parent else ''
        if tag:
            safe_tag = escape(tag)
            xml_parent = f'''<dc:subject>
    <rdf:Bag>
     <rdf:li>{safe_tag}</rdf:li>
    </rdf:Bag>
   </dc:subject>
   <lr:hierarchicalSubject>
    <rdf:Bag>
     <rdf:li>{safe_tag}</rdf:li>
    </rdf:Bag>
   </lr:hierarchicalSubject>'''

        # capture date from EXIF so darktable does not fall back to the epoch
        captured = get_rating_datetime(file, date_source)
        xml_date = ''
        if captured:
            xml_date = f'\n   exif:DateTimeOriginal="{escape(captured)}"'
        else:
            logging.warning(f"No EXIF capture date found for {file}; XMP will lack a date.")

        # create a minimal XMP structure with the rating
        xmp_template = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:exif="http://ns.adobe.com/exif/1.0/"
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:xmpMM="http://ns.adobe.com/xap/1.0/mm/"
    xmlns:darktable="http://darktable.sf.net/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:acdsee="http://ns.acdsee.com/iptc/1.0/"
    xmlns:lr="http://ns.adobe.com/lightroom/1.0/"
   xmp:Rating="{rating}"
   xmpMM:DerivedFrom="{escape(filename)}"{xml_date}>
   {xml_parent}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
'''
        #exif:DateTimeOriginal="2025:01:13 19:19:16.000"

        #open file and write template
        with open(xmp_filepath, 'w', encoding='utf-8') as f:
            f.write(xmp_template)

        #log created
        if not silent:
            logging.debug(f"Created new XMP file at {xmp_filepath} with rating {rating} star(s).")

        return

    #edit existing file
    else:

        try:

            #parse xmp file
            tree = ET.parse(xmp_filepath)

            #get xml root
            root = tree.getroot()

            # Find the rdf:Description element
            description = root.find(".//rdf:Description", ns)

            # set rating attribute
            if description is not None:
                description.set('{http://ns.adobe.com/xap/1.0/}Rating', str(rating))

                # backfill the capture date when the sidecar has none,
                # otherwise darktable shows 1969/epoch timestamps
                date_attr = f'{{{EXIF_NS}}}DateTimeOriginal'
                if description.get(date_attr) is None:
                    captured = get_rating_datetime(file, date_source)
                    if captured:
                        description.set(date_attr, captured)

                tree.write(xmp_filepath, encoding='utf-8', xml_declaration=True)
                if not silent:
                    logging.debug(f"Rating for {xmp_filepath} set to {rating} star(s).")

            # Create rating element if not found
            else:
                logging.warning(f"xmp:Rating element not found in {xmp_filepath}.")

        #file removed between check and parse
        except FileNotFoundError:
            logging.error(f"Error: XMP file not found at {xmp_filepath}")


# Example usage:
# Assuming you have an XMP file named 'my_photo.nef.xmp'
# set_darktable_rating('path/to/my_photo.nef.xmp', 4)