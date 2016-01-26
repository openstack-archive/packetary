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

from packetary.api import RepositoryApi
from packetary.schemas import DEB_REPO_SCHEMA
from packetary.schemas import PACKAGES_SCHEMA
from packetary.schemas import RPM_REPO_SCHEMA
from packetary.tests import base
from packetary.tests.stubs.helpers import CallbacksAdapter


class TestDebRepoSchema(base.TestCase):
    def setUp(self):
        self.controller = CallbacksAdapter()
        self.api = RepositoryApi(self.controller)
        self.validate = self.api.validate_data
        self.schema = DEB_REPO_SCHEMA

    def test_valid_data(self):
        repo_data = {"name": "os", "uri": "file:///repo", "suite": "trusty"}
        self.assertNotRaises(
            ValueError, self.validate, repo_data, self.schema
        )

    def test_required(self):
        repo_data1 = {"name": "os"}
        repo_data2 = {"uri": "file:///repo"}
        repo_data3 = {"name": "os", "uri": "file:///repo"}
        self.assertRaisesRegexp(
            ValueError, "'uri' is a required property", self.validate,
            repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'name' is a required property", self.validate,
            repo_data2, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'suite' is a required property", self.validate,
            repo_data3, self.schema
        )

    def test_name_type(self):
        repo_data = {"name": 123, "uri": "file:///repo", "suite": "trusty"}
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_uri_type(self):
        repo_data = {"name": "os", "uri": 123, "suite": "trusty"}
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_suite_type(self):
        repo_data = {"name": "os", "uri": "file:///repo", "suite": 123}
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_path_type(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "path": 123
        }
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_section_type(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": 123
        }
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'array'", self.validate,
            repo_data, self.schema)

    def test_section_item_type(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": [123]
        }
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_section_not_raise(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": ["main", "multiverse"]
        }
        self.assertNotRaises(
            ValueError, self.validate, repo_data, self.schema
        )

    def test_priority_not_raise(self):
        repo_data1 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "priority": None
        }
        repo_data2 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "priority": 0
        }
        repo_data3 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "priority": 1001
        }
        self.assertNotRaises(
            ValueError, self.validate, repo_data1, self.schema
        )
        self.assertNotRaises(
            ValueError, self.validate, repo_data2, self.schema
        )
        self.assertNotRaises(
            ValueError, self.validate, repo_data3, self.schema
        )

    def test_priority_raise(self):
        repo_data1 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "priority": -1
        }
        repo_data2 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "priority": "abc"
        }
        self.assertRaisesRegexp(
            ValueError, "-1 is not valid under any of the given schemas",
            self.validate, repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'abc' is not valid under any of the given schemas",
            self.validate, repo_data2, self.schema
        )


class TestRpmRepoSchema(base.TestCase):
    def setUp(self):
        self.controller = CallbacksAdapter()
        self.api = RepositoryApi(self.controller)
        self.validate = self.api.validate_data
        self.schema = RPM_REPO_SCHEMA

    def test_valid_data(self):
        repo_data = {"name": "os", "uri": "file:///repo"}
        self.assertNotRaises(
            ValueError, self.validate, repo_data, self.schema
        )

    def test_required(self):
        repo_data1 = {"name": "os"}
        repo_data2 = {"uri": "file:///repo"}
        self.assertRaisesRegexp(
            ValueError, "'uri' is a required property", self.validate,
            repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'name' is a required property", self.validate,
            repo_data2, self.schema
        )

    def test_name_type(self):
        repo_data = {"name": 123, "uri": "file:///repo"}
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_uri_type(self):
        repo_data = {"name": "os", "uri": 123}
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_path_type(self):
        repo_data = {
            "name": "os", "uri": "file:///repo",
            "path": 123
        }
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            repo_data, self.schema)

    def test_priority_not_raise(self):
        repo_data1 = {
            "name": "os", "uri": "file:///repo",
            "priority": None
        }
        repo_data2 = {
            "name": "os", "uri": "file:///repo",
            "priority": 1
        }
        repo_data3 = {
            "name": "os", "uri": "file:///repo",
            "priority": 99
        }
        self.assertNotRaises(
            ValueError, self.validate, repo_data1, self.schema
        )
        self.assertNotRaises(
            ValueError, self.validate, repo_data2, self.schema
        )
        self.assertNotRaises(
            ValueError, self.validate, repo_data3, self.schema
        )

    def test_priority_raise(self):
        repo_data1 = {
            "name": "os", "uri": "file:///repo",
            "priority": 0
        }
        repo_data2 = {
            "name": "os", "uri": "file:///repo",
            "priority": 100
        }
        repo_data3 = {
            "name": "os", "uri": "file:///repo",
            "priority": "abc"
        }
        self.assertRaisesRegexp(
            ValueError, "0 is not valid under any of the given schemas",
            self.validate, repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "100 is not valid under any of the given schemas",
            self.validate, repo_data2, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'abc' is not valid under any of the given schemas",
            self.validate, repo_data3, self.schema
        )


class TestPackagesSchema(base.TestCase):
    def setUp(self):
        self.controller = CallbacksAdapter()
        self.api = RepositoryApi(self.controller)
        self.validate = self.api.validate_data
        self.schema = PACKAGES_SCHEMA

    def test_valid_data(self):
        requirements_data = [
            {"name": "test1", "versions": [">= 1.1.2", "<= 3"]},
            {"name": "test2", "versions": ["< 3", "> 1", ">= 4"]}
        ]
        self.assertNotRaises(
            ValueError, self.validate, requirements_data, self.schema
        )

    def test_required(self):
        requirements_data1 = [
            {"name": "test1"},
        ]
        requirements_data2 = [
            {"versions": ["< 3", "> 1"]},
        ]
        self.assertRaisesRegexp(
            ValueError, "'versions' is a required property", self.validate,
            requirements_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'name' is a required property", self.validate,
            requirements_data2, self.schema
        )

    def test_name_type(self):
        requirements_data = [
            {"name": 123, "versions": [">= 1.1.2", "<= 3"]},
        ]
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            requirements_data, self.schema
        )

    def test_versions_type(self):
        requirements_data = [
            {"name": "test1", "versions": 123},
        ]
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'array'", self.validate,
            requirements_data, self.schema
        )

    def test_versions_item_type(self):
        requirements_data = [
            {"name": "test1", "versions": [123]},
        ]
        self.assertRaisesRegexp(
            ValueError, "123 is not of type 'string'", self.validate,
            requirements_data, self.schema
        )

    def test_versions_item_pattern_raise(self):
        requirements_data1 = [
            {"name": "test1", "versions": [">=  1.1.2"]}  # extra whitespace
        ]
        requirements_data2 = [
            {"name": "test1", "versions": ["1.1.2"]}  # relational operator
        ]
        requirements_data3 = [
            {"name": "test1", "versions": [">=3"]}  # not whitespace after ro
        ]
        self.assertRaisesRegexp(
            ValueError, "'>=  1.1.2' does not match", self.validate,
            requirements_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'1.1.2' does not match", self.validate,
            requirements_data2, self.schema
        )
        self.assertRaisesRegexp(
            ValueError, "'>=3' does not match", self.validate,
            requirements_data3, self.schema
        )
