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

from packetary.controllers import PackagingController

logger = logging.getLogger(__package__)


class PackagingApi(object):
    """Provides high-level API to build packages."""

    def __init__(self, controller):
        """Initialises.

        :param controller: the packaging controller.
        :type controller: object
        """
        self.controller = controller

    @classmethod
    def create(cls, pkg_type):
        """Creates the packaging API instance.

        :param pkg_type: package type
        :type pkg_type: str

        :return PackagingApi instance
        :rtype object
        """
        return cls(PackagingController.load(pkg_type))

    def build_packages(self, packages_config, output_dir, repos):
        """Build new package.

        :param packages_config: list of building packages parameters
        :type packages_config: list[dict]

        :param output_dir: directory for new packages
        :type output_dir: str

        :param repos: list of build chroot repositories
        :type repos: list

        :return: list of builded packages
        :rtype: list[str]
        """
        result = []
        for package_config in packages_config:
            packages = self.controller.build_packages(
                package_config.get('release', None),
                package_config.get('src', package_config.get('source', './')),
                package_config.get('spec', None),
                output_dir,
                repos
            )

            result.append((
                package_config.get('src', package_config.get('source', './')),
                packages
            ))

        return result
