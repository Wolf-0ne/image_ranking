import cv2
import logging
import numpy

from image_ranking.cv2_image_hash import (
    cv2_get_image,
    cv2_crop,
    cv2_resize
)

def calculate_blur(
        filename: str,
        mode: str = "sml",
        raw_image: bool = False,
        resize: tuple = None,
        crop: float = 0.0) -> float:

    # read image
    image = cv2_get_image(filename, raw_image, True)
    if image is None:
        logging.warning(f'warning! failed to read image from {filename}; skipping!')
        return

    # resize and crop
    image = cv2_resize(image, resize) # resize to speed up processing
    image = cv2_crop(image, crop) # crop for central blur detection

    # estimate blur
    mode = str(mode).lower()
    match mode:

        # Laplacian
        case "laplacian":
            score = calculate_laplacian(image)

        # Tenengrad (Sobel)
        case "sobel":
            score = calculate_sobel(image)

        # Sum Modified Laplacian
        # in my test data so far, SML seems to line up with Sobel results regularly
        # and is on par with Laplacian performance
        case _:
            score = calculate_sml(image)

    return score

def calculate_laplacian(image: numpy.array):

    # Laplacian
    blur_map = cv2.Laplacian(image, cv2.CV_64F)
    score = numpy.var(blur_map)

    return score

def calculate_sobel(image: numpy.array):

    # Sobel (Tenengrad)
    sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
    tenengrad = numpy.sqrt(sobelx**2 + sobely**2)
    score = numpy.mean(tenengrad)

    return score

def calculate_sml(image: numpy.array):

    # Sum Modified Laplacian
    M = numpy.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])
    score = numpy.abs(cv2.filter2D(image, cv2.CV_64F, M)).sum()

    return score