
import argparse
import concurrent.futures
import logging

from image_ranking.image_hash import ImageHash

from image_ranking.get_and_hash_images import get_and_hash_images
from image_ranking.darktable_set_rating import darktable_set_rating


# main process class
class Core(object):

    """
    Main process class
    Steps:
    1. get and hash images
    2. group images by hash / similarity
    3. calculate blur value for each image in the group
    4. iterate image groups, rank by blur value, update xmp rating
    """
    def __init__(self, args: argparse.Namespace):
        self.images_list = []
        self.args = args


    def get_and_hash_images(self):
        self.images_list = get_and_hash_images(self.args)


    def group(self):
        # group all image
        for i in range(0, len(self.images_list)):
            for j in range(i + 1, len(self.images_list)):

                i1 = self.images_list[i]
                i2 = self.images_list[j]

                # if i1 has no root and is same group, set i1 as i2's root
                if i1.is_same_group(i2):
                    if i1.root:
                        i2.root = i1.root
                    else:
                        i2.root = i1

                else: break
    

    def calculate_blur(self):
        
        # calculate blur in parallel
        def blur(image: ImageHash):
            image.calculate_blur()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.threads) as executor:
            executor.map(blur, self.images_list)


    def apply_ratings(self):

        # initialize
        image_group = list()
        previous_group_hash = None
        group_hash = None

        # iterate all images
        image: ImageHash
        for image in self.images_list:

            # set current group
            group_hash = image.root_hash

            # if group changed, apply ratings
            if group_hash != previous_group_hash:
                
                # process current group
                if previous_group_hash is not None:
                    self.apply_group_ratings(image_group, group_hash)

                # reset for new group
                previous_group_hash = group_hash
                image_group = list()

            # add image to current group
            image_group.append(image)

        # process last group
        self.apply_group_ratings(image_group, group_hash) 


    def apply_group_ratings(self, images: list, group_hash: str = None):

        # validate images array
        if len(images) == 0:
            return
        
        # debug print
        logging.debug(f"group: {group_hash}")

        # sort images
        images.sort(key=lambda x: x.blur, reverse=True)

        # set initial rank
        rank = self.args.max_rank

        # iterate images
        image: ImageHash
        for image in images:

            # set rank
            image.rank = rank
            
            # decrement rank
            if rank > 0: rank -= 1

            # debug print
            logging.debug(f"file: {image.filename} blur: {image.blur} rank: {image.rank}")
                
        #apply ratings in parallel
        def rate_image(image: ImageHash):
            darktable_set_rating(f"{image.path}.xmp", image.rank, True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.threads) as executor:
            executor.map(rate_image, images)
