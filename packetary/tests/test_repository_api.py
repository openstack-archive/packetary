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

import jsonschema

from packetary.api import Configuration
from packetary.api import Context
from packetary.api import RepositoryApi
from packetary.schemas import PACKAGE_FILES_SCHEMA
from packetary.schemas import PACKAGES_SCHEMA
from packetary.tests import base
from packetary.tests.stubs import generator
from packetary.tests.stubs.helpers import CallbacksAdapter


@mock.patch("packetary.api.jsonschema")
class TestRepositoryApi(base.TestCase):
    def setUp(self):
        self.controller = CallbacksAdapter()
        self.api = RepositoryApi(self.controller)
        self.repo_data = {"name": "repo1", "uri": "file:///repo1"}
        self.requirements_data = [
            {"name": "test1"}, {"name": "test2", "versions": ["< 3", "> 1"]}
        ]
        self.schema = {}
        self.repo = generator.gen_repository(**self.repo_data)
        self.controller.load_repositories.return_value = [self.repo]
        self.controller.get_repository_data_schema.return_value = self.schema
        self._generate_packages()

    def _generate_packages(self):
        self.packages = [
            generator.gen_package(idx=1, repository=self.repo, requires=None),
            generator.gen_package(idx=2, repository=self.repo, requires=None),
            generator.gen_package(
                idx=3, repository=self.repo, mandatory=True,
                requires=[generator.gen_relation("package2")]
            ),
            generator.gen_package(
                idx=4, repository=self.repo, mandatory=False,
                requires=[generator.gen_relation("package1")]
            ),
            generator.gen_package(
                idx=5, repository=self.repo,
                requires=[generator.gen_relation("package6")])
        ]
        self.controller.load_packages.return_value = self.packages

    @mock.patch("packetary.api.RepositoryController")
    @mock.patch("packetary.api.ConnectionsManager")
    def test_create_with_config(self, connection_mock, controller_mock,
                                jsonschema_mock):
        config = Configuration(
            http_proxy="http://localhost", https_proxy="https://localhost",
            retries_num=10, retry_interval=1, threads_num=8,
            ignore_errors_num=6
        )
        RepositoryApi.create(config, "deb", "x86_64")
        connection_mock.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=10,
            retry_interval=1
        )
        controller_mock.load.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )

    @mock.patch("packetary.api.RepositoryController")
    @mock.patch("packetary.api.ConnectionsManager")
    def test_create_with_context(self, connection_mock, controller_mock,
                                 jsonschema_mock):
        config = Configuration(
            http_proxy="http://localhost", https_proxy="https://localhost",
            retries_num=10, retry_interval=1, threads_num=8,
            ignore_errors_num=6
        )
        context = Context(config)
        RepositoryApi.create(context, "deb", "x86_64")
        connection_mock.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=10,
            retry_interval=1
        )
        controller_mock.load.assert_called_once_with(
            context, "deb", "x86_64"
        )

    def test_create_repository(self, jsonschema_mock):
        file_urls = ["file://test1.pkg"]
        self.api.create_repository(self.repo_data, file_urls)
        self.controller.create_repository.assert_called_once_with(
            self.repo_data, file_urls
        )
        jsonschema_mock.validate.assert_has_calls(
            [
                mock.call(self.repo_data, self.schema),
                mock.call(file_urls, PACKAGE_FILES_SCHEMA),
            ]
        )

    def test_get_packages_as_is(self, jsonschema_mock):
        packages = self.api.get_packages([self.repo_data], None)
        self.assertEqual(5, len(packages))
        self.assertItemsEqual(
            self.packages,
            packages
        )
        jsonschema_mock.validate.assert_called_once_with(
            self.repo_data, self.schema
        )

    def test_get_packages_by_requirements_with_mandatory(self,
                                                         jsonschema_mock):
        requirements = [{"name": "package1"}]
        packages = self.api.get_packages(
            [self.repo_data], requirements, True
        )
        self.assertEqual(3, len(packages))
        self.assertItemsEqual(
            ["package1", "package2", "package3"],
            (x.name for x in packages)
        )
        jsonschema_mock.validate.assert_has_calls(
            [
                mock.call(self.repo_data, self.schema),
                mock.call(requirements, PACKAGES_SCHEMA),
            ]
        )

    def test_get_packages_by_requirements_without_mandatory(self,
                                                            jsonschema_mock):
        requirements = [{"name": "package4"}]
        packages = self.api.get_packages(
            [self.repo_data], requirements, False
        )
        self.assertEqual(2, len(packages))
        self.assertItemsEqual(
            ["package1", "package4"],
            (x.name for x in packages)
        )
        jsonschema_mock.validate.assert_has_calls(
            [
                mock.call(self.repo_data, self.schema),
                mock.call(requirements, PACKAGES_SCHEMA),
            ]
        )

    def test_clone_repositories_as_is(self, jsonschema_mock):
        # return value is used as statistics
        mirror = copy.copy(self.repo)
        mirror.url = "file:///mirror/repo"
        self.controller.fork_repository.return_value = mirror
        self.controller.assign_packages.return_value = [0, 1, 1, 1, 0, 6]
        stats = self.api.clone_repositories([self.repo_data], None, "/mirror")
        self.controller.fork_repository.assert_called_once_with(
            self.repo, '/mirror', False, False
        )
        self.controller.assign_packages.assert_called_once_with(
            mirror, set(self.packages)
        )
        self.assertEqual(6, stats.total)
        self.assertEqual(4, stats.copied)
        jsonschema_mock.validate.assert_called_once_with(
            self.repo_data, self.schema
        )

    def test_clone_by_requirements_with_mandatory(self, jsonschema_mock):
        # return value is used as statistics
        mirror = copy.copy(self.repo)
        mirror.url = "file:///mirror/repo"
        requirements = [{"name": "package1"}]
        self.controller.fork_repository.return_value = mirror
        self.controller.assign_packages.return_value = [0, 1, 1]
        stats = self.api.clone_repositories(
            [self.repo_data], requirements,
            "/mirror", include_mandatory=True
        )
        packages = {self.packages[0], self.packages[1], self.packages[2]}
        self.controller.fork_repository.assert_called_once_with(
            self.repo, '/mirror', False, False
        )
        self.controller.assign_packages.assert_called_once_with(
            mirror, packages
        )
        self.assertEqual(3, stats.total)
        self.assertEqual(2, stats.copied)
        jsonschema_mock.validate.assert_has_calls(
            [
                mock.call(self.repo_data, self.schema),
                mock.call(requirements, PACKAGES_SCHEMA),
            ]
        )

    def test_clone_by_requirements_without_mandatory(self,
                                                     jsonschema_mock):
        # return value is used as statistics
        mirror = copy.copy(self.repo)
        mirror.url = "file:///mirror/repo"
        requirements = [{"name": "package4"}]
        self.controller.fork_repository.return_value = mirror
        self.controller.assign_packages.return_value = [0, 4]
        stats = self.api.clone_repositories(
            [self.repo_data], requirements,
            "/mirror", include_mandatory=False
        )
        packages = {self.packages[0], self.packages[3]}
        self.controller.fork_repository.assert_called_once_with(
            self.repo, '/mirror', False, False
        )
        self.controller.assign_packages.assert_called_once_with(
            mirror, packages
        )
        self.assertEqual(2, stats.total)
        self.assertEqual(1, stats.copied)
        jsonschema_mock.validate.assert_has_calls(
            [
                mock.call(self.repo_data, self.schema),
                mock.call(requirements, PACKAGES_SCHEMA),
            ]
        )

    def test_get_unresolved(self, jsonschema_mock):
        unresolved = self.api.get_unresolved_dependencies([self.repo_data])
        self.assertItemsEqual(["package6"], (x.name for x in unresolved))
        jsonschema_mock.validate.assert_called_once_with(
            self.repo_data, self.schema
        )

    def test_load_requirements(self, jsonschema_mock):
        expected = {
            generator.gen_relation("test1"),
            generator.gen_relation("test2", ["<", "3"]),
            generator.gen_relation("test2", [">", "1"]),
        }
        actual = set(self.api._load_requirements(
            self.requirements_data
        ))
        self.assertEqual(expected, actual)
        self.assertIsNone(self.api._load_requirements(None))
        jsonschema_mock.validate.assert_called_once_with(
            self.requirements_data,
            PACKAGES_SCHEMA
        )

    def test_validate_data(self, jsonschema_mock):
        self.api._validate_data(self.repo_data, self.schema)
        jsonschema_mock.validate.assert_called_once_with(
            self.repo_data, self.schema
        )

    def test_validate_invalid_data(self, jschema_m):
        jschema_m.ValidationError = jsonschema.ValidationError
        jschema_m.SchemaError = jsonschema.SchemaError
        paths = [(("a", 0), "\['a'\]\[0\]"), ((), "")]
        for path, details in paths:
            msg = "Invalid data: error."
            if details:
                msg += "\nField: {0}".format(details)
            with self.assertRaisesRegexp(ValueError, msg):
                jschema_m.validate.side_effect = jsonschema.ValidationError(
                    "error", path=path
                )
                self.api._validate_data([], {})
            jschema_m.validate.assert_called_with([], {})
            jschema_m.validate.reset_mock()

            msg = "Invalid schema: error."
            if details:
                msg += "\nField: {0}".format(details)
            with self.assertRaisesRegexp(ValueError, msg):
                jschema_m.validate.side_effect = jsonschema.SchemaError(
                    "error", schema_path=path
                )
                self.api._validate_data([], {})
            jschema_m.validate.assert_called_with([], {})


class TestContext(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuration(
            threads_num=2,
            ignore_errors_num=3,
            retries_num=5,
            retry_interval=10,
            http_proxy="http://localhost",
            https_proxy="https://localhost"
        )

    @mock.patch("packetary.api.ConnectionsManager")
    def test_initialise_connection_manager(self, conn_manager):
        context = Context(self.config)
        conn_manager.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=5,
            retry_interval=10
        )

        self.assertIs(
            conn_manager(),
            context.connection
        )

    @mock.patch("packetary.api.AsynchronousSection")
    def test_asynchronous_section(self, async_section):
        context = Context(self.config)
        s = context.async_section()
        async_section.assert_called_with(2, 3)
        self.assertIs(s, async_section())
        context.async_section(0)
        async_section.assert_called_with(2, 0)
