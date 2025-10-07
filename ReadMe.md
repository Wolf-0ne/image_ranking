# Image Ranking Tool


## Overview

This script (`image-ranking.py`) is designed to review and group similar images, rank them by sharpness (blurriness), then seed xmp files with ratings for use in [darktable](https://www.darktable.org/).

These xmp files will be detected on import or detected on startup if you have "look for updated xmp files on startup" enabled.

My primary goal was to develop a tool to pre-seed ratings to help with culling bursts/series of photos. I'd also like to potentially group the images as well based on the subject, but with the current variance in this tool I'm avoiding moving any files around for now.

I primarily shoot Fujifilm JPG, but I have added rawpy to hopefully maybe support some Raw formats.

## Features

- Similarity Detection: via feature detection or hashing. Calculated in sequence to avoid hash collision
- Blur Rank: Each image is analyzed for sharpness using Laplacian on the center of the image
- Ranking: Within each group, images are ranked by sharpness
- Darktable Seeding: Sets default star ratings in darktable .xmp files
- Parallel Processing: Hashes, Blur, and Set Ratings are done in parralel, Grouping has to be serial though

## ToDo

- Add option for second pass with Feature Detection to focus on images not in groups
- Add Group Tagging to xmp files
- Add Object Detection ( dog, person, flower, rock?, landscape, etc ) to improve group tagging


## Steps

1. Image Hashing:
   Images are collected, grayscaled, optionally resized/cropped/guassian blurred, and then hashed/pre-processed in parallel.

2. Grouping by Similarity, Series, and MetaData:
   Images are grouped via the selected method and if they are sequential. Camera Body and Lens Metadata is also checked.

3. Blur Calculation:
   Images are resized, cropped, and then blur is calculated via laplacian ( I'm looking into this for more advanced blur handling https://github.com/Utkarsh-Deshmukh/Blurry-Image-Detector )

4. Ranking + Rating:
   Images are sorted by sharpness, then rankings are applied based on the selected method from max_rank to zero.


## Usage

By default the hashing method is used as it's more fuzzy, feature detection creates more groups but doesn't seem to work well with the flowers in my test data set. In my testing the grouping is fairly reliable, although it does require tuning the difference threshold which is not ideal.


### Basic Command

```sh
python image-ranking.py <directory> [options]
```

### Required Argument

- `<directory>`: Path to the folder containing your images.

### Basic Options

- `-f, --feature_matching`
  Use feature matching mode for grouping.

- `-e, --exclude`
  Exclude images that already have an XMP file.

- `-d, --diff <float>`
  Image difference threshold for grouping (default: 0.9 or 0.4 for feature matching).

- `-m, --max_rank <int>`
  Maximum star rating to assign (default: 3).

- `-t, --threads <int>`
  Number of threads to use (default: number of CPU cores).

- `--similarity_resize <(height, width)>`
  Similarity detection image size. Supports keywords `"half"`, `"third"`, `"quarter"` (default: (144, 196) or ('quarter', 'quarter') for feature matching).

- `--similarity_crop <int>`
  Similarity detection crop mask (in %, default: 15).

- `--similarity_blur <[int]>`
  List of radii for Gaussian blur applied before similarity detection (default: [3]).

- `--feature_min_contour <int>`
  Feature matching minimum contour area (default: 500).

- `--feature_delta <int>`
  Feature matching delta threshold (default: 25).

- `--blur_mode <str>`
  Blur detection algorithm: `sum_modified_laplacian`, `sobel`, or `laplacian` (default: `sum_modified_laplacian`).

- `--blur_crop <int>`
  Blur detection crop mask (in %, default: 30).

- `--blur_resize <(height, width)>`
  Blur detection image size. Supports keywords `"half"`, `"third"`, `"quarter"` (default: ('half', 'half')).

- `-v, --verbose`
  Enable debug logging.

### Example

```sh
python image-ranking.py ./photoshoot -e -m 4 -v
```

## Citations

- I used CoPilot quite a bit on this as I've only used python a handful of times
- mimetype filtering and grouping derived from [ezirmusitua's group-same-image.py](https://gist.github.com/ezirmusitua/1aa47567ad4ebd5679f9e3df09585e17)
- learned how to use Laplacian and argparse from [WillBrennan's BlurDetection2](https://github.com/WillBrennan/BlurDetection2/tree/master)


## Notes

- Always review the results before bulk deleting or archiving images
- The tool is designed to be a starting point for culling, not a magic bullet
- This tool is provided with no guarantees (:
- reminder for future me, do "pipreqs . > requirements.txt" when you add new imports