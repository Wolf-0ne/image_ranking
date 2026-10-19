# Workspace Instructions — `C:/Users/Wolf-001/Pictures/Processing`

Python photo-culling tool: hashes/groups images, ranks by sharpness, seeds darktable XMP ratings. Single-user Windows host. The tool reads real photo libraries outside this repo and writes sidecars next to them.

## Hard rules

- Real photos live outside this repo. Never move, rename, or delete user images. Writes limited to `.xmp` sidecars and darktable `library.db`
- `docs/KEY-FACTS.md` is the source of truth: XMP contract, crawler mtime rules, DB flag bits, ranking behavior, and bugs already fixed. Read it before changing `image_ranking/`
- Always validate against `Test/` (sample JPG+XMP pairs) before any run against a real shoot
- `-l 0` for real shoots — the `-l` default (250) silently truncates
- Close darktable before touching `library.db` — exclusive lock; lock file holds the PID
- The tool **overwrites higher existing ratings**. Surface this to the user before batch runs; in darktable's crawler dialog "keep the database edit" restores manual stars
- RAW/JPEG pairing uses Windows `ctime` with a 3s window — copying a shoot between drives breaks pairing

## Dependencies

- Pins are exact in `requirements.txt`; refresh with `pipreqs . > requirements.txt` after adding imports
- OpenCV stays 4.14.x (5.x returns `None` from `imread`), flagged for future upgrade/review; rawpy 0.27.1 minimum (no cp314 wheel below)
- Run `python image-ranking.py --help` after changing imports — catches environment drift in seconds

## Layout

- `image-ranking.py` — entry point, CLI, logging (MemoryHandler)
- `image_ranking/` — modules: hash, similarity, blur, exif, darktable sidecar writer, core pipeline
- `helpers/` — one-off repair scripts (`backfill_xmp_dates.py`, `fix_db_ratings.py`); both support dry-run — use it first
- `Test/` — validation samples; `Ignore/`, `Preprocessed/` — data/scratch zones, not source
- Parallel steps (hash, blur, rating) use `ThreadPoolExecutor`, threads via `-t`; grouping is serial — keep it that way
