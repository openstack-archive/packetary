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
import os.path as path
import six

from packetary.drivers import deb_driver
from packetary.schemas import DEB_REPO_SCHEMA
from packetary.tests import base
from packetary.tests.stubs.generator import gen_package
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import get_compressed


PACKAGES = path.join(path.dirname(__file__), "data", "Packages")


class HTTPError(Exception):
    def __init__(self, code):
        self.code = code


class TestDebDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestDebDriver, cls).setUpClass()
        cls.driver = deb_driver.DebRepositoryDriver()
        cls.driver.logger = mock.MagicMock()

    def setUp(self):
        self.connection = mock.MagicMock()
        self.connection.HTTPError = HTTPError
        self.repo = gen_repository(
            name="trusty", section=("trusty", "main"), url="file:///repo"
        )

    def test_priority_sort(self):
        repos = [
            {"name": "repo0"},
            {"name": "repo1", "priority": 0},
            {"name": "repo2", "priority": 1000},
            {"name": "repo3", "priority": None}
        ]
        repos.sort(key=self.driver.priority_sort)

        self.assertEqual(
            ["repo2", "repo0", "repo3", "repo1"],
            [x['name'] for x in repos]
        )

    def test_get_repository(self):
        repos = []
        repo_data = {
            "name": "repo1", "uri": "http://host", "suite": "trusty",
            "section": ["main", "universe"], "path": "my_path"
        }
        self.connection.open_stream.return_value = {"Origin": "Ubuntu"}
        self.driver.get_repository(
            self.connection,
            repo_data,
            "x86_64",
            repos.append
        )
        self.connection.open_stream.assert_any_call(
            "http://host/dists/trusty/main/binary-amd64/Release"
        )
        self.connection.open_stream.assert_any_call(
            "http://host/dists/trusty/universe/binary-amd64/Release"
        )
        self.assertEqual(2, len(repos))
        repo = repos[0]
        self.assertEqual("repo1", repo.name)
        self.assertEqual(("trusty", "main"), repo.section)
        self.assertEqual("Ubuntu", repo.origin)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual("http://host/", repo.url)
        self.assertEqual("my_path", repo.path)
        repo = repos[1]
        self.assertEqual("repo1", repo.name)
        self.assertEqual(("trusty", "universe"), repo.section)
        self.assertEqual("Ubuntu", repo.origin)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual("http://host/", repo.url)

    def test_get_repository_if_release_does_not_exist(self):
        repo_data = {
            "name": "repo1", "uri": "http://host", "suite": "trusty",
            "section": ["main"], "path": "my_path"
        }
        repos = []
        self.connection.open_stream.side_effect = HTTPError(404)
        self.driver.get_repository(
            self.connection,
            repo_data,
            "x86_64",
            repos.append
        )
        self.assertEqual(1, len(repos))
        self.assertEqual("", repos[0].origin)

    def test_get_repository_fail_if_error(self):
        repo_data = {
            "name": "repo1", "uri": "http://host", "suite": "trusty",
            "section": ["main"], "path": "my_path"
        }
        repos = []
        self.connection.open_stream.side_effect = HTTPError(403)
        with self.assertRaises(HTTPError):
            self.driver.get_repository(
                self.connection,
                repo_data,
                "x86_64",
                repos.append
            )

    def test_get_flat_repository(self):
        with self.assertRaisesRegexp(ValueError, "does not supported"):
            self.driver.get_repository(
                self.connection,
                {"uri": "http://host", "suite": "trusty"},
                "x86_64",
                lambda x: None
            )

    def test_get_packages(self):
        packages = []
        with open(PACKAGES, "rb") as s:
            self.connection.open_stream.return_value = get_compressed(s)
            self.driver.get_packages(
                self.connection,
                self.repo,
                packages.append
            )

        self.connection.open_stream.assert_called_once_with(
            "file:///repo/dists/trusty/main/binary-amd64/Packages.gz",
        )
        self.assertEqual(1, len(packages))
        package = packages[0]
        self.assertEqual("test", package.name)
        self.assertEqual("1.1.1-1~u14.04+test", package.version)
        self.assertEqual(100, package.filesize)
        self.assertEqual(
            deb_driver.FileChecksum(
                '1ae09f80109f40dfbfaf3ba423c8625a',
                '402bd18c145ae3b5344edf07f246be159397fd40',
                '14d6e308d8699b7f9ba2fe1ef778c0e3'
                '8cf295614d308039d687b6b097d50859'),
            package.checksum
        )
        self.assertEqual(
            "pool/main/t/test.deb", package.filename
        )
        self.assertTrue(package.mandatory)
        self.assertItemsEqual(
            [
                'test-main (any)',
                'test2 (>= 0.8.16~exp9) | tes2-old (any)',
                'test3 (any)'
            ],
            (str(x) for x in package.requires)
        )
        self.assertItemsEqual(
            ["file (any)"],
            (str(x) for x in package.provides)
        )
        self.assertItemsEqual(
            [],
            (str(x) for x in package.obsoletes)
        )

    @mock.patch.multiple(
        "packetary.drivers.deb_driver",
        deb822=mock.DEFAULT,
        debfile=mock.DEFAULT,
        fcntl=mock.DEFAULT,
        gzip=mock.DEFAULT,
        utils=mock.DEFAULT,
        os=mock.DEFAULT,
        open=mock.DEFAULT
    )
    def test_add_packages(self, os, debfile, deb822, fcntl, gzip, utils, open):
        package = gen_package(name="test", repository=self.repo)
        os.path.join = lambda *x: "/".join(x)
        utils.get_path_from_url = lambda x: x[7:]

        files = [
            mock.MagicMock(),  # Packages, w
            mock.MagicMock(),  # Release, a+b
            mock.MagicMock(),  # Packages, rb
            mock.MagicMock(),  # Release, rb
            mock.MagicMock()   # Packages.gz, rb
        ]
        open.side_effect = files
        self.driver.add_packages(self.connection, self.repo, {package})
        open.assert_any_call(
            "/repo/dists/trusty/main/binary-amd64/Packages", "wb"
        )
        gzip.open.assert_called_once_with(
            "/repo/dists/trusty/main/binary-amd64/Packages.gz", "wb"
        )
        debfile.DebFile.assert_called_once_with("/repo/test.pkg")

    @mock.patch.multiple(
        "packetary.drivers.deb_driver",
        deb822=mock.DEFAULT,
        gzip=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
    )
    @mock.patch("packetary.drivers.deb_driver.utils.ensure_dir_exist")
    def test_fork_repository(self, mkdir_mock, deb822, gzip, open, os):
        os.path.sep = "/"
        os.path.join = lambda *x: "/".join(x)
        files = [
            mock.MagicMock(),
            mock.MagicMock()
        ]
        open.side_effect = files
        new_repo = self.driver.fork_repository(
            self.connection, self.repo, "/root/test"
        )
        self.assertEqual(self.repo.name, new_repo.name)
        self.assertEqual(self.repo.architecture, new_repo.architecture)
        self.assertEqual(self.repo.origin, new_repo.origin)
        self.assertEqual("file:///root/test/", new_repo.url)
        mkdir_mock.assert_called_once_with(os.path.dirname())
        open.assert_any_call(
            "/root/test/dists/trusty/main/binary-amd64/Release", "wb"
        )
        open.assert_any_call(
            "/root/test/dists/trusty/main/binary-amd64/Packages", "ab"
        )
        gzip.open.assert_called_once_with(
            "/root/test/dists/trusty/main/binary-amd64/Packages.gz", "ab"
        )

    @mock.patch.multiple(
        "packetary.drivers.deb_driver",
        fcntl=mock.DEFAULT,
        gzip=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
        utils=mock.DEFAULT
    )
    def test_update_suite_index(self, os, fcntl, gzip, open, utils):
        files = [
            mock.MagicMock(),  # Release, a+b
            mock.MagicMock(),  # Packages, rb
            mock.MagicMock(),  # Release, rb
            mock.MagicMock()   # Packages.gz, rb
        ]
        files[0].items.return_value = [
            ("SHA1", "invalid  1  main/binary-amd64/Packages\n"),
            ("Architectures", "i386"),
            ("Components", "restricted"),
        ]
        os.path.join = lambda *x: "/".join(x)
        open().__enter__.side_effect = files
        utils.get_path_from_url.return_value = "/root"
        utils.append_token_to_string.side_effect = [
            "amd64 i386", "main restricted"
        ]

        utils.get_size_and_checksum_for_files.return_value = (
            (
                "/root/dists/trusty/main/binary-amd64/{0}".format(name),
                10,
                (k + "_value" for k in deb_driver._CHECKSUM_METHODS)
            )
            for name in deb_driver._REPOSITORY_FILES
        )
        self.driver._update_suite_index(self.repo)
        open.assert_any_call("/root/dists/trusty/Release", "a+b")
        files[0].seek.assert_called_once_with(0)
        files[0].truncate.assert_called_once_with(0)
        files[0].write.assert_any_call(six.b("Architectures: amd64 i386\n"))
        files[0].write.assert_any_call(six.b("Components: main restricted\n"))
        for k in deb_driver._CHECKSUM_METHODS:
            files[0].write.assert_any_call(six.b(
                '{0}:\n'
                ' {1}               10 main/binary-amd64/Packages\n'
                ' {1}               10 main/binary-amd64/Release\n'
                ' {1}               10 main/binary-amd64/Packages.gz\n'
                .format(k, k + "_value")
            ))
        open.assert_any_call("/root/dists/trusty/Release", "a+b")
        fcntl.flock.assert_any_call(files[0].fileno(), fcntl.LOCK_EX)
        fcntl.flock.assert_any_call(files[0].fileno(), fcntl.LOCK_UN)

    @mock.patch.multiple(
        "packetary.drivers.deb_driver",
        deb822=mock.DEFAULT,
        gzip=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
    )
    @mock.patch("packetary.drivers.deb_driver.utils.ensure_dir_exist")
    def test_create_repository(self, mkdir_mock, deb822, gzip, open, os):
        repository_data = {
            "name": "Test", "uri": "file:///repo", "suite": "trusty",
            "section": "main", "type": "rpm", "priority": "100",
            "origin": "Origin", "path": "/repo"
        }
        repo = self.driver.create_repository(repository_data, "x86_64")
        self.assertEqual(repository_data["name"], repo.name)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual(repository_data["uri"] + "/", repo.url)
        self.assertEqual(repository_data["origin"], repo.origin)
        self.assertEqual(
            (repository_data["suite"], repository_data["section"]),
            repo.section
        )
        self.assertEqual(repository_data["path"], repo.path)
        mkdir_mock.assert_called_once_with(os.path.dirname())
        open.assert_any_call(
            "/repo/dists/trusty/main/binary-amd64/Release", "wb"
        )
        open.assert_any_call(
            "/repo/dists/trusty/main/binary-amd64/Packages", "ab"
        )
        gzip.open.assert_called_once_with(
            "/repo/dists/trusty/main/binary-amd64/Packages.gz", "ab"
        )

    def test_createrepository_fails_if_invalid_data(self):
        repository_data = {
            "name": "Test", "uri": "file:///repo", "suite": "trusty",
            "type": "rpm", "priority": "100",
            "origin": "Origin", "path": "/repo"
        }
        with self.assertRaisesRegexp(ValueError, "flat format"):
            self.driver.create_repository(repository_data, "x86_64")
        with self.assertRaisesRegexp(ValueError, "single component"):
            repository_data["section"] = ["main", "universe"]
            self.driver.create_repository(repository_data, "x86_64")

    @mock.patch.multiple(
        "packetary.drivers.deb_driver",
        debfile=mock.DEFAULT,
        open=mock.DEFAULT,
        os=mock.DEFAULT,
        utils=mock.DEFAULT,
    )
    def test_load_package_from_file(self, debfile, os, open, utils):
        fake_repo = gen_repository(
            name=("trusty", "main"), url="file:///repo"
        )
        file_info = ("/test.rpm", 2, [3, 4, 5])
        utils.get_size_and_checksum_for_files.return_value = [file_info]
        debfile.DebFile().control.get_content.return_value = {
            "package": "Test",
            "version": "2.7.9-1",
            "depends": "test1 (>= 2.2.1)",
            "replaces": "test2 (<< 2.2.1)",
            "recommends": "test3 (>> 2.2.1)",
            "provides": "test4 (>> 2.2.1)"
        }
        pkg = self.driver.load_package_from_file(
            fake_repo, "pool/main/t/test.deb"
        )

        self.assertEqual("Test", pkg.name)
        self.assertEqual("2.7.9-1", pkg.version)
        self.assertEqual("pool/main/t/test.deb", pkg.filename)
        self.assertEqual((3, 4, 5), pkg.checksum)
        self.assertEqual(2, pkg.filesize)
        self.assertItemsEqual(
            ['test1 (>= 2.2.1)', 'test3 (> 2.2.1)'],
            (str(x) for x in pkg.requires)
        )
        self.assertItemsEqual(
            ['test4 (> 2.2.1)'],
            (str(x) for x in pkg.provides)
        )
        self.assertEqual([], pkg.obsoletes)
        self.assertFalse(pkg.mandatory)

    def test_get_relative_path(self):
        repo = gen_repository(
            "test", "file://repo", section=("trusty", "main")
        )
        rel_path = self.driver.get_relative_path(repo, "test.pkg")
        self.assertEqual("pool/main/t/test.pkg", rel_path)

    def test_get_repository_data_scheme(self):
        schema = self.driver.get_repository_data_schema()
        self.assertIs(DEB_REPO_SCHEMA, schema)
