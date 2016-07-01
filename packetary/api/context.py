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

import os
import tempfile

from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection


class Configuration(object):
    """The configuration holder."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_num=0, retry_interval=0, threads_num=0,
                 ignore_errors_num=0, cache_dir=None):
        """Initialises.

        :param http_proxy: the url of proxy for connections over http,
                           no-proxy will be used if it is not specified
        :param https_proxy: the url of proxy for connections over https,
                            no-proxy will be used if it is not specified
        :param retries_num: the number of retries on errors
        :param retry_interval: the minimal time between retries (in seconds)
        :param threads_num: the max number of active threads
        :param ignore_errors_num: the number of errors that may occurs
                before stop processing
        :param cache_dir: the path to directory were will be downloaded
                        remote files
        """

        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ignore_errors_num = ignore_errors_num
        self.retries_num = retries_num
        self.retry_interval = retry_interval
        self.threads_num = threads_num
        self.cache_dir = cache_dir


class Context(object):
    """The infra-objects holder."""

    def __init__(self, config):
        """Initialises.

        :param config: the configuration
        """
        self._connection = ConnectionsManager(
            proxy=config.http_proxy,
            secure_proxy=config.https_proxy,
            retries_num=config.retries_num,
            retry_interval=config.retry_interval
        )
        self._threads_num = config.threads_num
        self._ignore_errors_num = config.ignore_errors_num
        if config.cache_dir:
            self._cache_dir = config.cache_dir
        else:
            self._cache_dir = os.path.join(
                tempfile.gettempdir(), 'packetary-cache'
            )

    @property
    def connection(self):
        """Gets the connection."""
        return self._connection

    @property
    def cache_dir(self):
        return self._cache_dir

    def async_section(self, ignore_errors_num=None):
        """Gets the execution scope.

        :param ignore_errors_num: custom value for ignore_errors_num,
                                  the class value is used if omitted.
        """
        if ignore_errors_num is None:
            ignore_errors_num = self._ignore_errors_num

        return AsynchronousSection(self._threads_num, ignore_errors_num)
