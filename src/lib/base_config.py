from __future__ import annotations

import json
import logging
import inspect
import typing
import enum
from typing import Self, Type, Any, overload



class BaseConfig:


    class Volatile:
        def __init__(self, wrapped: any):
            self.wrapped = wrapped


    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._serialized_member_types = {}
        obj._initial_member_values = {}
        members = {k: cls.__dict__[k] for k in cls.__annotations__.keys()}
        for name,typ in typing.get_type_hints(cls).items():
            initial = members[name]
            if isinstance(initial, BaseConfig.Volatile):
                obj._initial_member_values[name] = initial.wrapped
            else:
                obj._initial_member_values[name] = initial
                obj._serialized_member_types[name] = typ
        return obj


    def __init__(self, format_version_str: str = None):
        for name,value in self._initial_member_values.items():
            self.__dict__[name] = value
        self._format_version_str = format_version_str
    

    def __hash__(self):
        all_hashes = []
        for k in self._initial_member_values.keys():
            item = self.__dict__[k]
            if isinstance(item, list):
                all_hashes.append(hash(tuple([hash(subitem) for subitem in item])))
            elif isinstance(item, (str,int,float,complex,bool,enum.Enum,BaseConfig)):
                all_hashes.append(hash(item))
            elif item is None:
                all_hashes.append(-1)
            elif item is any:
                all_hashes.append(-2)
            else:
                pass  # cannot hash this type; ignore
        return hash(tuple(all_hashes))


    def save(self, path_or_fp):
        data = self._serialize()
        if hasattr(path_or_fp, 'write') and callable(path_or_fp.write):
            json.dump(data, path_or_fp, indent=4)
        else:
            with open(path_or_fp, 'w') as fp:
                json.dump(data, fp, indent=4)
            


    @classmethod
    def load(cls, path_or_fp) -> Self:
        if hasattr(path_or_fp, 'read') and callable(path_or_fp.read):
            data = json.load(path_or_fp)
        else:
            with open(path_or_fp, 'r') as fp:
                data = json.load(fp)
        return cls._deserialize(data)

    
    def _serialize(self) -> dict:
        data = dict()
        
        if self._format_version_str:
            data['file_format'] = self._format_version_str

        def serialize(obj, typ):
            if issubclass(typ, BaseConfig):
                return obj._serialize()
            else:  # plain data
                return obj

        for name in self._serialized_member_types.keys():
            if typing.get_origin(self._serialized_member_types[name]) is list:
                serialized = [serialize(element,typing.get_args(self._serialized_member_types[name])[0]) for element in self.__dict__[name]]
            else:
                serialized = serialize(self.__dict__[name],self._serialized_member_types[name])
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

        expected_keys = set(obj._serialized_member_types.keys())
        found_keys = set([k for k in data.keys() if k!='file_format'])

        missing_keys = expected_keys - found_keys
        excess_keys = found_keys - expected_keys
        used_keys = found_keys & expected_keys
        if len(missing_keys) > 0:
            logging.warning(f'The following settings were not found in the loaded file: {missing_keys}; ignoring')
        if len(excess_keys) > 0:
            logging.warning(f'The following settings were found in the loaded file, but are unknown: {excess_keys}; ignoring')

        def deserialize(data, typ):
            if issubclass(typ, BaseConfig):
                return typ._deserialize(data)
            else:  # plain data
                if typ is typing.Any:
                    return data
                try:
                    return typ(data)
                except Exception as ex:
                    logging.warning(f'Cannot cast >{data}> to <{typ}> for config "{name}"; ignoring')
                    return None

        for name in used_keys:

            if typing.get_origin(obj._serialized_member_types[name]) is list:
                deserialized = [deserialize(element,typing.get_args(obj._serialized_member_types[name])[0]) for element in data[name]]
            else:
                deserialized = deserialize(data[name],obj._serialized_member_types[name])
            
            if deserialized is not None:
                obj.__dict__[name] = deserialized
    
        return obj
