# Key Facts & Gotchas

Terse notes from the 2026-10-17 session. Read before changing the tool.

## Always

- `-l 0` for real shoots. Default `-l 250` silently truncates.
- Close darktable before touching `library.db` — exclusive lock, lock file holds the PID.
- Run `--help` after changing imports; catches environment drift in one second.

## darktable XMP contract

- Reads: `xmp:Rating`, `xmp:Label`, `exif:DateTimeOriginal`, `dc:subject`, `darktable:*`.
- Missing `exif:DateTimeOriginal` → dates render as **1969** (epoch 0).
- Never synthesize `darktable:history*` / `auto_presets_applied` — darktable discards XMP that has them with no matching history.
- Tag values must be names, not paths. `/` in `lr:hierarchicalSubject` builds a bogus hierarchy; a drive colon is invalid.
- Escape filenames into XML — an `&` yields malformed XML darktable rejects silently.

## Crawler: why sidecars get ignored

- `src/control/crawler.c`: flags a sidecar only if `xmp mtime > images.write_timestamp + 2`.
- After one crawl darktable sets `write_timestamp = xmp mtime` → equal → never flagged again.
- Editing the DB directly beats mtime games.

## write_sidecar_files modes

- `after edit` (default, lazy) **deletes** sidecars with no altered data — rating-only sidecars vanish.
- `on import` keeps them. This tool wants `on import`.

## DB flags (main.images.flags)

- Rating bits are `0x7`; `DT_IMAGE_REJECTED = 8`.
- `0x8000` is `DT_IMAGE_MONOCHROME`, **not** rejected.
- Read: `-1 if flags & 8 else flags & 0x7`. Write: `(flags & ~0x7 & ~8) | rating`.

## Ranking behaviour

- Rank is per-group, not absolute — 3 stars means "best in this group".
- Ladder doubles: any group larger than `max_rank + 1` produces rank-0 images.
- Tool writes up to `max_rank` (default 3), never 4–5, and **overwrites higher existing ratings**. In darktable's crawler dialog prefer *keep the database edit* to restore manual stars.

## Pairing caveat

- RAW/JPEG pairing requires `ctime` within 3s. On Windows `ctime` is *creation* time, so copying a shoot between drives breaks pairing.

## Bugs fixed — don't reintroduce

| Bug | Symptom |
|---|---|
| `image.path = raw_path` in pair filter | JPEGs decoded as RAF → `cvtColor !_src.empty()` |
| `if rating == 0: return` | group tails got no sidecar at all |
| `help='... (in %)'` in argparse | `ValueError: badly formed help string`; `%` must be `%%` |
| no `isfile` guard in `verify_file` | `PermissionError` on subfolders |
| OpenCV 5.0.0.93 | `imread` returns `None`; stay on 4.14.x |
| `rawpy==0.25.1` | no cp314 wheel; use 0.27.1 |
| absolute path as tag value | unusable tags, broken hierarchy |

## Scripts

- `backfill_xmp_dates.py <dir> [--dry-run]` — add missing dates, repair path tags.
- `fix_db_ratings.py <dir> [--apply] [--sync-raw-to-jpg]` — raise 0-star DB ratings from sidecars; never lowers existing values.
