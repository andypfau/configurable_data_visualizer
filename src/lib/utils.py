from typing import Any



def reverse_lookup(dict: dict, value: Any) -> Any:
    for k,v in dict.items():
        if v == value:
            return k
    raise ValueError(f'Value <{value}> not found')
