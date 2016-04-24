# -*- coding: utf-8 -*-

#    Copyright 2016 Mirantis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import functools
import inspect

import jsonschema


def _validate_data(data, schema):
    """Validate the input data using jsonschema validation.

    :param data: a data to validate represented as a dict
    :param schema: a schema to validate represented as a dict;
                   must be in JSON Schema Draft 4 format.
    """
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        _raise_validation_error("data", e.message, e.path)
    except jsonschema.SchemaError as e:
        _raise_validation_error("schema", e.message, e.schema_path)


def _raise_validation_error(what, details, path):
    message = "Invalid {0}: {1}.".format(what, details)
    if path:
        message += "\nField: [{0}]".format(
            "][".join(repr(p) for p in path)
        )
    raise ValueError(message)


def _build_validator(schema):
    # check that schema is method of class and expected self argument
    if callable(schema) and len(inspect.signature(schema).parameters) > 0:
        def validator(self, value):
            _validate_data(value, schema(self))
    elif callable(schema):
        def validator(_, value):
            _validate_data(value, schema())
    else:
        def validator(_, value):
            return _validate_data(value, schema)
    return validator


def declare_schema(**schemas):
    """Declares data schema for function arguments.

    :param schemas: the mapping, where key is argument name, value is schema
                    the schema may be callable object or method of class
                    in this case the wrapped function should be method of
                    same class
    :raises ValueError: if the passed data does not fit declared schema
    """

    def decorator(func):
        validators = {k: _build_validator(v) for k, v in schemas.items()}
        func_signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound_args = func_signature.bind(*args, **kwargs)
            params = func_signature.parameters
            for n, v in bound_args.arguments.items():
                validator = v is not params[n].default and validators.get(n)
                validator and validator(args and args[0] or None, v)

            return func(*args, **kwargs)
        return wrapper
    return decorator
