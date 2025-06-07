import json
import logging
from typing import Callable, Self



class BaseConfig:


    def __init__(self, format_version_str: str = None):
        self._format_version_str = format_version_str


    def save(self, path: str):
        data = self._serialize()
        with open(path, 'w') as fp:
            json.dump(data, fp, indent=4)


    @classmethod
    def load(cls, path: str) -> Self:
        with open(path, 'r') as fp:
            data = json.load(fp)
        result = cls()
        result._deserialize(data)
        return result

    
    def _serialize(self) -> dict:
        data = dict()
        
        if self._format_version_str:
            data['file_format'] = self._format_version_str

        for name,value in self.__dict__.items():
            if name.startswith('_'):
                continue
            if isinstance(value, BaseConfig):
                data[name] = value._serialize()
            else:
                data[name] = value
        
        return data

    
    def _deserialize(self, data: dict):
        if self._format_version_str:
            if 'file_format' in data:
                file_format_version_str = data['file_format']
                if file_format_version_str != self._format_version_str:
                    logging.warning(f'Expected file format "{self._format_version_str}", but loaded file contains "{file_format_version_str}", ignoring')
            else:
                logging.warning(f'File format not specified in loaded file (expected "{self._format_version_str}"), ignoring')

        expected_keys = set([k for k in self.__dict__.keys() if not k.startswith('_')])
        found_keys = set([k for k in data.keys() if k!='file_format'])

        missing_keys = expected_keys - found_keys
        excess_keys = found_keys - expected_keys
        used_keys = found_keys & expected_keys
        if len(missing_keys) > 0:
            logging.warning(f'The following settings were not found in the loaded file: {missing_keys}; ignoring')
        if len(excess_keys) > 0:
            logging.warning(f'The following settings were found in the loaded file, but are unknown: {excess_keys}; ignoring')

        for name in used_keys:
            value = data[name]
            if isinstance(self.__dict__[name], BaseConfig):
                self.__dict__[name]._deserialize(value)
            else:
                self.__dict__[name] = value
