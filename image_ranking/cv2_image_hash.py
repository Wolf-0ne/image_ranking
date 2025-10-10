import cv2
import imutils
import argparse
import numpy as np

def cv2_process_image(path: str, content_type: str, args: argparse.Namespace, debug: bool = False):

    # get image
    image = cv2_get_image(path, content_type, True)

    # resize image
    if args.similarity_resize is not None:
        image = cv2_resize(image, args.similarity_resize)
        if debug:
            cv2.imshow("resize", image)

    # guassian blur
    blur = args.similarity_blur
    for radius in blur:
        if radius is not None:

            # ensure radius is at least 1
            if radius < 1:
                radius = 1

            # ensure radius is odd
            if radius % 2 == 0:
                radius += 1

            # apply blur
            image = cv2.GaussianBlur(image, (radius, radius), 0)
            if debug:
                cv2.imshow(f"blur{radius}", image)

    # apply crop
    crop = args.similarity_crop
    if crop > 0:
        image = cv2_crop(image, args.similarity_crop)
        if debug:
            cv2.imshow(f"crop{crop}", image)

    if debug:
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # return image data
    return image


def cv2_get_image(path: str, content_type: str, grayscale: bool = False):

    image = None

    # read image (raw)
    from image_ranking.content_type import is_raw_image_file
    if is_raw_image_file(content_type):
        import rawpy
        with rawpy.imread(path) as raw:
            image = raw.postprocess(output_color=rawpy.ColorSpace.sRGB)
            image = cv2.cvtColor(image, cv2_get_rgb_color_map(grayscale))

    # read image (heic)
    elif content_type == 'image/heic':
        from PIL import Image
        import pillow_heif

        image = pillow_heif.read_heif(path)
        image = Image.frombytes(
            image.mode,
            image.size,
            image.data,
            "raw"
        )
        image = np.array(image)
        image = cv2.cvtColor(image, cv2_get_rgb_color_map(grayscale))

    # read image (normal)
    else:
        image = cv2.imread(path, cv2.IMREAD_COLOR)
        if grayscale:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # return image data
    return image


def cv2_get_rgb_color_map(grayscale: bool = False):
    return cv2.COLOR_RGB2GRAY if grayscale else cv2.COLOR_RGB2BGR


def cv2_resize(image, shape: tuple):

    # resize image
    if shape is not None:

        # map strings to float
        def map_fractional(v) -> float:
            fractional_map = {
                "half": 1/2,
                "third": 1/3,
                "quarter": 1/4
            }
            v = fractional_map.get(v.lower()) if type(v) is str else v
            return v if v is not None else 1

        if type(shape[0]) is str:
            shape = (round(image.shape[0] * map_fractional(shape[0])), shape[1])
        if type(shape[1]) is str:
            shape = (shape[0], round(image.shape[1] * map_fractional(shape[1])))

        # validate resize
        if not isinstance(shape[0], int) or not isinstance(shape[1], int):
            raise ValueError(
                "resize must be a tuple of two integers or "
                "fractional strings ('half', 'third', 'quarter')"
            )

        # resize
        image = cv2.resize(image, shape)

    # return image data
    return image


def cv2_crop(image, percent):

    # validate crop percentage
    if percent <= 0 or percent >= 100:
        raise ValueError("Crop percentage must be between 0 and 100")

    w = image.shape[0] #width
    h = image.shape[1] #height
    t = percent / 2 # half of crop from each size

    w_min = int(w * t / 100)
    h_min = int(h * t / 100)

    w_max = w - w_min
    h_max = h - h_min

    return image[w_min:w_max, h_min:h_max]


def cv2_draw_color_mask(image, borders, color=(0, 0, 0)):
    w = image.shape[0]
    h = image.shape[1]

    x_min = int(borders[0] * w / 100)
    x_max = w - int(borders[2] * w / 100)
    y_min = int(borders[1] * h / 100)
    y_max = h - int(borders[3] * h / 100)

    image = cv2.rectangle(image, (0, 0), (x_min, h), color, -1)     # left border
    image = cv2.rectangle(image, (0, 0), (w, y_min), color, -1)     # top border
    image = cv2.rectangle(image, (x_max, 0), (w, h), color, -1)     # right border
    image = cv2.rectangle(image, (0, y_max), (w, h), color, -1)     # bottom border

    return image


def cv2_compare_image(a, b, args: argparse.Namespace):

    # validate image shape
    if a.shape != b.shape:
        raise ValueError("Images must be the same size for comparison")

    # compute the absolute difference between frames
    frame_delta = cv2.absdiff(a, b)

    # threshold the delta image
    thresh = cv2.threshold(frame_delta, args.similarity_delta, 255, cv2.THRESH_BINARY)[1]

    # dilate the thresholded image to fill in holes
    thresh = cv2.dilate(thresh, None, iterations=2)

    # find contours on thresholded image
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # calculate score and filter by min area
    score = 0
    res_cnts = []
    for c in cnts:
        if cv2.contourArea(c) < args.similarity_min_contour:
            continue

        res_cnts.append(c)
        score += cv2.contourArea(c)

    # return score, contours and threshold image
    return score, res_cnts, thresh

