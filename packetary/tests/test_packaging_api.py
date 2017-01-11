#    Copyright 2015 Mirantis, Inc.
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

from packetary import api
from packetary import controllers

from packetary.tests import base
from packetary.tests.stubs import helpers


class TestPackagingApi(base.TestCase):
    def setUp(self):
        super(TestPackagingApi, self).setUp()
        self.controller = helpers.CallbacksAdapter(
            spec=controllers.PackagingController
        )
        self.controller.get_data_schema.return_value = {}
        self.api = api.PackagingApi(self.controller)

    @mock.patch("packetary.api.packaging.Context", autospec=True)
    @mock.patch("packetary.api.packaging.PackagingController", autospec=True)
    @mock.patch("packetary.api.packaging.isinstance",
                new=mock.MagicMock(return_value=False), create=True)
    def test_create_with_config(self, controller_mock, context_mock):
        config = mock.MagicMock()
        api.PackagingApi.create(config, "test_driver", "driver_config")
        context_mock.assert_called_with(config)
        controller_mock.load.assert_called_with(
            context_mock.return_value, "test_driver", "driver_config"
        )

    @mock.patch("packetary.api.packaging.Context", autospec=True)
    @mock.patch("packetary.api.packaging.PackagingController", autospec=True)
    @mock.patch("packetary.api.packaging.isinstance",
                new=mock.MagicMock(return_value=True), create=True)
    def test_create_with_context(self, controller_mock, context_mock):
        context = mock.MagicMock()
        api.PackagingApi.create(context, "test_driver", "driver_config")
        controller_mock.load.assert_called_with(
            context, "test_driver", "driver_config"
        )
        self.assertEqual(0, context_mock.call_count)

    @mock.patch("packetary.api.validators.jsonschema")
    @mock.patch("packetary.api.packaging.os")
    @mock.patch("packetary.api.packaging.utils")
    def test_build_packages(self, utils_mock, os_mock, jsonschema_mock):
        data = [
            {'sources': '/sources1'},
            {'sources': '/sources2'}
        ]
        output_dir = '/tmp'
        self.controller.build_packages.side_effect = [
            ['package1.src', 'package1.bin'],
            ['package2.src', 'package2.bin']
        ]
        packages = self.api.build_packages(data, output_dir)
        self.assertEqual(
            ['package1.src', 'package1.bin', 'package2.src', 'package2.bin'],
            packages
        )
        os_mock.path.abspath.assert_called_once_with(output_dir)
        utils_mock.ensure_dir_exist.assert_called_once_with(
            os_mock.path.abspath.return_value
        )
        jsonschema_mock.validate.assert_called_with(
            data,
            {
                'items': self.controller.get_data_schema.return_value,
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'type': 'array'
            }
        )
