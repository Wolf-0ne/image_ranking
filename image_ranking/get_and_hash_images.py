
import mimetypes
import os
import argparse
import logging
from tqdm import tqdm

from concurrent.futures import ThreadPoolExecutor

from image_ranking.image_hash import ImageHash


def get_and_hash_images(args: argparse.Namespace):
    """
    Iterate all files in given directory, generate image hash for each image file
    :param args: arguments namespace
    :return: images
    :rtype: a list of tuple(filename, file_path)
    """
    logging.info("get_and_hash_images")

    images = []
    files = os.listdir(args.directory)
    arguments = [(file, args) for file in files]

    # Use ThreadPoolExecutor to process files in parallel
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        results = list(tqdm(executor.map(process_file, arguments), total=len(files), ascii=' ='))
        #add valid hashed images to list
        for result in results:
            if result:
                images.append(result)

    # return images
    return images


def process_file(arguments) -> ImageHash | None:
    file, args = arguments

    # Ignore xmp files
    if file.lower().endswith('.xmp'):
        return None

    # Get file mime type
    content_type = mimetypes.guess_type(file)

    # Ignore non-image files
    if content_type[0] and not content_type[0].startswith('image'):
        return None

    # Get file path
    file_path = os.path.join(args.directory, file)

    # If is file
    if os.path.isfile(file_path):
        
        # Ignore already processed file
        if args.exclude:
            if os.path.isfile(f"{file_path}.xmp"):
                return None
        
        # hash file result
        return ImageHash(file, file_path, content_type, args)
    
    return None
