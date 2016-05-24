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
import os
import subprocess

from packetary.drivers.packaging_sbuild import SbuildDriver
from packetary.tests import base

schroot_output = os.path.join(
    os.path.dirname(__file__),
    "data",
    "schroot_output.txt"
)

_chroot_parameters = [
    {
        "Name": "trusty-amd64-sbuild",
        "Type": "directory",
        "Directory": "/fake/path",
    },
    {
        "Name": "unstable-amd64-sbuild",
        "Type": "directory",
        "Directory": "/fake/path"
    },

]


class TestSbuildDriver(base.TestCase):

    @classmethod
    def setUpClass(cls):
        SbuildDriver.get_chroots = lambda x: _chroot_parameters
        SbuildDriver.find_system_mock = lambda x: "/usr/bin/sbuild"
        super(TestSbuildDriver, cls).setUpClass()
        cls.sys_execute = mock.MagicMock()
        cls.driver = SbuildDriver()
        cls.driver.logger = mock.MagicMock()

    def setUp(self):
        self.sys_execute.reset_mock()

    @mock.patch.object(SbuildDriver, "sys_execute")
    def test_get_chroots(self, m_execute):

        m_execute.return_value = schroot_output
        releases = self.driver.get_chroots()

        self.assertEqual(
            releases,
            _chroot_parameters
        )

    def test_sys_execute_exception(self):
        with self.assertRaisesRegex(
                ValueError,
                "Please specify command to execute"):
            self.driver.sys_execute(None)

    def test_sys_execute_command(self):
        subprocess.check_output = mock.create_autospec(
            subprocess.check_output,
            return_value='mocked'
        )
        self.assertEqual(
            self.driver.sys_execute('fake command'),
            'mocked'
        )

    @mock.patch.object(SbuildDriver, "sys_execute")
    def test_sys_execute_command_exception(self, m_execute):
        m_execute.side_effect = Exception("fail")

        with self.assertRaisesRegexp(
                ValueError,
                """Failed to create chroot fake."""):
            self.driver.create_chroot(
                "fake"
                )

    @mock.patch.object(SbuildDriver, "sys_execute")
    def test_create_chroot_command(self, m_execute):
        self.driver.create_chroot(
            "trusty",
            "http://fake/mirror/"
        )
        _command = self.driver.create_chroot_template.format(
            self.driver.chroot_components,
            "trusty",
            "http://fake/mirror/"
        )
        self.driver.sys_execute.assert_called_with(_command)

    def test_add_apt_sources_except_wrong_chroot(self):
        with self.assertRaisesRegex(
                ValueError,
                """Can't update fake chroot"""):
            self.driver.add_apt_sources(
                "fake",
                "http://fake/repo"
            )

    @mock.patch("os.path.isdir")
    def test_add_apt_sources_except_listd_dir(self, m_isdir):
        m_isdir.return_value = False
        with self.assertRaisesRegex(
                ValueError,
                "There is no apt sources.list.d in /fake"
                "/path/etc/apt/sources.list.d/"):
            self.driver.add_apt_sources(
                _chroot_parameters[0]["Name"],
                {
                    "type": "deb",
                    "url": "http://fake/repo",
                    "distribution": "trusty"
                }
            )

    @mock.patch.object(SbuildDriver, "sys_execute")
    @mock.patch("os.path.isdir")
    def test_add_apt_sources_open_config(self, m_isdir, m_execute):
        m_isdir.return_value = True
        m_execute.return_value = "mocked"
        m = mock.mock_open()
        with mock.patch("__builtin__.open", m, create=True):
            self.driver.add_apt_sources(
                _chroot_parameters[0]["Name"],
                {
                    "type": "deb",
                    "url": "http://fake/repo",
                    "distribution": "trusty",
                    "components": ["main"]
                }
            )

        handler = m()
        handler.write.assert_has_calls([
            mock.call("deb http://fake/repo trusty main"),
        ])

    @mock.patch("glob.glob")
    @mock.patch("os.path")
    @mock.patch("os.chdir")
    @mock.patch.object(SbuildDriver, "sys_execute")
    @mock.patch.object(SbuildDriver, "create_chroot")
    @mock.patch.object(SbuildDriver, "add_apt_sources")
    def test_build_deb_from_sources(
            self,
            m_add,
            m_create,
            sys_execute,
            m_chdir,
            m_path,
            m_glob):

        m_chdir.return_value = True
        self.driver.build_deb_from_sources(
            "trusty",
            "/fake/sources",
            "/fake/resultdir",
            []
        )
        sys_execute.assert_called_with(
            "sudo sbuild -d {1} -c {2}".format(
                "/fake/sources",
                "trusty",
                "trusty"
            )
        )

    @mock.patch.object(SbuildDriver, "build_deb_from_sources")
    def test_build_packages(self, m_build):
        self.driver.build_packages(
            "trusty",
            "/fake/sources",
            "/fake/resultdir",
            []
        )
        m_build.assert_called_with("trusty", "/fake/sources", [], None)
