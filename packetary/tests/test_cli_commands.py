# -*- coding: utf-8 -*-

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
import subprocess

# The cmd2 does not work with python3.5
# because it tries to get access to the property mswindows,
# that was removed in 3.5
subprocess.mswindows = False

from packetary.api import RepositoryApi
from packetary.cli.commands import clone
from packetary.cli.commands import create
from packetary.cli.commands import packages
from packetary.cli.commands import unresolved
from packetary.objects.statistics import CopyStatistics
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_relation
from packetary.tests.stubs.generator import gen_repository


@mock.patch("packetary.cli.commands.base.BaseRepoCommand.stdout")
@mock.patch("packetary.cli.commands.base.read_from_file")
@mock.patch("packetary.cli.commands.base.RepositoryApi")
class TestCliCommands(base.TestCase):
    common_argv = [
        "--ignore-errors-num=3",
        "--threads-num=8",
        "--retries-num=10",
        "--retry-interval=1",
        "--http-proxy=http://proxy",
        "--https-proxy=https://proxy"
    ]

    clone_argv = [
        "-r", "repositories.yaml",
        "-p", "packages.yaml",
        "-d", "/root",
        "-t", "deb",
        "-a", "x86_64",
        "--skip-mandatory"
    ]

    create_argv = [
        "--repository", "repository.yaml",
        "--package-files", "package-files.yaml",
    ]

    packages_argv = [
        "-r", "repositories.yaml",
        "-t", "deb",
        "-a", "x86_64",
        "-c", "name", "filename"
    ]

    unresolved_argv = [
        "-r", "repositories.yaml",
        "-t", "deb",
        "-a", "x86_64"
    ]

    def start_cmd(self, cmd, argv):
        cmd.debug(argv + self.common_argv)

    def get_api_instance_mock(self, api_mock):
        api_instance = mock.MagicMock(spec=RepositoryApi)
        api_mock.create.return_value = api_instance
        return api_instance

    def check_common_config(self, config):
        self.assertEqual("http://proxy", config.http_proxy)
        self.assertEqual("https://proxy", config.https_proxy)
        self.assertEqual(3, config.ignore_errors_num)
        self.assertEqual(8, config.threads_num)
        self.assertEqual(10, config.retries_num)
        self.assertEqual(1, config.retry_interval)

    def test_clone_cmd(self, api_mock, read_file_mock, stdout_mock):
        read_file_mock.side_effect = [
            [{"name": "repo"}],
            [{"name": "package"}],
        ]
        api_instance = self.get_api_instance_mock(api_mock)
        api_instance.clone_repositories.return_value = CopyStatistics()
        self.start_cmd(clone, self.clone_argv)
        api_mock.create.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_common_config(api_mock.create.call_args[0][0])
        read_file_mock.assert_any_call("repositories.yaml")
        read_file_mock.assert_any_call("packages.yaml")
        api_instance.clone_repositories.assert_called_once_with(
            [{"name": "repo"}], [{"name": "package"}], "/root",
            False, False, False
        )
        stdout_mock.write.assert_called_once_with(
            "Packages copied: 0/0.\n"
        )

    def test_get_packages_cmd(self, api_mock, read_file_mock, stdout_mock):
        read_file_mock.return_value = [{"name": "repo"}]
        api_instance = self.get_api_instance_mock(api_mock)
        api_instance.get_packages.return_value = [
            gen_package(name="test1", filesize=1, requires=None,
                        obsoletes=None, provides=None)
        ]

        self.start_cmd(packages, self.packages_argv)
        read_file_mock.assert_called_with("repositories.yaml")
        api_mock.create.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_common_config(api_mock.create.call_args[0][0])
        api_instance.get_packages.assert_called_once_with(
            [{"name": "repo"}], None, True
        )
        self.assertIn(
            "test1; test1.pkg",
            stdout_mock.write.call_args_list[3][0][0]
        )

    def test_get_unresolved_cmd(self, api_mock, read_file_mock, stdout_mock):
        read_file_mock.return_value = [{"name": "repo"}]
        api_instance = self.get_api_instance_mock(api_mock)
        api_instance.get_unresolved_dependencies.return_value = [
            gen_relation(name="test")
        ]

        self.start_cmd(unresolved, self.unresolved_argv)
        api_mock.create.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_common_config(api_mock.create.call_args[0][0])
        api_instance.get_unresolved_dependencies.assert_called_once_with(
            [{"name": "repo"}]
        )
        self.assertIn(
            "test; any; -",
            stdout_mock.write.call_args_list[3][0][0]
        )

    @mock.patch("packetary.cli.commands.create.read_from_file")
    def test_create_cmd(self, read_file_in_create_mock, api_mock,
                        read_file_mock, stdout_mock):
        read_file_in_create_mock.side_effect = [
            [{"name": "repo"}],
            ["/test1.deb", "/test2.deb", "/test3.deb"],
        ]
        api_instance = self.get_api_instance_mock(api_mock)
        api_instance.create_repository.return_value = gen_repository()
        self.start_cmd(create, self.create_argv)
        api_mock.create.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )
        self.check_common_config(api_mock.create.call_args[0][0])
        read_file_in_create_mock.assert_any_call("repository.yaml")
        read_file_in_create_mock.assert_any_call("package-files.yaml")
        api_instance.create_repository.assert_called_once_with(
            [{'name': 'repo'}],
            ['/test1.deb', '/test2.deb', '/test3.deb']
        )
        stdout_mock.write.assert_called_once_with(
            "Successfully completed."
        )
