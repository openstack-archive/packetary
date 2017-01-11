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

import mock

from jsonschema import SchemaError
from jsonschema import ValidationError

from packetary.api import validators

from packetary.tests import base


@mock.patch('packetary.api.validators.jsonschema',
            ValidationError=ValidationError, SchemaError=SchemaError)
class TestDataValidators(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {'key': 'value'}
        cls.schema = {'type': 'object'}

    def test_validate_data(self, jsonschema_mock):
        validators._validate_data(self.data, self.schema)
        jsonschema_mock.validate.assert_called_once_with(
            self.data, self.schema
        )

    def test_validate_invalid_data(self, jsonschema_mock):
        paths = [(("a", 0), "\['a'\]\[0\]"), ((), "")]
        for path, details in paths:
            msg = "Invalid data: error."
            if details:
                msg += "\nField: {0}".format(details)
            with self.assertRaisesRegexp(ValueError, msg):
                jsonschema_mock.validate.side_effect = ValidationError(
                    "error", path=path
                )
                validators._validate_data(self.data, self.schema)

            msg = "Invalid schema: error."
            if details:
                msg += "\nField: {0}".format(details)
            with self.assertRaisesRegexp(ValueError, msg):
                jsonschema_mock.validate.side_effect = SchemaError(
                    "error", schema_path=path
                )
                validators._validate_data(self.data, self.schema)

    def test_build_validator(self, jsonschema_mock):
        schemas = [
            lambda this: this.schema,
            lambda: self.schema,
            self.schema
        ]
        for schema in schemas:
            jsonschema_mock.reset()
            validator = validators._build_validator(schema)
            validator(self, self.data)
            jsonschema_mock.validate.assert_called_with(self.data, self.schema)

    def test_declare_schema_default_does_not_check(self, jsonschema_mock):
        func = validators.declare_schema(p=self.schema)(lambda p=None: None)
        func(None)
        self.assertEqual(0, jsonschema_mock.validate.call_count)

    def test_declare_schema_check_data(self, jsonschema_mock):
        func = validators.declare_schema(p=self.schema)(lambda p: None)
        func(self.data)
        jsonschema_mock.validate.assert_called_with(self.data, self.schema)

    def test_declare_schema_if_schema_is_method(self, jsonschema_mock):
        func = validators.declare_schema(p=lambda x: x.schema)(
            lambda x, p: None
        )
        func(self, self.data)
        jsonschema_mock.validate.assert_called_with(self.data, self.schema)
