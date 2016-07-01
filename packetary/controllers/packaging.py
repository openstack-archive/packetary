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
        return {
            "$schema": "http://json-schema.org/draft-04/schema#",
            "type": "object",
            "required": ["src", self.driver.get_section_name()],
            "properties": {
                "src": {"type": "string"},
                self.driver.get_section_name(): self.driver.get_data_schema()
            }
        }

    def build_packages(self, data, output_dir, consumer):
        """Build package from sources.

        :param data: the input data for building packages,
                     the format of data depends on selected driver
        :param output_dir: directory for new packages
        :param consumer: callable, that will be called for each built package
        """

        driver_data = data[self.driver.get_section_name()]

        with self.context.async_section() as section:
            result = {}
            mapping = {
                'src': data['src'],
                'spec': self.driver.get_spec(driver_data)
            }
            for key, value in mapping.items():
                section.execute(self._ensure_local_path, value, key, result)

        return self.driver.build_packages(
            result['src'],
            result['spec'],
            self.driver.get_options(driver_data),
            output_dir,
            consumer
        )

    def _ensure_local_path(self, url, key, output):
        path = utils.get_path_from_url(url, ensure_file=False)
        if not utils.is_local(url):
            path = os.path.join(
                self.context.cache_dir, utils.get_filename_from_uri(path)
            )
            self.context.connection.retrieve(url, path)
        output[key] = path
