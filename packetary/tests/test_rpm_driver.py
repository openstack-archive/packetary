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
import sys

import six

from packetary.objects import FileChecksum
from packetary.schemas import RPM_REPO_SCHEMA
from packetary.tests import base
from packetary.tests.stubs.generator import gen_repository
from packetary.tests.stubs.helpers import get_compressed
from packetary.tests.stubs.helpers import read_to_buffer


REPOMD = path.join(path.dirname(__file__), "data", "repomd.xml")

REPOMD2 = path.join(path.dirname(__file__), "data", "repomd2.xml")

PRIMARY_DB = path.join(path.dirname(__file__), "data", "primary.xml")

GROUPS_DB = path.join(path.dirname(__file__), "data", "groups.xml")


class TestRpmDriver(base.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.modules["createrepo"] = mock.MagicMock()
        from packetary.drivers import rpm_driver
        cls.createrepo = rpm_driver.createrepo = mock.MagicMock()

        super(TestRpmDriver, cls).setUpClass()
        cls.driver = rpm_driver.RpmRepositoryDriver()
        cls.driver.logger = mock.MagicMock()

    def setUp(self):
        self.createrepo.reset_mock()
        self.connection = mock.MagicMock()

    def configure_streams(self, groups_gzipped=True):
        streams = []
        if groups_gzipped:
            groups_conv = get_compressed
            md_file = REPOMD
        else:
            groups_conv = read_to_buffer
            md_file = REPOMD2

        for conv, fname in six.moves.zip(
            (read_to_buffer, groups_conv, get_compressed),
            (md_file, GROUPS_DB, PRIMARY_DB)
        ):
            with open(fname, "rb") as s:
                streams.append(conv(s))

        self.connection.open_stream.side_effect = streams

    def test_priority_sort(self):
        repos = [
            {"name": "repo0"},
            {"name": "repo1", "priority": 1},
            {"name": "repo2", "priority": 99},
            {"name": "repo3", "priority": None}
        ]
        repos.sort(key=self.driver.priority_sort)

        self.assertEqual(
            ["repo1", "repo0", "repo3", "repo2"],
            [x['name'] for x in repos]
        )

    def test_get_repository(self):
        repos = []
        repo_data = {
            "name": "os", "uri": "http://host/centos/os/x86_64/",
            "path": "centos"
        }
        self.driver.get_repository(
            self.connection,
            repo_data,
            "x86_64",
            repos.append
        )

        self.assertEqual(1, len(repos))
        repo = repos[0]
        self.assertEqual("os", repo.name)
        self.assertEqual("", repo.origin)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual("http://host/centos/os/x86_64/", repo.url)
        self.assertEqual("centos", repo.path)

    def test_get_packages(self):
        self.configure_streams()
        packages = []
        self.driver.get_packages(
            self.connection,
            gen_repository("test", url="http://host/centos/os/x86_64/"),
            packages.append
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/repomd.xml"
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/groups.xml.gz"
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/primary.xml.gz"
        )
        self.assertEqual(2, len(packages))
        package = packages[0]
        self.assertEqual("test1", package.name)
        self.assertEqual("1.1.1.1-1.el7", package.version)
        self.assertEqual(100, package.filesize)
        self.assertEqual(
            FileChecksum(
                None,
                None,
                'e8ed9e0612e813491ed5e7c10502a39e'
                '43ec665afd1321541dea211202707a65'),
            package.checksum
        )
        self.assertEqual(
            "Packages/test1.rpm", package.filename
        )
        self.assertItemsEqual(
            ['test2 (= 0-1.1.1.1-1.el7)'],
            (str(x) for x in package.requires)
        )
        self.assertItemsEqual(
            ["file (any)"],
            (str(x) for x in package.provides)
        )
        self.assertItemsEqual(
            ["test-old (any)"],
            (str(x) for x in package.obsoletes)
        )
        self.assertTrue(package.mandatory)
        self.assertFalse(packages[1].mandatory)

    def test_get_packages_if_group_not_gzipped(self):
        self.configure_streams(False)
        packages = []
        self.driver.get_packages(
            self.connection,
            gen_repository("test", url="http://host/centos/os/x86_64/"),
            packages.append
        )
        self.connection.open_stream.assert_any_call(
            "http://host/centos/os/x86_64/repodata/groups.xml"
        )
        self.assertEqual(2, len(packages))
        package = packages[0]
        self.assertTrue(package.mandatory)

    @mock.patch("packetary.drivers.rpm_driver.os")
    @mock.patch("packetary.drivers.rpm_driver.open")
    def test_add_packages_to_existing(self, open_mock, os_mock):
        self.configure_streams()
        tmp_file = mock.MagicMock()
        tmp_file.name = "/tmp/groups.gz"
        open_mock.return_value.__enter__.return_value = tmp_file
        repo = gen_repository("test", url="file:///repo/os/x86_64")
        md_gen = mock.MagicMock()
        self.createrepo.MetaDataGenerator.return_value = md_gen
        md_gen.outputdir = "/repo/os/x86_64"
        md_gen.tempdir = "tmp"
        md_gen.finaldir = "repodata"
        os_mock.path.exists.return_value = True
        os_mock.path.join.side_effect = [
            "/repo/os/x86_64/tmp",
            tmp_file.name,
            "/repo/os/x86_64/tmp"
        ]
        self.driver.add_packages(self.connection, repo, set())
        self.assertEqual(
            "/repo/os/x86_64",
            self.createrepo.MetaDataConfig().directory
        )
        self.assertTrue(self.createrepo.MetaDataConfig().update)
        md_gen.doPkgMetadata.assert_called_once_with()
        md_gen.doRepoMetadata.assert_called_once_with()
        md_gen.doFinalMove.assert_called_once_with()

        self.assertGreater(tmp_file.write.call_count, 0)
        self.assertEqual(
            tmp_file.name, self.createrepo.MetaDataConfig().groupfile
        )
        os_mock.unlink.assert_called_once_with(tmp_file.name)

    @mock.patch("packetary.drivers.rpm_driver.os")
    @mock.patch("packetary.drivers.rpm_driver.shutil")
    @mock.patch("packetary.drivers.rpm_driver.open")
    def test_add_packages_clean_metadata_on_error(
            self, open_mock, shutil_mock, os_mock
    ):
        self.configure_streams()
        tmp_file = mock.MagicMock()
        tmp_file.name = "/tmp/groups.gz"
        open_mock.return_value.__enter__.return_value = tmp_file
        self.createrepo.MDError = ValueError
        md_gen = mock.MagicMock()
        self.createrepo.MetaDataGenerator.return_value = md_gen
        md_gen.doFinalMove.side_effect = self.createrepo.MDError()

        repo = gen_repository("test", url="file:///repo/os/x86_64")
        self.createrepo.MetaDataConfig().outputdir = "/repo/os/x86_64"
        self.createrepo.MetaDataConfig().tempdir = "tmp"
        self.createrepo.MetaDataConfig().finaldir = "repodata"
        os_mock.path.exists.return_value = True
        os_mock.path.join.side_effect = [
            "/repo/os/x86_64/tmp",
            tmp_file.name,
            "/repo/os/x86_64/tmp"
        ]
        with self.assertRaises(RuntimeError):
            self.driver.add_packages(self.connection, repo, set())
        shutil_mock.rmtree.assert_called_once_with(
            "/repo/os/x86_64/tmp", ignore_errors=True
        )
        os_mock.unlink.assert_called_once_with(tmp_file.name)

    @mock.patch("packetary.drivers.rpm_driver.os")
    @mock.patch("packetary.drivers.rpm_driver.open")
    @mock.patch("packetary.drivers.rpm_driver.utils.ensure_dir_exist")
    def test_fork_repository_to_empty_destination(
            self, m_ensure_dir_exists, m_open, m_os
    ):
        self.configure_streams()
        tmp_file = mock.MagicMock()
        tmp_file.name = "/tmp/groups.gz"
        m_open.return_value.__enter__.return_value = tmp_file
        repo = gen_repository("os", url="http://localhost/os/x86_64/")
        md_gen = mock.MagicMock()
        self.createrepo.MetaDataGenerator.return_value = md_gen
        md_gen.doFinalMove.side_effect = [None]
        md_gen.outputdir = "/repo/os/x86_64"
        md_gen.tempdir = "tmp"
        md_gen.finaldir = "repodata"
        md_config = mock.MagicMock()
        self.createrepo.MetaDataConfig.return_value = md_config
        m_os.path.join.side_effect = [
            "/repo/os/x86_64/repodata/repomd.xml",
            tmp_file.name,
            "/repo/os/x86_64/tmp"
        ]
        m_os.path.exists.return_value = False
        new_repo = self.driver.fork_repository(
            self.connection,
            repo,
            "/repo/os/x86_64"
        )
        m_ensure_dir_exists.assert_called_once_with("/repo/os/x86_64")
        self.assertEqual(repo.name, new_repo.name)
        self.assertEqual(repo.architecture, new_repo.architecture)
        self.assertEqual("file:///repo/os/x86_64/", new_repo.url)
        md_gen.doFinalMove.assert_called_once_with()
        self.assertGreater(tmp_file.write.call_count, 0)
        self.assertEqual(["*"], md_config.excludes)
        self.assertFalse(md_config.update)
        self.assertEqual(tmp_file.name, md_config.groupfile)
        m_open.assert_called_once_with(tmp_file.name, "w")
        m_os.unlink.assert_called_once_with(tmp_file.name)

    @mock.patch("packetary.drivers.rpm_driver.os")
    @mock.patch("packetary.drivers.rpm_driver.open")
    @mock.patch("packetary.drivers.rpm_driver.utils.ensure_dir_exist")
    def test_fork_repository_to_existing_destination(
            self, ensure_dir_exists_mock, open_mock, os_mock
    ):
        self.configure_streams()
        tmp_file = mock.MagicMock()
        tmp_file.name = "/tmp/groups.gz"
        open_mock.return_value.__enter__.return_value = tmp_file
        repo = gen_repository("os", url="http://localhost/os/x86_64/")
        md_gen = mock.MagicMock()
        self.createrepo.MetaDataGenerator.return_value = md_gen
        md_gen.doFinalMove.side_effect = [None]
        md_gen.outputdir = "/repo/os/x86_64"
        md_gen.tempdir = "tmp"
        md_gen.finaldir = "repodata"
        md_config = mock.MagicMock()
        self.createrepo.MetaDataConfig.return_value = md_config
        os_mock.path.join.side_effect = [
            "/repo/os/x86_64/repodata/repomd.xml",
            tmp_file.name,
            "/repo/os/x86_64/tmp"
        ]
        os_mock.path.exists.return_value = True
        groups_xml = mock.MagicMock()
        with mock.patch.object(self.driver, "_load_groups") as load_mock:
            load_mock.side_effect = [None, groups_xml]
            self.driver.fork_repository(
                self.connection,
                repo,
                "/repo/os/x86_64"
            )
        self.assertEqual(tmp_file.name, md_config.groupfile)
        os_mock.unlink.assert_called_once_with(tmp_file.name)
        groups_xml.write.assert_called_once_with(tmp_file)

    @mock.patch("packetary.drivers.rpm_driver.os")
    @mock.patch("packetary.drivers.rpm_driver.open")
    @mock.patch("packetary.drivers.rpm_driver.utils.ensure_dir_exist")
    def test_create_repository(
            self, ensure_dir_exists_mock, open_mock, os_mock
    ):
        repository_data = {
            "name": "Test", "uri": "file:///repo/os/x86_64", "origin": "Test",
            "path": "centos"
        }
        self.configure_streams()
        md_gen = mock.MagicMock()
        self.createrepo.MetaDataGenerator.return_value = md_gen
        md_gen.doFinalMove.side_effect = [None]
        md_gen.outputdir = "/repo/os/x86_64"
        md_gen.tempdir = "tmp"
        md_gen.finaldir = "repodata"
        md_config = mock.MagicMock()
        self.createrepo.MetaDataConfig.return_value = md_config

        repo = self.driver.create_repository(
            self.connection, repository_data, "x86_64"
        )
        ensure_dir_exists_mock.assert_called_once_with("/repo/os/x86_64/")
        self.assertEqual(repository_data["name"], repo.name)
        self.assertEqual("x86_64", repo.architecture)
        self.assertEqual(repository_data["uri"] + "/", repo.url)
        self.assertEqual(repository_data["origin"], repo.origin)
        self.assertEqual(repository_data["path"], repo.path)
        md_gen.doFinalMove.assert_called_once_with()
        self.assertEqual(["*"], md_config.excludes)
        self.assertFalse(md_config.update)
        open_mock.assert_not_called()
        os_mock.unlink.assert_not_called()

    @mock.patch("packetary.drivers.rpm_driver.utils")
    def test_load_package_from_file(self, utils):
        file_info = ("/test.rpm", 2, [3, 4, 5])
        utils.get_size_and_checksum_for_files.return_value = [file_info]
        utils.get_path_from_url.return_value = "/repo/x86_64/test.rpm"
        rpm_mock = mock.MagicMock(
            requires=[('test1', 'EQ', ('0', '1.2.3', '1.el5'))],
            provides=[('test2', None, (None, None, None))],
            obsoletes=[]
        )
        self.createrepo.yumbased.YumLocalPackage.return_value = rpm_mock
        rpm_mock.returnLocalHeader.return_value = {
            "name": "Test", "epoch": 1, "version": "1.2.3", "release": "1",
            "size": "10", "group": "Group"
        }
        repo = gen_repository("Test", url="file:///repo/os/x86_64/")
        pkg = self.driver.load_package_from_file(repo, "test.rpm")
        utils.get_path_from_url.assert_called_once_with(
            "file:///repo/os/x86_64/test.rpm"
        )
        self.createrepo.yumbased.YumLocalPackage.assert_called_once_with(
            filename="/repo/x86_64/test.rpm"
        )
        utils.get_size_and_checksum_for_files.assert_called_once_with(
            ["/repo/x86_64/test.rpm"], mock.ANY
        )

        self.assertEqual("Test", pkg.name)
        self.assertEqual("1-1.2.3-1", str(pkg.version))
        self.assertEqual("test.rpm", pkg.filename)
        self.assertEqual((3, 4, 5), pkg.checksum)
        self.assertEqual("Group", pkg.group)
        self.assertEqual(10, pkg.filesize)
        self.assertItemsEqual(
            ['test1 (= 0-1.2.3-1.el5)'],
            (str(x) for x in pkg.requires)
        )
        self.assertItemsEqual(
            ['test2 (any)'],
            (str(x) for x in pkg.provides)
        )
        self.assertEqual([], pkg.obsoletes)
        self.assertEqual(pkg.mandatory, False)

    def test_get_relative_path(self):
        repo = gen_repository(
            "test", "file://repo", section=("trusty", "main")
        )
        rel_path = self.driver.get_relative_path(repo, "test.pkg")
        self.assertEqual("packages/test.pkg", rel_path)

    def test_get_repository_data_schema(self):
        schema = self.driver.get_repository_data_schema()
        self.assertIs(RPM_REPO_SCHEMA, schema)
