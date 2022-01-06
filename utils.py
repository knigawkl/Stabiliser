import logging
import sys


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
