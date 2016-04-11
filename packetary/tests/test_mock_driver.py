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
from packetary.tests import base
from packetary.drivers.packaging_mock import MockDriver

mock_releases = ["centos-6-x86_64", "centos-7-x86_64"]


class MockDriverOverride(MockDriver):
    """
    Override for get_chroots & find_system_mock
    """

    @staticmethod
    def get_chroots(path_to_configs=None):
        return mock_releases

    @staticmethod
    def find_system_mock(mock_path='/usr/bin/mock'):
        return "/usr/bin/mock"


class TestMockDriver(base.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMockDriver, cls).setUpClass()
        cls.sys_execute = mock.MagicMock()
        cls.driver = MockDriverOverride()
        cls.driver.logger = mock.MagicMock()

    def setUp(self):
        self.sys_execute.reset_mock()

    def test_check_release_fail(self):
        with self.assertRaisesRegexp(
                ValueError,
                'There is no "centos-10-x86_64"'):
            self.driver.check_release("centos-10-x86_64")

    def test_check_release_success(self):
        self.assertIsNone(self.driver.check_release(mock_releases[0]))

    @mock.patch("os.path.exists")
    def test_build_srpm_sources_not_exists(self, m_path):
        m_path.return_value = False
        with self.assertRaisesRegexp(
                ValueError,
                """Sources exists "/path/to/fake/sources" ?"""):
            self.driver.build_srpm(
                mock_releases[0],
                "/path/to/fake/sources/"
                )

    @mock.patch("os.path.exists")
    @mock.patch("glob.glob")
    def test_build_srpm_spec_empty(self, m_glob, m_path):
        m_path.return_value = True
        m_glob.return_value = []
        with self.assertRaisesRegexp(
                ValueError,
                "There is no spec file in sources, please specify it"):
            self.driver.build_srpm(
                mock_releases[0],
                "/path/to/fake/sources/"
                )

    @mock.patch("os.path.exists")
    @mock.patch("glob.glob")
    def test_build_srpm_no_spec_exists(self, m_glob, m_path):
        m_path.return_value = True
        m_glob.return_value = []
        with self.assertRaisesRegexp(
                ValueError,
                "There is no spec file in sources, please specify it"):
            self.driver.build_srpm(
                mock_releases[0],
                "/path/to/fake/sources/"
                )

    @mock.patch("os.path.exists")
    @mock.patch("os.path.isdir")
    def test_build_srpm_resultdir_not_exists(self, m_isdir, m_exists):
        m_exists.return_value = True
        m_isdir.return_value = False
        with self.assertRaisesRegexp(
                ValueError,
                """Result dir "/path/to/fake/resultdir" not exists"""):
            self.driver.build_srpm(
                mock_releases[0],
                "/path/to/fake/sources/",
                "fake.spec",
                "/path/to/fake/resultdir"
                )

    @mock.patch("os.path.exists")
    @mock.patch("os.path.isdir")
    @mock.patch.object(MockDriver, "sys_execute")
    def test_build_srpm_success(self, m_execute, m_isdir, m_exists):
        m_isdir.return_value = True
        m_exists.return_value = True
        self.driver.build_srpm(
            mock_releases[0],
            "/path/to/fake/sources",
            "./fake/spec",
            "./fake/resultdir"
            )

        test_command = self.driver.srpm_template.format(
            self.driver.mock_bin,
            mock_releases[0],
            "./fake/resultdir",
            "/path/to/fake/sources",
            "./fake/spec"
        )
        self.driver.sys_execute.assert_called_with(test_command)

    @mock.patch("os.path.isfile")
    def test_build_rpm_empty_srpms(self, m_isfile):
        m_isfile.return_value = False
        with self.assertRaisesRegexp(ValueError, "There is no valid srpms"):
            self.driver.build_rpm(
                mock_releases[0],
                ["/fake/package.srpm"]
                )

    @mock.patch("os.path.isfile")
    @mock.patch("os.path.isdir")
    def test_build_rpm_resultdir_not_exists(self, m_isdir, m_isfile):
        m_isfile.return_value = True
        m_isdir.return_value = False
        with self.assertRaisesRegexp(
                ValueError,
                """Result dir "/path/to/fake/resultdir" not exists"""):
            self.driver.build_rpm(
                mock_releases[0],
                ["/fake/package.srpm"],
                "/path/to/fake/resultdir"
                )

    @mock.patch("os.path.isfile")
    @mock.patch("os.path.isdir")
    @mock.patch.object(MockDriver, "sys_execute")
    def test_build_rpm_success(self, m_execute, m_isdir, m_isfile):
        m_isfile.return_value = True
        m_isdir.return_value = True
        self.driver.build_rpm(
            mock_releases[0],
            ["/fake/package.srpm"],
            "/path/to/fake/resultdir"
            )

        test_command = self.driver.rpm_template.format(
            self.driver.mock_bin,
            mock_releases[0],
            "/path/to/fake/resultdir",
            "/fake/package.srpm"
        )
        self.driver.sys_execute.assert_called_with(test_command)
