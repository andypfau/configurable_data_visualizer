import json
import logging
import inspect
from typing import Self, Type, Any, overload



class BaseConfig:


    class ConfigList(list):
        
        def __init__(self, type: Type):
            assert issubclass(type, BaseConfig)
            self._type: Type = type
        
        @property
        def type(self) -> Type:
            return self._type


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
        return cls._deserialize(data)

    
    def _serialize(self) -> dict:
        data = dict()
        
        if self._format_version_str:
            data['file_format'] = self._format_version_str

        for name,value in self.__dict__.items():
            if name.startswith('_'):
                continue
            
            if isinstance(value, BaseConfig):
                serialized = value._serialize()
            elif isinstance(value, BaseConfig.ConfigList):
                serialized = [elem._serialize() for elem in value]
            else:
                serialized = value
            data[name] = serialized
        
        return data

    
    @classmethod
    def _deserialize(cls, data: dict):
        obj = cls()

        if obj._format_version_str:
            if 'file_format' in data:
                file_format_version_str = data['file_format']
                if file_format_version_str != obj._format_version_str:
                    logging.warning(f'Expected file format "{obj._format_version_str}", but loaded file contains "{file_format_version_str}", ignoring')
            else:
                logging.warning(f'File format not specified in loaded file (expected "{obj._format_version_str}"), ignoring')

        expected_keys = set([k for k in obj.__dict__.keys() if not k.startswith('_')])
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
            initial = obj.__dict__[name]
            
            if isinstance(initial, BaseConfig):
                deserialized = initial._deserialize(value)
            elif isinstance(initial, BaseConfig.ConfigList):
                items = [initial.type()._deserialize(elem) for elem in value]
                initial.extend(items)
                deserialized = initial
            else:
                deserialized = value
            obj.__dict__[name] = deserialized
    
        return obj
