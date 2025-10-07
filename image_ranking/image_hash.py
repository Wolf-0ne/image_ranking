
import hashlib
import cv2
import logging
import numpy

from image_ranking.cv2_image_hash import cv2_process_image, cv2_compare_image, cv2_crop, cv2_resize
from image_ranking.image_similarity import image_similarity


class ImageHash:

    """
    Image to group class
    """
    def __init__(self, filename: str, path: str, content_type: str, args):

        # save args
        self.args = args

        # image original path
        self.path = path

        # image filename
        self.filename = filename

        # image mime type
        self.content_type = content_type

        # cv2 processed image
        self.processed_image = cv2_process_image(path, self.raw, args)

        # save image shape
        self.shape = args.similarity_resize
        if self.processed_image.shape is not None:
            self.shape = self.processed_image.shape

        # hash image content
        self.hash = hashlib.md5(str(self.processed_image).encode()).hexdigest()

        # image blur value
        self.blur = None

        # image rank
        self.rank = 0

        # similarity data
        self.similar = []
        
        # parent image ref
        self.root = None

        #logging.debug(f"  {self.filename} ###")


    def is_same_group(self, anotherImage) -> bool:

        score = 0
        result = False

        # feature matching
        if self.args.feature_matching:
            score = image_similarity(self.processed_image, anotherImage.processed_image)
            result = score >= self.args.diff

        # cv2 hash compare
        else:
            score, res_cnts, thresh = cv2_compare_image(self.processed_image, anotherImage.processed_image, self.args)
            result = score < self.shape[0] * self.shape[1] * self.args.diff #delta is rougly number of total pixels

        # save similarity data
        self.similar.append((anotherImage.filename, score, result))
        
        # return compare result
        return result
    

    def calculate_blur(self):
        try:

            # read image
            image = cv2.imread(str(self.path))
            if image is None:
                logging.warning(f'warning! failed to read image from {self.path}; skipping!')
                return
            
            # resize and crop
            image = cv2_resize(image, self.args.blur_resize) # resize to speed up processing
            image = cv2_crop(image, self.args.blur_crop) # crop border for better central blur detection

            # estimate blur
            mode = str(self.args.blur_mode).lower()
            match mode:

                # Laplacian
                case "laplacian":
                    blur_map = cv2.Laplacian(image, cv2.CV_64F)
                    score = numpy.var(blur_map)

                # Tenengrad (Sobel)
                case "sobel":
                    sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
                    sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
                    tenengrad = numpy.sqrt(sobelx**2 + sobely**2)
                    score = numpy.mean(tenengrad)

                # Sum Modified Laplacian
                # in my test data so far, SML seems to line up with Sobel results regularly 
                # and is on par with Laplacian performance
                case _:
                    M = numpy.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])
                    score = numpy.abs(cv2.filter2D(image, cv2.CV_64F, M)).sum()

            # set attributes
            self.blur = score

            return True

        except Exception as e:
            logging.error(f"error calculating blur for {self.path}: {e}")

        return False


    @property
    def root_hash(self) -> str:
        # get image root hash, if self is root, get self hash
        if not self.root: return self.hash
        return self.root.hash
    