"""
Backfill exif:DateTimeOriginal into existing darktable XMP sidecars.

Sidecars written by older versions of image-ranking.py contain only
xmp:Rating, which makes darktable fall back to an epoch timestamp
(displayed as 1969-12-31). This script adds the capture date from the
image EXIF data without touching ratings or other darktable attributes.

Usage:
    python backfill_xmp_dates.py <directory> [--dry-run]
"""

import argparse
import glob
import logging
import os
import re
import sys

from image_ranking.darktable_set_rating import (
    get_rating_datetime,
    sanitize_tag,
)

DATE_RE = re.compile(r'exif:DateTimeOriginal="([^"]+)"')

# rdf:li values that look like absolute paths (the old writer stored these)
PATH_TAG_RE = re.compile(
    r'<rdf:li>((?:[A-Za-z]:)?[\\/][^<]*)</rdf:li>'
)


def find_date_source(xmp_path: str) -> str | None:
    """
    Locate the image a sidecar belongs to and, for RAW files, its JPEG pair.
    """
    image_path = xmp_path[:-4]  # strip ".xmp"
    if not os.path.isfile(image_path):
        return None

    # prefer the JPEG sibling as the EXIF date source
    stem, ext = os.path.splitext(image_path)
    if ext.lower() not in ('.jpg', '.jpeg'):
        for candidate in ('.JPG', '.jpg', '.JPEG', '.jpeg'):
            sibling = stem + candidate
            if os.path.isfile(sibling):
                return sibling

    return image_path


def backfill(xmp_path: str, dry_run: bool) -> str:
    """
    Add exif:DateTimeOriginal to a sidecar if missing.

    :return: one of "backfilled", "has-date", "no-date", "unreadable"
    """
    try:
        with open(xmp_path, encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except OSError as e:
        logging.debug(f"Cannot read {xmp_path}: {e}")
        return "unreadable"

    has_date = bool(DATE_RE.search(text))

    # the old writer stored absolute paths as rdf:li tag values; repair them
    updated = PATH_TAG_RE.sub(
        lambda m: f'<rdf:li>{sanitize_tag(m.group(1))}</rdf:li>', text
    )

    if not has_date:
        source = find_date_source(xmp_path)
        captured = get_rating_datetime(xmp_path[:-4], source) if source else None
        if captured:
            # insert alongside an existing xmp:Rating attribute
            updated = re.sub(
                r'(xmp:Rating="\d+")',
                rf'\1\n   exif:DateTimeOriginal="{captured}"',
                updated,
                count=1,
            )
            if 'xmlns:exif=' not in updated:
                updated = updated.replace(
                    '<rdf:Description',
                    '<rdf:Description\n    xmlns:exif="http://ns.adobe.com/exif/1.0/"',
                    1,
                )

    if updated == text:
        return "has-date" if has_date else "no-date"

    if not dry_run:
        with open(xmp_path, 'w', encoding='utf-8') as f:
            f.write(updated)

    return "fixed"


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Backfill EXIF capture dates into XMP sidecars'
    )
    parser.add_argument('directory', help='directory containing images and XMPs')
    parser.add_argument('--dry-run', action='store_true',
                        help='report what would change without writing')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='enable debug logging')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(levelname)s %(message)s',
    )

    if not os.path.isdir(args.directory):
        logging.error(f"Not a directory: {args.directory}")
        return 1

    xmps = sorted(glob.glob(os.path.join(args.directory, '*.xmp')))
    counts = {"fixed": 0, "has-date": 0, "no-date": 0, "unreadable": 0}

    for xmp in xmps:
        result = backfill(xmp, args.dry_run)
        counts[result] += 1
        if result == "no-date":
            logging.debug(f"No usable EXIF date: {os.path.basename(xmp)}")

    verb = "would fix" if args.dry_run else "fixed"
    print(f"{len(xmps)} sidecars: {counts['fixed']} {verb}, "
          f"{counts['has-date']} already correct, "
          f"{counts['no-date']} without a usable date, "
          f"{counts['unreadable']} unreadable")
    return 0


if __name__ == '__main__':
    sys.exit(main())
