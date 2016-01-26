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

from jsonschema import validate
from jsonschema import ValidationError

from packetary.schemas import DEB_REPO_SCHEMA
from packetary.schemas import PACKAGE_FILES_SCHEMA
from packetary.schemas import PACKAGES_SCHEMA
from packetary.schemas import RPM_REPO_SCHEMA
from packetary.tests import base


class TestRepositorySchemaBase(base.TestCase):
    def check_invalid_name(self):
        invalid_data = {"name": 123}
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            invalid_data['name'], self.schema['properties']['name']
        )

    def check_invalid_uri(self):
        invalid_data = {"uri": 123}
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            invalid_data['uri'], self.schema['properties']['uri']
        )

    def check_invalid_path(self):
        invalid_data = {"path": 123}
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            invalid_data['path'], self.schema['properties']['path']
        )

    def check_required_properties(self):
        repo_data1 = {"name": "os"}
        repo_data2 = {"uri": "file:///repo"}
        self.assertRaisesRegexp(
            ValidationError, "'uri' is a required property", validate,
            repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValidationError, "'name' is a required property", validate,
            repo_data2, self.schema
        )

    def check_priority(self, min_value=None, max_value=None):
        if min_value is not None:
            self.assertRaisesRegexp(
                ValidationError, "is not valid under any of the given schemas",
                validate, min_value - 1, self.schema['properties']['priority']
            )
            self.assertNotRaises(
                ValidationError, validate, min_value,
                self.schema['properties']['priority']
            )
        if max_value is not None:
            self.assertRaisesRegexp(
                ValidationError, "is not valid under any of the given schemas",
                validate, max_value + 1, self.schema['properties']['priority']
            )
            self.assertNotRaises(
                ValidationError, validate, max_value,
                self.schema['properties']['priority']
            )
        self.assertNotRaises(
            ValidationError, validate, None,
            self.schema['properties']['priority']
        )
        self.assertRaisesRegexp(
            ValidationError, "'abc' is not valid under any of the given",
            validate, "abc", self.schema['properties']['priority']
        )


class TestDebRepoSchema(TestRepositorySchemaBase):
    def setUp(self):
        self.schema = DEB_REPO_SCHEMA

    def test_valid_repo_data(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": ["main", "multiverse"], "path": "/some/path",
            "priority": 1001
        }
        self.assertNotRaises(
            ValidationError, validate, repo_data, self.schema
        )

    def test_priority(self):
        self.check_priority(0)

    def test_validation_fail_for_required_properties(self):
        self.check_required_properties()

        repo_data = {"name": "os", "uri": "file:///repo"}
        self.assertRaisesRegexp(
            ValidationError, "'suite' is a required property", validate,
            repo_data, self.schema
        )

    def test_validation_fail_if_name_is_invalid(self):
        self.check_invalid_name()

    def test_validation_fail_if_uri_is_invalid(self):
        self.check_invalid_uri()

    def test_validation_fail_if_path_is_invalid(self):
        self.check_invalid_path()

    def test_validation_fail_if_suite_is_invalid(self):
        repo_data = {"name": "os", "uri": "file:///repo", "suite": 123}
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            repo_data, self.schema
        )

    def test_validation_fail_if_section_is_invalid(self):
        repo_data1 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": 123
        }
        repo_data2 = {
            "name": "os", "uri": "file:///repo", "suite": "trusty",
            "section": [123]
        }
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'array'", validate,
            repo_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            repo_data2, self.schema
        )


class TestRpmRepoSchema(TestRepositorySchemaBase):
    def setUp(self):
        self.schema = RPM_REPO_SCHEMA

    def test_valid_repo_data(self):
        repo_data = {
            "name": "os", "uri": "file:///repo", "path": "/some/path",
            "priority": 45
        }
        self.assertNotRaises(
            ValidationError, validate, repo_data, self.schema
        )

    def test_priority(self):
        self.check_priority(1, 99)

    def test_validation_fail_for_required_properties(self):
        self.check_required_properties()

    def test_validation_fail_if_name_is_invalid(self):
        self.check_invalid_name()

    def test_validation_fail_if_uri_is_invalid(self):
        self.check_invalid_uri()

    def test_validation_fail_if_path_is_invalid(self):
        self.check_invalid_path()


class TestPackagesSchema(base.TestCase):
    def setUp(self):
        self.schema = PACKAGES_SCHEMA

    def test_valid_requirements_data(self):
        requirements_data = [
            {"name": "test1", "versions": [">= 1.1.2", "<= 3"]},
            {"name": "test2", "versions": ["< 3", "> 1", ">= 4"]},
            {"name": "test3", "versions": ["= 3"]},
            {"name": "test4", "versions": ["=     3"]}
        ]
        self.assertNotRaises(
            ValidationError, validate, requirements_data, self.schema
        )

    def test_validation_fail_for_required_properties(self):
        requirements_data1 = [
            {"name": "test1"},
        ]
        requirements_data2 = [
            {"versions": ["< 3", "> 1"]},
        ]
        self.assertRaisesRegexp(
            ValidationError, "'versions' is a required property", validate,
            requirements_data1, self.schema
        )
        self.assertRaisesRegexp(
            ValidationError, "'name' is a required property", validate,
            requirements_data2, self.schema
        )

    def test_validation_fail_if_name_is_invalid(self):
        requirements_data = [
            {"name": 123, "versions": [">= 1.1.2", "<= 3"]},
        ]
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            requirements_data, self.schema
        )

    def test_validation_fail_if_versions_is_invalid(self):
        versions = [
            123,        # not array
            [123],      # not string
            ["1.1.2"],  # relational operator
            [">=3"],    # not whitespace after ro
            ["== 3"]    # ==
        ]
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'array'", validate,
            versions[0], self.schema['items']['properties']['versions']
        )
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            versions[1], self.schema['items']['properties']['versions']
        )
        for version in versions[2:]:
            self.assertRaisesRegexp(
                ValidationError, "does not match", validate,
                version, self.schema['items']['properties']['versions']
            )


class TestPackageFilesSchema(base.TestCase):
    def setUp(self):
        self.schema = PACKAGE_FILES_SCHEMA

    def test_valid_file_urls(self):
        file_urls = [
            "file://test1.pkg",
            "file:///test2.pkg",
            "/test3.pkg",
            "http://test4.pkg",
            "https://test5.pkg"
        ]
        self.assertNotRaises(
            ValidationError, validate, file_urls, self.schema
        )

    def test_validation_fail_if_invalid_file_urls(self):
        file_urls = [
            "/test1.pkg",         # not array
            [123],                # not string
            ["test1.pkg"],        # does not match pattern
            ["./test2.pkg"],      # does not match pattern
            ["file//test3.pkg"],  # does not match pattern
            ["http//test4.pkg"]   # does not match pattern
        ]

        self.assertRaisesRegexp(
            ValidationError, "'/test1.pkg' is not of type 'array'", validate,
            file_urls[0], self.schema
        )
        self.assertRaisesRegexp(
            ValidationError, "123 is not of type 'string'", validate,
            file_urls[1], self.schema
        )
        for url in file_urls[2:]:
            self.assertRaisesRegexp(
                ValidationError, "does not match", validate,
                url, self.schema
            )
