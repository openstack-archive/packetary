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

from packetary.api import context

from packetary.tests import base


class TestContext(base.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = context.Configuration(
            threads_num=2,
            ignore_errors_num=3,
            retries_num=5,
            retry_interval=10,
            http_proxy="http://localhost",
            https_proxy="https://localhost",
            cache_dir="/root/cache"
        )

    @mock.patch("packetary.api.context.ConnectionsManager")
    def test_initialise_connection_manager(self, conn_manager):
        ctx = context.Context(self.config)
        conn_manager.assert_called_once_with(
            proxy="http://localhost",
            secure_proxy="https://localhost",
            retries_num=5,
            retry_interval=10
        )

        self.assertIs(conn_manager(), ctx.connection)

    @mock.patch("packetary.api.context.AsynchronousSection")
    def test_asynchronous_section(self, async_section):
        ctx = context.Context(self.config)
        s = ctx.async_section()
        async_section.assert_called_with(2, 3)
        self.assertIs(s, async_section())
        ctx.async_section(0)
        async_section.assert_called_with(2, 0)

    @mock.patch("packetary.api.context.tempfile")
    def test_cache_dir(self, tempfile_mock):
        ctx = context.Context(self.config)
        self.assertEqual(self.config.cache_dir, ctx.cache_dir)
        self.config.cache_dir = None
        tempfile_mock.gettempdir.return_value = '/tmp'
        ctx2 = context.Context(self.config)
        self.assertEqual('/tmp/packetary-cache', ctx2.cache_dir)
