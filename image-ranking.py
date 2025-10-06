
import time
import argparse
import logging
import os

from pathlib import Path

from image_ranking.core import Core   


# setup logging
logging.basicConfig(
    level=logging.INFO,  # Default level
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


# main process
def main(args: argparse.Namespace):
    
    # get image directory
    directory = args.directory
    if not os.path.isabs(directory):
        directory = Path(__file__).resolve().parent / directory
    if not os.path.isdir(directory):
        logging.error(f"directory: {directory} is not a valid directory")
        exit(1)
    args.directory = directory
    logging.info(f"directory: {directory}")

    # fix me - show current options here

    # initialize Ranking class
    core = Core(args)

    # get and hash images
    start_time = time.time()
    core.get_and_hash_images()
    end_time = time.time()
    logging.debug(f"get_and_hash_images executed in {end_time - start_time:.2f} seconds")

    # group images
    start_time = time.time()
    core.group()
    end_time = time.time()
    logging.debug(f"group executed in {end_time - start_time:.2f} seconds")

    # calculate blur for each image
    start_time = time.time()
    core.calculate_blur()
    end_time = time.time()
    logging.debug(f"calculate_blur executed in {end_time - start_time:.2f} seconds")

    # process groups
    start_time = time.time()
    core.apply_ratings()
    end_time = time.time()
    logging.debug(f"apply_ratings executed in {end_time - start_time:.2f} seconds")


# main entry point
if __name__ == '__main__':
    start_time = time.time()

    # parse command line arguments
    parser = argparse.ArgumentParser(description='run blur detection on a single image')

    default_threads = os.cpu_count() if os.cpu_count() else 4

    parser.add_argument('directory', type=str, help='directory of images')

    parser.add_argument('-f', '--feature_matching', action='store_true', help='feature matching mode')
    parser.add_argument('-e', '--exclude', action='store_true', help='exclude files with existing xmp')

    parser.add_argument('-d', '--diff', metavar='float', type=float, default=0, help='image difference threshold')

    parser.add_argument('-m', '--max_rank', metavar='int', type=int, default=3, help='max image rank (1 to 5)')
    parser.add_argument('-t', '--threads', metavar='int', type=int, default=default_threads, help='number of threads')

    parser.add_argument('-r', '--resize', metavar='touple (x,y)', type=tuple, default=None, help='resize image dimension')

    parser.add_argument('--cv2_min_contour_area', metavar='int', type=int, default=500, help='cv2 minimum contour area for similarity comparison')
    parser.add_argument('--cv2_crop', metavar='int', default=5, help='cv2 crop mask (in %) to apply on the image')
    parser.add_argument('--cv2_gaussian_blur_radius', type=str, nargs='+', default=[None], help='cv2 list of radii for Gaussian blur')
    parser.add_argument('--cv2_delta_threshold', metavar='int', type=int, default=25, help='cv2 delta threshold for similarity comparison')
    
    parser.add_argument('-v', '--verbose', action='store_true', help='set logging level to debug')
    #parser.add_argument('-d', '--display', action='store_true', help='display images')
    
    # show help if no args
    import sys
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(1) 

    # parse args
    args = parser.parse_args();

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # conditional defaults
    if args.diff <= 0:
        if args.feature_matching:
            args.diff = 0.4
        else:
            args.diff = 0.9
    if args.resize is None:
        if args.feature_matching:
            args.resize = ('quarter', 'quarter')
        else:
            args.resize = (196, 144)

    # run main process
    try:
        main(args)

    except KeyboardInterrupt:
        logging.warning("process interrupted by user")

    # end 
    end_time = time.time()
    logging.info(f"execution time {end_time - start_time:.2f} seconds")
