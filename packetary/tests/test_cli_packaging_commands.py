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

from packetary.api import PackagingApi
from packetary.cli.commands import build

from packetary.tests import base


@mock.patch("packetary.cli.commands.base.BaseCommand.stdout")
@mock.patch("packetary.cli.commands.base.api.PackagingApi")
class TestCliPackagingCommands(base.TestCase):
    common_argv = [
        "--ignore-errors-num=3",
        "--threads-num=8",
        "--retries-num=10",
        "--retry-interval=1",
        "--http-proxy=http://proxy",
        "--https-proxy=https://proxy"
    ]

    build_argv = [
        "-C", "driver.conf",
        "-i", "packages.yaml",
        "-o", "/tmp",
        "-t", "test",
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def get_api_instance_mock(self, api_mock):
        api_instance = mock.MagicMock(spec=PackagingApi)
        api_mock.create.return_value = api_instance
        return api_instance

    @mock.patch("packetary.cli.commands.build.read_from_file")
    def test_build_cmd(self, read_file_mock, api_mock, stdout_mock):
        read_file_mock.side_effect = [[{"source": "/sources"}]]
        api_instance = self.get_api_instance_mock(api_mock)
        api_instance.build_packages.return_value = ['package1']
        self.start_cmd(build, self.build_argv)
        api_mock.create.assert_called_once_with(
            mock.ANY, "test", "driver.conf"
        )
        read_file_mock.assert_called_once_with("packages.yaml")
        api_instance.build_packages.assert_called_once_with(
            [{"source": "/sources"}], "/tmp"
        )
        stdout_mock.write.assert_has_calls([
            mock.call("Packages built:\n"),
            mock.call("package1"),
            mock.call("\n")
        ])
