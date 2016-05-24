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
from packetary.drivers.base_packaging import PackagingDriverBase
from packetary.tests import base


class TestPackagingController(base.TestCase):
    def setUp(self):
        self.driver = mock.MagicMock(spec=PackagingDriverBase)
        self.context = mock.MagicMock()
        self.ctrl = PackagingController("rpm")

    def test_load_fail_if_unknown_driver(self):
        with self.assertRaisesRegexp(
                NotImplementedError,
                "The driver fake_driver is not supported yet"):
            PackagingController.load(
                "fake_driver"
            )

    @mock.patch("packetary.controllers.packaging.stevedore")
    def test_load_driver(self, stevedore):
        stevedore.ExtensionManager.return_value = {
            "test": mock.MagicMock(obj=self.driver)
        }
        PackagingController._drivers = None
        controller = PackagingController.load("test")
        self.assertIs(self.driver, controller.driver)

    @mock.patch("packetary.controllers.PackagingController.build_packages")
    def test_build_packages(self, m_buildp):
        params = ['release', 'sources', 'spec_file']
        self.driver.build_packages(*params)
        self.driver.build_packages.assert_called_with(*params)
