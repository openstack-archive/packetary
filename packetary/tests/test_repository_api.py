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

from packetary import api
from packetary import controllers
from packetary import schemas

from packetary.tests import base
from packetary.tests.stubs import generator
from packetary.tests.stubs import helpers


@mock.patch("packetary.api.validators.jsonschema")
class TestRepositoryApi(base.TestCase):
    def setUp(self):
        super(TestRepositoryApi, self).setUp()
        self.controller = helpers.CallbacksAdapter(
            spec=controllers.RepositoryController
        )
        self.api = api.RepositoryApi(self.controller)
        self.schema = {}
        self.controller.get_repository_data_schema.return_value = self.schema

    def _generate_repositories(self, count=1):
        self.repos_data = [
            {"name": "repo{0}".format(i), "uri": "file:///repo{0}".format(i)}
            for i in range(count)
        ]
        self.repos = [
            generator.gen_repository(**data) for data in self.repos_data
        ]
        self.controller.load_repositories.return_value = self.repos

    def _generate_mirrors(self):
        mirrors = {}
        for repo in self.repos:
            mirror = copy.copy(repo)
            mirror.url = "file:///mirror/{0}".format(repo.name)
            mirrors[repo] = mirror
        self.controller.fork_repository.side_effect = lambda *x: mirrors[x[0]]
        self.mirrors = mirrors

    def _generate_packages(self):
        self.packages = [
            [
                generator.gen_package(
                    name='{0}_1'.format(r.name), repository=r, requires=None
                ),
                generator.gen_package(
                    name='{0}_2'.format(r.name), repository=r, requires=None
                ),
                generator.gen_package(
                    name='{0}_3'.format(r.name), repository=r, mandatory=True,
                    requires=[generator.gen_relation("{0}_2".format(r.name))]
                ),
                generator.gen_package(
                    name='{0}_4'.format(r.name), repository=r, mandatory=False,
                    requires=[generator.gen_relation("{0}_1".format(r.name))]
                ),
                generator.gen_package(
                    name='{0}_5'.format(r.name), repository=r,
                    requires=[generator.gen_relation("unresolved")]
                ),
            ]
            for r in self.repos
        ]
        self.controller.load_packages.side_effect = self.packages

    @mock.patch("packetary.api.context.ConnectionsManager")
    @mock.patch("packetary.api.repositories.RepositoryController")
    def test_create_with_config(self, controller_mock, connection_mock, _):
        config = api.Configuration(
            http_proxy="http://localhost", https_proxy="https://localhost",
            retries_num=10, retry_interval=1, threads_num=8,
            ignore_errors_num=6
        )
        api.RepositoryApi.create(config, "deb", "x86_64")
        connection_mock.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=10,
            retry_interval=1
        )
        controller_mock.load.assert_called_once_with(
            mock.ANY, "deb", "x86_64"
        )

    @mock.patch("packetary.api.context.ConnectionsManager")
    @mock.patch("packetary.api.repositories.RepositoryController")
    def test_create_with_context(self, controller_mock, connection_mock, _):
        config = api.Configuration(
            http_proxy="http://localhost", https_proxy="https://localhost",
            retries_num=10, retry_interval=1, threads_num=8,
            ignore_errors_num=6, cache_dir='/tmp/cache'
        )
        context = api.Context(config)
        api.RepositoryApi.create(context, "deb", "x86_64")
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
        self._generate_repositories(1)
        self.api.create_repository(self.repos_data[0], file_urls)
        self.controller.create_repository.assert_called_once_with(
            self.repos_data[0], file_urls
        )
        jsonschema_mock.validate.assert_has_calls([
            mock.call(self.repos_data[0], self.schema),
            mock.call(file_urls, schemas.PACKAGE_FILES_SCHEMA),
        ], any_order=True)

    def test_get_packages_as_is(self, jsonschema_mock):
        self._generate_repositories(1)
        self._generate_packages()
        packages = self.api.get_packages(self.repos_data)
        self.assertEqual(5, len(self.packages[0]))
        self.assertItemsEqual(self.packages[0], packages)
        jsonschema_mock.validate.assert_called_once_with(
            self.repos_data, self.api._get_repositories_data_schema()
        )

    def test_get_packages_by_requirements(self, jsonschema_mock):
        self._generate_repositories(2)
        self._generate_packages()
        requirements = {
            'packages': [{"name": "repo0_1"}],
            'repositories': [{"name": "repo1"}],
            'mandatory': True
        }
        packages = self.api.get_packages(self.repos_data, requirements)
        expected_packages = self.packages[0][:3] + self.packages[1]
        self.assertItemsEqual(
            [x.name for x in expected_packages],
            [x.name for x in packages]
        )
        repos_schema = self.api._get_repositories_data_schema()
        jsonschema_mock.validate.assert_has_calls([
            mock.call(self.repos_data, repos_schema),
            mock.call(requirements, schemas.REQUIREMENTS_SCHEMA)
        ], any_order=True)

    def test_clone_repositories_as_is(self, jsonschema_mock):
        self._generate_repositories(1)
        self._generate_packages()
        self._generate_mirrors()

        self.controller.assign_packages.return_value = [0, 1, 1, 1, 0, 6]
        options = api.RepositoryCopyOptions()
        stats = self.api.clone_repositories(
            self.repos_data, "/mirror", options=options)
        self.controller.fork_repository.assert_called_once_with(
            self.repos[0], '/mirror', options
        )
        self.controller.assign_packages.assert_called_once_with(
            self.mirrors[self.repos[0]], set(self.packages[0]), mock.ANY
        )
        self.assertEqual(6, stats.total)
        self.assertEqual(4, stats.copied)
        jsonschema_mock.validate.assert_called_once_with(
            self.repos_data, self.api._get_repositories_data_schema()
        )

    def test_clone_by_requirements(self, jsonschema_mock):
        self._generate_repositories(2)
        self._generate_packages()
        self._generate_mirrors()
        requirements = {
            'packages': [{"name": "repo0_1"}],
            'repositories': [{"name": "repo1"}],
            'mandatory': False
        }
        self.controller.assign_packages.return_value = [0, 1, 1] * 3
        stats = self.api.clone_repositories(
            self.repos_data, "/mirror", requirements
        )
        self.controller.fork_repository.assert_has_calls(
            [mock.call(r, '/mirror', mock.ANY) for r in self.repos],
            any_order=True
        )
        self.controller.assign_packages.assert_has_calls([
            mock.call(
                self.mirrors[self.repos[0]],
                set(self.packages[0][:1]),
                mock.ANY
            ),
            mock.call(
                self.mirrors[self.repos[1]],
                set(self.packages[1]),
                mock.ANY
            )
        ], any_order=True)
        self.assertEqual(18, stats.total)
        self.assertEqual(12, stats.copied)
        repos_schema = self.api._get_repositories_data_schema()
        jsonschema_mock.validate.assert_has_calls([
            mock.call(self.repos_data, repos_schema),
            mock.call(requirements, schemas.REQUIREMENTS_SCHEMA)
        ], any_order=True)

    def test_get_unresolved(self, jsonschema_mock):
        self._generate_repositories(1)
        self._generate_packages()
        unresolved = self.api.get_unresolved_dependencies(self.repos_data)
        self.assertItemsEqual(["unresolved"], (x.name for x in unresolved))
        jsonschema_mock.validate.assert_called_once_with(
            self.repos_data, self.api._get_repositories_data_schema()
        )
