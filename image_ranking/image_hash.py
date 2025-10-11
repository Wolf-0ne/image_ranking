import hashlib
import logging
import os

#suppress exifread warnings
logging.getLogger("exifread").setLevel(logging.ERROR)

class ImageHash:

    """
    Image data and methods for comparing images
    :param filename: image filename
    """
    def __init__(self, filename: str, args):

        # set args
        self.args = args

        # set filename
        self.filename = filename

        # image original path
        self.path = os.path.join(args.directory, filename)

        # image mime type
        from image_ranking.content_type import get_mime_type
        self.content_type = get_mime_type(self.path)

        # image blur value
        self.blur = None

        # image rank
        self.rank = 0

        # similarity data
        self.similar = []

        # parent image ref
        self.root = None


    def validate(self) -> bool:

        # Validate file exists
        if os.path.isfile(self.path):

            # Ignore already processed file
            if self.args.exclude:
                if os.path.isfile(f"{self.path}.xmp"):
                    logging.debug(f"Skipping already processed file: {self.filename}")
                    return False

            # validate image file
            from image_ranking.content_type import is_image_file
            if not is_image_file(self.content_type):
                logging.debug(f"Skipping non-image file: {self.filename}, type: {self.content_type}")
                return False

            # raw image flag
            from image_ranking.content_type import is_raw_image_file
            self.raw_image = is_raw_image_file(self.content_type)

            # log file timestamp
            self.created = os.path.getctime(self.path)

            # file exists and is valid
            return True

        # file does not exist
        logging.debug(f"File does not exist: {self.filename}")
        return False

    def initialize(self):

        # get exif data
        from image_ranking.image_exif import get_exif
        self.exif = get_exif(self.path)

        # cv2 processed image
        from image_ranking.cv2_image_hash import cv2_process_image
        self.processed_image = cv2_process_image(self.path, self.content_type, self.args)

        # save image shape
        self.shape = self.args.similarity_resize
        if self.processed_image.shape is not None:
            self.shape = self.processed_image.shape

        # hash image
        self.hash = hashlib.md5(str(self.processed_image).encode()).hexdigest()

        # calculate score threshold
        self.metric = self.args.diff
        if not self.args.feature_matching:
            self.metric = self.shape[0] * self.shape[1] * self.metric


    def is_same_group(self, anotherImage) -> bool:

        score = 0
        result = False

        # return if exif data mismatch
        from image_ranking.image_exif import exif_mismatch
        if exif_mismatch(self.exif, anotherImage.exif):
            logging.debug(f"EXIF mismatch: {self.filename} and {anotherImage.filename}")
            return result

        # feature matching
        if self.args.feature_matching:
            from image_ranking.image_similarity import image_similarity
            score = image_similarity(self.processed_image, anotherImage.processed_image)
            result = score >= self.args.diff

        # cv2 hash compare
        else:
            from image_ranking.cv2_image_hash import cv2_compare_image
            score, res_cnts, thresh = cv2_compare_image(
                self.processed_image,
                anotherImage.processed_image,
                self.args)
            #delta is rougly number of total pixels
            result = score < self.metric

        # save similarity data
        self.similar.append((anotherImage.filename, score, result))

        # return compare result
        return result

    def calculate_blur(self):
        try:

            # calculate blur
            from image_ranking.image_blur import calculate_blur
            self.blur = calculate_blur(
                self.path,
                self.content_type,
                self.args.blur_mode,
                self.args.blur_resize,
                self.args.blur_crop)

            return True

        except Exception as e:
            logging.error(f"error calculating blur for {self.path}: {e}", exc_info=True)

        return False


    @property
    def root_hash(self) -> str:
        # get image root hash, if self is root, get self hash
        if not self.root: return self.hash
        return self.root.hash
