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

import logging
import os

import six
import stevedore

from packetary.library import utils

logger = logging.getLogger(__package__)

urljoin = six.moves.urllib.parse.urljoin


class PackagingController(object):
    """Implements low-level functionality to communicate with drivers."""

    _drivers = None

    def __init__(self, context, driver):
        self.context = context
        self.driver = driver

    @classmethod
    def load(cls, context, driver_name, driver_config):
        """Creates the packaging manager."""
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager(
                "packetary.packaging_drivers", invoke_on_load=True,
                invoke_args=(driver_config,)
            )
        try:
            driver = cls._drivers[driver_name].obj
        except KeyError:
            raise NotImplementedError(
                "The driver {0} is not supported yet.".format(driver_name)
            )
        return cls(context, driver)

    def get_data_schema(self):
        """Return jsonschema to validate data, which will be pass to driver

        :return : Return a jsonschema represented as a dict
        """
        return self.driver.get_data_schema()

    def build_packages(self, data, output_dir, consumer):
        """Build package from sources.

        :param data: the input data for building packages,
                     the format of data depends on selected driver
        :param output_dir: directory for new packages
        :param consumer: callable, that will be called for each built package
        """

        cache = {}
        with self.context.async_section() as section:
            for url in self.driver.get_for_caching(data):
                section.execute(self._add_to_cache, url, cache)

        return self.driver.build_packages(data, cache, output_dir, consumer)

    def _add_to_cache(self, url, cache):
        path = utils.get_path_from_url(url, ensure_file=False)
        if not utils.is_local(url):
            path = os.path.join(
                self.context.cache_dir, utils.get_filename_from_uri(path)
            )
            self.context.connection.retrieve(url, path)
        cache[url] = path
