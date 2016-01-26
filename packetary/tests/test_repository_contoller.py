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

import copy
import mock

from packetary.controllers import RepositoryController
from packetary.drivers.base import RepositoryDriverBase
from packetary.tests import base
from packetary.tests.stubs.executor import Executor
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import CallbacksAdapter


class TestRepositoryController(base.TestCase):
    def setUp(self):
        self.driver = mock.MagicMock(spec=RepositoryDriverBase)
        self.context = mock.MagicMock()
        self.context.async_section.return_value = Executor()
        self.ctrl = RepositoryController(self.context, self.driver, "x86_64")

    def test_load_fail_if_unknown_driver(self):
        with self.assertRaisesRegexp(NotImplementedError, "unknown_driver"):
            RepositoryController.load(
                self.context,
                "unknown_driver",
                "x86_64"
            )

    @mock.patch("packetary.controllers.repository.stevedore")
    def test_load_driver(self, stevedore):
        stevedore.ExtensionManager.return_value = {
            "test": mock.MagicMock(obj=self.driver)
        }
        RepositoryController._drivers = None
        controller = RepositoryController.load(self.context, "test", "x86_64")
        self.assertIs(self.driver, controller.driver)

    def test_load_repositories(self):
        repo_data = {"name": "test", "uri": "file:///test1"}
        repo = gen_repository(**repo_data)
        self.driver.get_repository = CallbacksAdapter()
        self.driver.get_repository.side_effect = [repo]

        repos = self.ctrl.load_repositories([repo_data])
        self.driver.get_repository.assert_called_once_with(
            self.context.connection, repo_data, self.ctrl.arch
        )
        self.assertEqual([repo], repos)

    def test_load_packages(self):
        repo = mock.MagicMock()
        consumer = mock.MagicMock()
        self.ctrl.load_packages(repo, consumer)
        self.driver.get_packages.assert_called_once_with(
            self.context.connection, repo, consumer
        )

    @mock.patch("packetary.controllers.repository.os")
    def test_assign_packages(self, os):
        repo = gen_repository(url="/test/repo")
        packages = {
            gen_package(name="test1", repository=repo),
            gen_package(name="test2", repository=repo)
        }
        os.path.join = lambda *x: "/".join(x)
        self.ctrl.assign_packages(repo, packages)
        self.driver.add_packages.assert_called_once_with(
            self.ctrl.context.connection, repo, packages
        )

    @mock.patch("packetary.controllers.repository.os")
    def test_fork_repository(self, os):
        os.path.join.side_effect = lambda *args: "".join(args)
        repo = gen_repository(name="test1", url="file:///test")
        clone = copy.copy(repo)
        clone.url = "/root/repo"
        self.driver.fork_repository.return_value = clone
        self.context.connection.retrieve.side_effect = [0, 10]
        self.ctrl.fork_repository(repo, "./repo", False, False)
        self.driver.fork_repository.assert_called_once_with(
            self.context.connection, repo, "./repo/test", False, False
        )
        repo.path = "os"
        self.ctrl.fork_repository(repo, "./repo/", False, False)
        self.driver.fork_repository.assert_called_with(
            self.context.connection, repo, "./repo/os", False, False
        )

    def test_copy_packages(self):
        repo = gen_repository(url="file:///repo/")
        packages = [
            gen_package(name="test1", repository=repo, filesize=10),
            gen_package(name="test2", repository=repo, filesize=-1)
        ]
        target = gen_repository(url="/test/repo")
        self.context.connection.retrieve.side_effect = [0, 10]
        observer = mock.MagicMock()
        self.ctrl._copy_packages(target, packages, observer)
        observer.assert_any_call(0)
        observer.assert_any_call(10)
        self.context.connection.retrieve.assert_any_call(
            "file:///repo/test1.pkg",
            "/test/repo/test1.pkg",
            size=10
        )
        self.context.connection.retrieve.assert_any_call(
            "file:///repo/test2.pkg",
            "/test/repo/test2.pkg",
            size=-1
        )

    def test_copy_packages_does_not_affect_packages_in_same_repo(self):
        repo = gen_repository(url="file:///repo/")
        packages = [
            gen_package(name="test1", repository=repo, filesize=10),
            gen_package(name="test2", repository=repo, filesize=-1)
        ]
        observer = mock.MagicMock()
        self.ctrl._copy_packages(repo, packages, observer)
        self.assertFalse(self.context.connection.retrieve.called)

    @mock.patch("packetary.controllers.repository.jsonschema")
    def test_validate_data(self, jsonschema):
        repo_data = {"name": "test", "uri": "file:///test1"}
        schema = {}
        self.ctrl.validate_data(repo_data, schema)
        jsonschema.validate.assert_called_with(
            repo_data, schema
        )
