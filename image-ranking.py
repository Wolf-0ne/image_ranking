
import time
import argparse
import logging
import os

from logging.handlers import MemoryHandler

from pathlib import Path

from image_ranking.core import Core

# create formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s',
                      datefmt='%H:%M:%S'))

# create memory buffer
buffer_handler = MemoryHandler(
    capacity=10000,
    flushLevel=logging.INFO,
    target=console_handler
)

# setup logging
logging.basicConfig(
    handlers=[buffer_handler],
    level=logging.INFO  # Default level
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

    # init
    start_time = time.time()
    default_threads = os.cpu_count() if os.cpu_count() else 4

    # parse command line arguments
    parser = argparse.ArgumentParser(description='run blur detection on a single image')

    parser.add_argument('directory', type=str, help='directory of images')

    parser.add_argument('-f', '--feature_matching', action='store_true',
                        help='feature matching mode')
    parser.add_argument('-e', '--exclude', action='store_true',
                        help='exclude files with existing xmp')

    parser.add_argument('-d', '--diff', metavar='float', type=float, default=0,
                        help='image difference threshold')

    parser.add_argument('-m', '--max_rank', metavar='int', type=int, default=3,
                        help='max image rank (1 to 5)')
    parser.add_argument('-t', '--threads', metavar='int', type=int, default=default_threads,
                        help='number of threads')

    parser.add_argument('--similarity_resize', metavar='(width, height)', type=tuple, default=None,
                        help='similarity detection image size, supports keywords "half/third/quarter"')
    parser.add_argument('--similarity_crop', metavar='int', default=15,
                        help='similarity detection crop mask (in %)')
    parser.add_argument('--similarity_blur', metavar='[5]', type=str, nargs='+', default=[5],
                        help='List of radii for Gaussian blur applied before similarity detection')
    parser.add_argument('--similarity_min_contour', metavar='int', type=int, default=500,
                        help='Similarity minimum contour area')
    parser.add_argument('--similarity_delta', metavar='int', type=int, default=25,
                        help='Similarity delta threshold')

    parser.add_argument('--blur_mode', metavar='str', default='sum_modified_laplacian',
                        help='blur detection algorithm (sum_modified_laplacian, sobel, laplacian)')
    parser.add_argument('--blur_crop', metavar='int', default=30,
                        help='blur detection crop mask (in %)')
    parser.add_argument('--blur_resize', metavar='(width, height)', type=tuple, default=None,
                        help='blur detection image size, supports keywords "half/third/quarter"')

    parser.add_argument('-v', '--verbose', action='store_true', help='set logging level to debug')

    # show help if no args
    import sys
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(1)

    # parse args
    args = parser.parse_args();

    # debug
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # conditional defaults
    if args.diff <= 0:
        if args.feature_matching:
            args.diff = 0.4
        else:
            args.diff = 0.6
    if args.similarity_resize is None:
        if args.feature_matching:
            args.similarity_resize = ('quarter', 'quarter')
        else:
            args.similarity_resize = (144, 196)
    if args.blur_resize is None:
       args.blur_resize = ('half', 'half')

    # run main process
    try:
        main(args)

    except KeyboardInterrupt:
        logging.warning("process interrupted by user")

    # end
    end_time = time.time()
    logging.info(f"execution time {end_time - start_time:.2f} seconds")
