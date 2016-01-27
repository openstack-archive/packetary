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

from packetary.library import utils
from packetary.tests import base


class TestLibraryUtils(base.TestCase):

    def test_append_token_to_string(self):
        cases = [
            ("v1 v2 v3", ("v2 v3", "v1")),
            ("v1", ("", "v1")),
            ("v1 v2 v3 v4", ("v1\tv2   v3", "v4")),
            ("v1 v2 v3", ("v1 v2 v3", "v1")),
        ]
        self._check_cases(
            self.assertEqual, cases, utils.append_token_to_string
        )

    def test_composite_writer(self):
        fds = [
            mock.MagicMock(),
            mock.MagicMock()
        ]
        writer = utils.composite_writer(*fds)
        writer(u"text1")
        writer(b"text2")
        for fd in fds:
            fd.write.assert_any_call(b"text1")
            fd.write.assert_any_call(b"text2")

    @mock.patch.multiple(
        "packetary.library.utils",
        os=mock.DEFAULT,
        open=mock.DEFAULT
    )
    def test_get_size_and_checksum_for_files(self, os, open):
        files = [
            "/file1.txt",
            "/file2.txt"
        ]
        os.fstat.side_effect = [
            mock.MagicMock(st_size=1),
            mock.MagicMock(st_size=2)
        ]
        r = list(utils.get_size_and_checksum_for_files(
            files, mock.MagicMock(side_effect=["1", "2"])
        ))
        self.assertEqual(
            [("/file1.txt", 1, "1"), ("/file2.txt", 2, "2")],
            r
        )

    def test_get_path_from_url(self):
        cases = [
            ("/a/f.txt", ("/a/f.txt",)),
            ("/a/f.txt", ("file:///a/f.txt?size=1",)),
            ("/f.txt", ("http://host/f.txt", False)),
        ]
        self._check_cases(self.assertEqual, cases, utils.get_path_from_url)
        with self.assertRaises(ValueError):
            utils.get_path_from_url("http:///a/f.txt")

    @mock.patch("packetary.library.utils.os")
    def test_normalize_repository_url(self, os_mock):
        def abs_patch_mock(p):
            if p.startswith("/"):
                return p
            return "/root/" + p[2:]

        os_mock.sep = "/"
        os_mock.path.abspath.side_effect = abs_patch_mock

        cases = [
            ("file:///repo/", ("/repo",)),
            ("file:///root/repo/", ("./repo",)),
            ("http://localhost/repo/", ("http://localhost/repo",)),
            ("http://localhost/repo/", ("http://localhost/repo/",)),
        ]
        self._check_cases(
            self.assertEqual, cases, utils.normalize_repository_url
        )

    @mock.patch("packetary.library.utils.os")
    def test_ensure_dir_exist(self, os):
        os.makedirs.side_effect = [
            True,
            OSError(utils.errno.EEXIST, ""),
            OSError(utils.errno.EACCES, ""),
            ValueError()
        ]
        utils.ensure_dir_exist("/nonexisted")
        os.makedirs.assert_called_with("/nonexisted")
        utils.ensure_dir_exist("/existed")
        os.makedirs.assert_called_with("/existed")
        with self.assertRaises(OSError):
            utils.ensure_dir_exist("/private")
        with self.assertRaises(ValueError):
            utils.ensure_dir_exist(1)

    def test_get_filename_from_uri(self):
        cases = [
            ("test.pkg", ("test.pkg",)),
            ("test.pkg", ("/root/test.pkg",)),
            ("test.pkg", ("file:///root/test.pkg",)),
            ("", ("file:///root/",))
        ]
        self._check_cases(self.assertEqual, cases, utils.get_filename_from_uri)
