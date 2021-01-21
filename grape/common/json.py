'''
Some local JSON utilities.
'''
import json
from grape.common.log import err


def read_json_dict_from_file(path: str) -> dict:
    '''Read JSON file that is a dictionary.

    It must start with a '{'.

    If the read fails, an error is reported and the program halts.

    This function is used by the dashin and dashout commands.

    Args:
        path: The JSON file.

    Return:
        dict: The JSON data.
    '''
    value = {}
    try:
        with open(path) as ifp:
            data = ifp.read()
            if data.startswith('['):
                err(f'input dashboard json file is a list not a map: "{path}"')
            if not data.startswith('{'):
                # It must be a dictionary.
                err(f'input dashboard json file is not a map: "{path}"')
        value = json.loads(data)
    except FileNotFoundError:
        err(f'input dashboard json file does not exist: "{path}"')
    except json.decoder.JSONDecodeError as exc:
        err(f'input dashboard json file is invalid: "{path}" - {exc}')
    return value
