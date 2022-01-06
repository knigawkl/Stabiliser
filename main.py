import sys
import argparse

from stabiliser import Stabiliser
from utils import setup_logger, Features


def get_parser() -> argparse.ArgumentParser:
    """Parse command line parameters for the `Stabiliser` console script.

    Returns:
        Parser object, which is used for processing command line arguments.
    """
    parser_desc = '\nPerforms video stabilisation.'
    parser = argparse.ArgumentParser(
        description=parser_desc, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '--smoothing_radius',
        dest='smoothing_radius',
        type=int,
        required=False,
        default=50,
        help='The larger the radius the more stable the video, but less reactive to sudden panning.'
    )
    parser.add_argument(
        '--input_path',
        dest='input_path',
        type=str,
        required=False,
        default='video/video.mp4',
        help='Path to the input video.'
    )
    parser.add_argument(
        '--output_path',
        dest='output_path',
        type=str,
        required=False,
        default='video/out.mp4',
        help='Path to the output video.'
    )
    parser.add_argument(
        '--features',
        dest='features',
        type=str,
        choices=list(Features),
        required=False,
        default=Features.GOOD_FEATURES,
        help='Keypoint detector type.'
    )
    return parser


if __name__ == '__main__':

    args: argparse.Namespace = get_parser().parse_args(sys.argv[1:])

    Stabiliser(
        logger=setup_logger(),
        smoothing_radius=args.smoothing_radius,
        features=args.features
    ).stabilise(  # todo: test on different videos
        input_path=args.input_path,  # todo: get better results on the piano video
        output_path=args.output_path
    )
    # todo: compare our method with smartphone stabilisation or any application (Google Photos?)
