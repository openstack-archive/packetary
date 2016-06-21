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

import mock

from packetary.controllers import PackagingController
from packetary.drivers.base import PackagingDriverBase

from packetary.tests import base


class TestPackagingController(base.TestCase):
    def setUp(self):
        super(TestPackagingController, self).setUp()
        self.driver = mock.MagicMock(spec=PackagingDriverBase)
        self.controller = PackagingController("contex", self.driver)

    @mock.patch("packetary.controllers.packaging.stevedore")
    def test_load_fail_if_unknown_driver(self, stevedore):
        stevedore.ExtensionManager.return_value = {}
        self.assertRaisesRegexp(
            NotImplementedError,
            "The driver unknown_driver is not supported yet.",
            PackagingController.load, "contex", "unknown_driver", "config"
        )

    @mock.patch("packetary.controllers.packaging.stevedore")
    def test_load_driver(self, stevedore):
        stevedore.ExtensionManager.return_value = {
            "test": mock.MagicMock(obj=self.driver)
        }
        PackagingController._drivers = None
        controller = PackagingController.load("context", "test", "config")
        self.assertIs(self.driver, controller.driver)
        stevedore.ExtensionManager.assert_called_once_with(
            "packetary.packaging_drivers", invoke_on_load=True,
            invoke_args=("config",)
        )

    def test_get_data_schema(self):
        self.driver.get_data_schema.return_value = {}
        self.assertIs(
            self.driver.get_data_schema.return_value,
            self.controller.get_data_schema()
        )
        self.driver.get_data_schema.assert_called_once_with()

    def test_build_packages(self):
        data = {'sources': '/sources'}
        output_dir = '/tmp/'
        callback = mock.MagicMock()
        self.controller.build_packages(data, output_dir, callback)
        self.driver.build_packages.assert_called_once_with(
            data, output_dir, callback
        )
