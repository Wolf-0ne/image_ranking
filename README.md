# Image Ranking Tool

Pre-rank photo shoots by sharpness and seed star ratings into darktable `.xmp` sidecars, so culling bursts and series starts mostly done.

## ⚠️ Read this first

> [!WARNING]
> **This tool writes.** It creates and overwrites `.xmp` sidecar files next to your images, and can update darktable's `library.db` directly. It **never moves, renames, or deletes** your original images.

> [!WARNING]
> **Ratings are overwritten, not maxed.** The tool will replace a higher existing rating with a lower computed one. In darktable's crawler dialog, *keep the database edit* restores your manual stars.

> [!WARNING]
> **The `-l` default is 250 and silently truncates.** Pass `-l 0` on real shoots to process every image.

> [!NOTE]
> **Close darktable before any `library.db` write** — it holds an exclusive lock (the lock file holds the PID).

> [!NOTE]
> **RAW/JPEG pairing uses Windows `ctime` within a 3-second window.** Copying a shoot between drives can break RAW↔JPEG pairing.

Full contract details — XMP fields, crawler timestamp rules, DB flag bits, ranking behavior, bugs already fixed — live in [`docs/KEY-FACTS.md`](docs/KEY-FACTS.md).

## Overview

This script (`image-ranking.py`) reviews and groups similar images, ranks them by sharpness (blurriness), then seeds `.xmp` files with ratings for use in [darktable](https://www.darktable.org/).

These `.xmp` files are detected on import, or on startup if you have "look for updated xmp files on startup" enabled.

My primary goal was a tool to pre-seed ratings to help with culling bursts/series of photos. I'd also like to potentially group the images as well based on the subject, but with the current variance in this tool I'm avoiding moving any files around for now.

I primarily shoot Fujifilm JPG; rawpy is included for experimental RAW support.

## Features

- Similarity Detection: via feature detection or hashing. Calculated in sequence to avoid hash collision
- Blur Rank: each image is analyzed for sharpness using Laplacian on the center of the image
- Ranking: within each group, images are ranked by sharpness
- Darktable Seeding: sets default star ratings in darktable `.xmp` files
- Parallel Processing: hashes, blur, and rating are done in parallel; grouping has to be serial though

## Install

```sh
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Pins are exact — two are load-bearing:

- **OpenCV stays on 4.14.x** (`opencv_python==4.14.0.94`): 5.x returns `None` from `imread`
- **rawpy 0.27.1 minimum**: older versions have no cp314 wheel

After changing imports, run `python image-ranking.py --help` — catches environment drift in one second.

## Usage

By default the hashing method is used as it's more fuzzy; feature detection creates more groups but doesn't seem to work well with the flowers in my test data set. In my testing the grouping is fairly reliable, although it does require tuning the difference threshold which is not ideal.

### Basic Command

```sh
python image-ranking.py <directory> [options]
```

### Required Argument

- `<directory>`: path to the folder containing your images.

### Basic Options

- `-f, --feature_matching`
  Use feature matching mode for grouping.

- `-e, --exclude`
  Exclude images that already have an XMP file.

- `-d, --diff <float>`
  Image difference threshold for grouping (default: 0.6, or 0.4 with `-f/--feature_matching`).

- `-m, --max_rank <int>`
  Maximum star rating to assign (default: 3). Rank is **per-group**, not absolute — see [Ranking behaviour](docs/KEY-FACTS.md#ranking-behaviour) in KEY-FACTS.md.

- `-t, --threads <int>`
  Number of threads to use (default: number of CPU cores).

- `-l, --limit <int>`
  Max number of images to process (default: 250 — **silently truncates larger shoots; pass `-l 0`**).

- `--similarity_resize <(width, height)>`
  Similarity detection image size. Supports keywords `"half"`, `"third"`, `"quarter"` (default: `(144, 196)`, or `('quarter', 'quarter')` for feature matching).

- `--similarity_crop <int>`
  Similarity detection crop mask (in %, default: 15).

- `--similarity_blur <[int]>`
  List of radii for Gaussian blur applied before similarity detection (default: `[5]`).

- `--similarity_min_contour <int>`
  Similarity minimum contour area (default: 500).

- `--similarity_delta <int>`
  Similarity delta threshold (default: 25).

- `--blur_mode <str>`
  Blur detection algorithm: `sum_modified_laplacian`, `sobel`, or `laplacian` (default: `sum_modified_laplacian`).

- `--blur_crop <int>`
  Blur detection crop mask (in %, default: 30).

- `--blur_resize <(width, height)>`
  Blur detection image size. Supports keywords `"half"`, `"third"`, `"quarter"` (default: `('half', 'half')`).

- `-v, --verbose`
  Enable debug logging.

### Example

```sh
python image-ranking.py ./photoshoot -l 0 -e -m 4 -v
```

## Outputs

- `.xmp` sidecar files written next to your images (ratings only)
- Optional `library.db` update via the repair helpers in `helpers/`
- Originals are never modified

## Supported inputs

- **Fujifilm JPG — tested** (my primary format)
- RAW via rawpy — **experimental**

## Repo layout

| Path | What it is |
|---|---|
| `image-ranking.py` | Entry point: CLI, logging (MemoryHandler), pipeline orchestration |
| `image_ranking/` | Modules: hash, similarity, blur, exif, darktable sidecar writer, core pipeline |
| `helpers/` | One-off repair scripts (`backfill_xmp_dates.py`, `fix_db_ratings.py`); both support dry-run — use it first |
| `docs/` | [`KEY-FACTS.md`](docs/KEY-FACTS.md) — source of truth for the XMP contract and known bugs |
| `Test/` | Validation samples (JPG + XMP pairs) — validate here before any real shoot |
| `Ignore/`, `Preprocessed/` | Data/scratch zones, not source |
| `autorun.ps1` | Personal batch runner — loops the tool over dated shoot folders with `-l 0` |
| `mining_*.py`, `mining_diff.patch` | Scratch experiments |

## How it works

1. **Image Hashing:**
   Images are collected, grayscaled, optionally resized/cropped/Gaussian blurred, and then hashed/pre-processed in parallel.

2. **Grouping by Similarity, Series, and MetaData:**
   Images are grouped via the selected method and if they are sequential. Camera body and lens metadata is also checked.

3. **Blur Calculation:**
   Images are resized, cropped, and then blur is calculated via Laplacian (I'm looking into this for more advanced blur handling: https://github.com/Utkarsh-Deshmukh/Blurry-Image-Detector)

4. **Ranking + Rating:**
   Images are sorted by sharpness, then rankings are applied based on the selected method from `max_rank` to zero.

## Troubleshooting

- **`imread` returns `None`** — you're on OpenCV 5.x. Reinstall from `requirements.txt` (pinned to 4.14.x).
- **rawpy install fails** — versions below 0.27.1 have no cp314 wheel; the pin in `requirements.txt` is the minimum.
- **Dependency drift after editing imports** — run `python image-ranking.py --help`; regenerate pins with `pipreqs . > requirements.txt`.
- **Sidecars ignored by darktable** — see [Crawler: why sidecars get ignored](docs/KEY-FACTS.md) (mtime rules); editing the DB directly beats mtime games.
- **Dates show as 1969** — missing `exif:DateTimeOriginal`; run `helpers/backfill_xmp_dates.py --dry-run` first.

## ToDo

- [ ] Add option for second pass with Feature Detection to focus on images not in groups
- [ ] Add Group Tagging to xmp files
- [ ] Add Object Detection (dog, person, flower, rock?, landscape, etc) to improve group tagging
  - [ ] pass in classifier xml files
  - [ ] if match a single classifier, apply tag
  - [ ] if match multiple, don't apply tag
  - [ ] method to train classifier?
  - [ ] find an ai model to train an ai model? lol
- [ ] For grouping
  - [ ] on default settings, sub 10k hash matches seem very similar, > 10k is a crap shoot
  - [ ] some > 10k images are the same with different colors/brightness
  - [ ] possible to do multiple passes?
    - [ ] pass a, low color hash
    - [ ] pass b, feature match
    - [ ] grouping by a + b ?
  - [ ] max delta if delta > threshold
  - [ ] look for high delta variance on hash matches, if delta is 1000, then 5000 reject
- [ ] If blur is super close, rank same?
- [ ] Store blur rank?
- [ ] Chart blur delta in group

## Notes

- Always review the results before bulk deleting or archiving images
- The tool is designed to be a starting point for culling, not a magic bullet
- This tool is provided with no guarantees (:

## Citations

- I used Copilot quite a bit on this as I've only used python a handful of times
- mimetype filtering and grouping derived from [ezirmusitua's group-same-image.py](https://gist.github.com/ezirmusitua/1aa47567ad4ebd5679f9e3df09585e17)
- learned how to use Laplacian and argparse from [WillBrennan's BlurDetection2](https://github.com/WillBrennan/BlurDetection2/tree/master)

## Support

> [!TIP]
> If you like my work, check out my [Buy Me a Coffee](https://buymeacoffee.com/wolfone_) link.
>
> <a href="https://buymeacoffee.com/wolfone_"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" width="180"></a>

## License

[MIT](LICENSE) — see [LICENSE](LICENSE).
