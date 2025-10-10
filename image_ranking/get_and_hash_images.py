import os
import argparse
import logging
from tqdm import tqdm

from concurrent.futures import ThreadPoolExecutor

from image_ranking.content_type import get_mime_type, is_image_file
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

    # Use ThreadPoolExecutor to process files in parallel
    arguments = [(file, args) for file in files]
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

    # create image hash object
    image = ImageHash(file, args)

    # validate and initialize image
    if image.validate():
        logging.debug(f"  {image.filename}, type: {image.content_type}")
        image.initialize()
        return image

    # invalid image
    logging.debug(f"Skipping: {image.filename}, type: {image.content_type}")
    return None