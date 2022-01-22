import logging
import sys
from enum import Enum


def setup_logger(verbosity: int = 0) -> logging.Logger:
    """Setup the `Stabiliser` logger. Verbosity is set to value assigned to `verbosity`.

    Parameters:
         verbosity: Logger level.

    Returns:
        The configured logger.
    """
    logformat = '[%(asctime)s] %(name)s - %(levelname)s: %(message)s'
    logging.basicConfig(
        level=verbosity, stream=sys.stdout, format=logformat, datefmt='%Y-%m-%d %H:%M:%S')
    logging.captureWarnings(capture=True)
    return logging.getLogger('Stabiliser')


class Enumeration(Enum):
    def __str__(self) -> str:
        """Overrides __str__ to simplify comparisons.

        Returns:
            Current value as string.
        """
        return self.value


class Features(str, Enumeration):
    """Holds supported feature description modes."""
    GOOD_FEATURES = 'good_features'
    ORB = 'orb'
    SIFT = 'sift'
    SURF = 'surf'
    AKAZE = 'akaze'
    FAST = 'fast'
    MSER = 'mser'
    BRISK = 'brisk'
