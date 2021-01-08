'''
Logging module.
'''
import inspect
import logging
import sys


# Note the we cannot use the default logging logger because
# other packages like requests also use it which leads to
# a conflict because we use extra settings.
LOG = None

# The log name.
NAME = 'grape'

# Colors for different levels.
COLORS = {
    'info': '\x1b[34m',
    'warn': '\x1b[31m',
    'debug': '\x1b[35m',
    'err': '\x1b[31m',
}

# Allow color to be enabled or disabled.
COLOR = True

# The format.
# Note the use of custom format variables: prefix and suffix.
FMT = '%(prefix)s%(levelname)s %(asctime)s %(filename)s:%(lineno)s - %(message)s%(suffix)s'

# Cached level.
LEVEL = logging.WARNING


def initv(verbose: int):
    '''Initialize the logger based on the level of verbosity.

    It maps the CLI verbosity to logging levels.

        0 - logging.WARNING
        1 - logging.INFO
        2 - logging.DEBUG

    This is used by each of the apps rather than init().

    Args:
        verbose: The level of verbosity: [0..2].
    '''
    if verbose == 0:
        init(logging.WARNING)
    elif verbose == 1:
        init(logging.INFO)
    elif verbose > 1:
        init(logging.DEBUG)
    else:
        sys.stderr.write('\x1b[31mERROR: logging initv failure, '
                         'expected a number in the range [0..2] '
                         f'but found {verbose}'
                         '\x1b[0m\n')
        sys.exit(1)


# Initialize.
def init(level: int):
    '''Initialize the logger.

    Args:
        level: The log level: logging.INFO, etc.
    '''
    global LOG, LEVEL  # pylint: disable=global-statement
    if not LOG is None:
        for hnd in LOG.handlers:
            LOG.removeHandler(hnd)
    LEVEL = level  # cache
    formatter = logging.Formatter(FMT)

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    LOG = logging.getLogger(NAME)
    LOG.setLevel(level)
    LOG.addHandler(stream)


def extra() -> dict:
    '''Define the extra for coloring.

    This allows color to be introduced to the standard logger.
    '''
    assert LOG is not None
    caller = inspect.stack()[1].function
    if COLOR:
        xtra = {'prefix': COLORS[caller],
                 'suffix': '\x1b[0m'}
    else:
        xtra = {'prefix': '',
                 'suffix': ''}
    return xtra


def info(msg: str, level: int = 1):
    '''Print an info message.

    Info messages will be invisible unless the
    logging level includes logging.INFO.

    Args:
        msg: The message.
        level: The stack level (default: parent).
    '''
    assert LOG  # make sure LOG is initialized
    try:
        LOG.info(msg, stacklevel=level+1, extra=extra())
    except ValueError:  # recover from pylint IO issue
        init(LEVEL)
        LOG.info(msg, stacklevel=level+1, extra=extra())


def warn(msg: str, level: int = 1):
    '''Print a warning message.

    Args:
        msg: The message.
        level: The stack level (default: parent).
    '''
    assert LOG  # make sure LOG is initialized
    try:
        LOG.warning(msg, stacklevel=level+1, extra=extra())
    except ValueError:  # recover from pylint IO issue
        init(LEVEL)
        LOG.warning(msg, stacklevel=level+1, extra=extra())


def debug(msg: str, level: int = 1):
    '''Print a debug message.

    Debug messages will be invisible unless the
    logging level includes logging.DEBUG.

    Args:
        msg: The message.
        level: The stack level (default: parent).
    '''
    assert LOG  # make sure LOG is initialized
    try:
        LOG.debug(msg, stacklevel=level+1, extra=extra())
    except ValueError:  # recover from pylint IO issue
        init(LEVEL)
        LOG.debug(msg, stacklevel=level+1, extra=extra())


def err(msg: str, level: int = 1, xflag=True, xcode=1):
    '''
    Print an error message and exit

    Args:
        msg: The message.
        level: The stack level (default: parent).
        xflag: If true, exit. The default is to exit.
        xcode: The exit code. The default is 1.
    '''
    assert LOG  # make sure LOG is initialized
    try:
        LOG.error(msg, stacklevel=level+1, extra=extra())
    except ValueError:  # recover from pylint IO issue
        init(LEVEL)
        LOG.error(msg, stacklevel=level+1, extra=extra())
    if xflag:
        logging.shutdown()
        sys.exit(xcode)
