'''
Initialized for the Grafana development environment tool.
'''
import os
from pathlib import Path


def load_version(fname: str) -> str:
    '''Load the module version from a __version__ file.

    This should follow semantic version 2.0 guidelines.

    For more information see
    https://packaging.python.org/guides/single-sourcing-package-version/

    Args:
        fname - The version file name.

    Returns:
        contents: The version which is the content of the file.

    Raises:
        FileNotFoundError: If the __version__ file does not exist.
    '''
    path = Path(Path(__file__).parent, fname)
    with open(path, 'r', encoding='utf-8') as ifp:
        return ifp.read().strip()


# Allows the user to access the version via: <package>.grape.__version__.
__version__ = load_version('__version__')
__module_path__ = os.path.abspath(Path(__file__).parent)
