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
import os.path

from packetary.api.context import Context
from packetary.api.validators import declare_schema
from packetary.controllers import PackagingController
from packetary.library import utils


logger = logging.getLogger(__package__)


class PackagingApi(object):
    """Provides high-level API to build packages."""

    def __init__(self, controller):
        """Initialises.

        :param controller: the packaging controller.
        :type controller: PackagingController
        """
        self.controller = controller

    def _get_data_schema(self):
        return {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'array',
            'items': self.controller.get_data_schema()
        }

    @classmethod
    def create(cls, config, driver_type, driver_config):
        """Creates the packaging API instance.

        :param config: the global config
        :param driver_type: the name of driver which will be used
        :param driver_config: the config of driver

        :return PackagingApi instance
        """
        context = config if isinstance(config, Context) else Context(config)
        return cls(
            PackagingController.load(context, driver_type, driver_config)
        )

    @declare_schema(sources=_get_data_schema)
    def build_packages(self, sources, output_dir):
        """Builds new package(s).

        :param sources: list descriptions of packages for building
        :param output_dir: directory for new packages
        :return: list of names of packages which was built
        """
        output_dir = os.path.abspath(output_dir)
        utils.ensure_dir_exist(output_dir)
        packages = []
        for source in sources:
            self.controller.build_packages(source, output_dir, packages.append)
        return packages
