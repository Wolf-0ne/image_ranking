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
    logging.info("get images")

    images = []
    files = os.listdir(args.directory)
    files = [(file, args) for file in files]

    # Iterate results to trim invalid files
    images = enumerate_list(verify_file, files, args.threads)

    # limit to 2x limit to account for raw/jpg pairs
    images = limit_list(images, args.limit * 2)

    # Check for matching raw/jpg pairs and remove raw if jpg exists
    # ( raw can take 10x time to process )
    images = get_filtered_list(images)

    # limit to final limit
    images = limit_list(images, args.limit)

    # initialize valid images
    logging.info("initialize images")
    images = enumerate_list(initialize_file, images, args.threads)

    # return images
    return images


def limit_list(array: list, limit: int) -> list:
    if limit > 0 and len(array) > limit:
        return array[:limit]
    return array


def enumerate_list(operation: callable, array: list, threads: int) -> list:
    result = []
    if len(array) > 0:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            result = list(tqdm(executor.map(operation, array), total=len(array), ascii=' ='))
    return list(filter(None, result))


def get_filtered_list(array: list) -> list:

    # iterate all images
    i = 0
    for item in array:

        # if valid image
        if item:

            # get current file part
            current = item[1]
            image = item[0]

            # get next and previous file parts
            next = ""
            if i < len(array):
                next = array[i + 1]
                if next: next = next[1]
            prev = ""
            if i > 1:
                prev = array[i - 1]
                if prev: prev = prev[1]

            # check if next or previous file is same name ( different extension )
            next = next == current
            prev = prev == current

            # if next or previous file is same name
            if next or prev:

                # check created time delta
                if next:
                    delta = get_created_delta(image, array[i + 1][0])
                else:
                    delta = get_created_delta(image, array[i - 1][0])

                # if created time delta is within 2 seconds, remove raw file
                # ( to avoid removing unrelated files with same name )
                if delta <= 2:

                    # remove current raw file
                    if image.raw_image:
                        logging.debug(f"Removing raw file due to existing jpeg: {image.path}")
                        array[i] = None

                    # remove next raw file
                    elif next:
                        logging.debug(f"Removing raw file due to existing jpeg: {array[i + 1][0].path}")
                        array[i + 1] = None

                    # remove previous raw file
                    else:
                        logging.debug(f"Removing raw file due to existing jpeg: {array[i - 1][0].path}")
                        array[i - 1] = None

        # invalid image
        else:
            array[i] = None

        # increment index
        i += 1

    # return filtered list
    return list(filter(None, array))


def get_created_delta(image_a: ImageHash, image_b: ImageHash) -> float:
    return abs(image_a.created - image_b.created)


def verify_file(arguments) -> bool:
    file, args = arguments

    # Ignore xmp files
    if file.lower().endswith('.xmp'):
        return None

    # create image hash object
    image = ImageHash(file, args)
    if image.validate():
        return (image, get_file_part(file))

    # invalid image
    return None


def get_file_part(path: str) -> str:
    return os.path.splitext(path)[0].lower()


def initialize_file(arguments) -> ImageHash | None:
    image, file_part = arguments

    try:
        logging.debug(f"  {image.filename}, type: {image.content_type}")
        image.initialize()
        return image

    except Exception as e:
        logging.error(f"Error initializing image: {e}")
        return None