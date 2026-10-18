"""
Sync darktable DB star ratings from XMP sidecars, conservatively.

Only images whose DB rating is 0 and whose sidecar has a positive rating are
updated. Existing non-zero ratings are never lowered or changed, so manual
edits made inside darktable are preserved.

darktable must be closed (it holds library.db.lock while running).

Usage:
    python fix_db_ratings.py <folder> [--apply] [--include-raw]
"""

import argparse
import os
import re
import shutil
import sqlite3
import sys
import time

# darktable image flag bits (src/common/image.h)
RATINGS_MASK = 0x7      # first 3 bits: star rating 0..5
DT_IMAGE_REJECTED = 8

RATING_RE = re.compile(r'xmp:Rating="(-?\d+)"')


def rating_from_flags(flags: int) -> int:
    return -1 if (flags & DT_IMAGE_REJECTED) else (flags & RATINGS_MASK)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Raise darktable DB star ratings from XMP sidecars')
    parser.add_argument('folder', help='shoot folder containing images + xmp')
    parser.add_argument('--apply', action='store_true',
                        help='write changes (default is dry run)')
    parser.add_argument('--include-raw', action='store_true',
                        help='also set RAW ratings from their own sidecar')
    parser.add_argument('--sync-raw-to-jpg', action='store_true',
                        help='set RAW DB ratings to match their JPEG sibling')
    args = parser.parse_args()

    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        return f"Not a directory: {folder}"

    db = os.path.join(os.environ['LOCALAPPDATA'], 'darktable', 'library.db')
    if not os.path.isfile(db):
        return f"library.db not found: {db}"

    lock = db + '.lock'
    if os.path.exists(lock):
        return (f"darktable appears to be running (lock file {lock} exists). "
                "Close darktable before running this script.")

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute(
        "SELECT i.id, i.filename, i.flags, f.folder"
        " FROM main.images i JOIN main.film_rolls f ON i.film_id = f.id"
        " WHERE f.folder = ? ORDER BY i.filename",
        (folder,),
    ).fetchall()

    if not rows:
        return f"No DB rows for folder: {folder}"

    updates = []
    skipped_raw = 0
    skipped_no_xmp = 0
    kept_existing = 0

    # map filename -> current DB rating, used for RAW/JPEG pairing
    by_name = {r['filename']: rating_from_flags(r['flags'] or 0) for r in rows}

    for r in rows:
        name = r['filename']
        ext = os.path.splitext(name)[1].lower()
        is_raw = ext in ('.raf', '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2')

        # optionally mirror the JPEG rating onto the RAW entry
        if is_raw and args.sync_raw_to_jpg and not args.include_raw:
            stem = os.path.splitext(name)[0]
            jpeg_rating = None
            for jext in ('.JPG', '.jpg', '.JPEG', '.jpeg'):
                if stem + jext in by_name:
                    jpeg_rating = by_name[stem + jext]
                    break
            if jpeg_rating is None or jpeg_rating <= 0:
                skipped_raw += 1
                continue
            flags = r['flags'] or 0
            if rating_from_flags(flags) == jpeg_rating:
                continue
            new_flags = ((flags & ~RATINGS_MASK & ~DT_IMAGE_REJECTED)
                         | jpeg_rating)
            updates.append((r['id'], name,
                            rating_from_flags(flags), jpeg_rating, new_flags))
            continue

        if is_raw and not args.include_raw:
            skipped_raw += 1
            continue

        xmp = os.path.join(r['folder'], name + '.xmp')
        if not os.path.exists(xmp):
            skipped_no_xmp += 1
            continue

        m = RATING_RE.search(open(xmp, encoding='utf-8', errors='ignore').read())
        if not m:
            skipped_no_xmp += 1
            continue

        xmp_rating = int(m.group(1))
        if xmp_rating <= 0:
            continue

        flags = r['flags'] or 0
        db_rating = rating_from_flags(flags)
        if db_rating != 0:
            # never touch an existing rating (protects manual 4/5 stars)
            kept_existing += 1
            continue

        new_flags = (flags & ~RATINGS_MASK & ~DT_IMAGE_REJECTED) | xmp_rating
        updates.append((r['id'], name, db_rating, xmp_rating, new_flags))

    print(f"DB rows in folder : {len(rows)}")
    print(f"to update (0 -> n): {len(updates)}")
    print(f"kept existing     : {kept_existing}")
    print(f"skipped RAW       : {skipped_raw}")
    print(f"skipped no rating : {skipped_no_xmp}")

    if updates:
        print("\nfirst 10 changes:")
        for _, name, old, new, _ in updates[:10]:
            print(f"  {name:<18} {old} -> {new}")

    if not args.apply:
        print("\nDRY RUN - nothing written. Re-run with --apply to commit.")
        return 0

    # safety backup before writing
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup = f"{db}.bak-ratings-{stamp}"
    shutil.copy2(db, backup)
    print(f"\nbackup written: {backup}")

    with con:
        con.executemany(
            "UPDATE main.images SET flags = ?2 WHERE id = ?1",
            [(uid, new_flags) for uid, _, _, _, new_flags in updates],
        )

    print(f"updated {len(updates)} DB rows")
    con.close()
    return 0


if __name__ == '__main__':
    result = main()
    if isinstance(result, str):
        print(f"ERROR: {result}", file=sys.stderr)
        sys.exit(1)
    sys.exit(result)
