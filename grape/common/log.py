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


def initv(verbose: int):
    '''
    Initialize the logger based on the level of verbosity:

        0 - logging.WARNING
        1 - logging.INFO
        2 - logging.DEBUG

    This is used by each of the apps rather than init().

    Args:
        verbose - the level of verbosity: [0..2]
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
    '''
    Initialize the logger.

    Args:
        level - The log level: logging.INFO, etc.
    '''
    global LOG  # pylint: disable=global-statement
    if not LOG is None:
        return
    formatter = logging.Formatter(FMT)

    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    LOG = logging.getLogger(NAME)
    LOG.setLevel(level)
    LOG.addHandler(stream)


def extra() -> dict:
    '''
    Define the extra for coloring.
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
    '''
    Print an info message.

    Args:
        msg - the message
        level - the stack level (default: parent)
    '''
    LOG.info(msg, stacklevel=level+1, extra=extra())


def warn(msg: str, level: int = 1):
    '''
    Print a warning message.

    Args:
        msg - the message
        level - the stack level (default: parent)
    '''
    LOG.warning(msg, stacklevel=level+1, extra=extra())


def debug(msg: str, level: int = 1):
    '''
    Print a debug message.
    Can't name it debug because that is reserved.

    Args:
        msg - the message
        level - the stack level (default: parent)
    '''
    LOG.debug(msg, stacklevel=level+1, extra=extra())


def err(msg: str, level: int = 1, xflag=True):
    '''
    Print an error message and exit

    Args:
        msg - the message
        level - the stack level (default: parent)
        xflag - if true, exit
    '''
    LOG.error(msg, stacklevel=level+1, extra=extra())
    if xflag:
        sys.exit(1)
