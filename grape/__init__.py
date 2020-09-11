'''
Initialized for the Grafana development environment tool.
'''
import os
from pathlib import Path


def load_version(fname: str) -> str:
    '''
    Load the module version from a __version__ file.

    This should follow semantic version 2.0 guidelines.

    See: https://packaging.python.org/guides/single-sourcing-package-version/

    Args:
        fname - The version file name.

    Returns:
        The contents.
    '''
    with open(Path(Path(__file__).parent, fname)) as ifp:
        return ifp.read().strip()


# Allows the user to access the version via: <package>.grape.__version__.
__version__ = load_version('__version__')
__module_path__ = os.path.abspath(Path(__file__).parent)
