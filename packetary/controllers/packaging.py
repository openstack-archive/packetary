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

import six
import stevedore

logger = logging.getLogger(__package__)

urljoin = six.moves.urllib.parse.urljoin


class PackagingController(object):
    """Implements low-level functionality to communicate with drivers."""

    _drivers = None

    def __init__(self, pkg_driver):
        self.driver = pkg_driver

    @classmethod
    def load(cls, pkg_type):
        """Creates the packaging manager.

        """
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager(
                "packetary.packaging_drivers", invoke_on_load=True
            )
        try:
            driver = cls._drivers[pkg_type].obj
        except KeyError:
            raise NotImplementedError(
                "The driver {0} is not supported yet.".format(pkg_type)
            )
        return cls(driver)

    def build_packages(self, release, sources):
        """Build package from sources.

        :param release: os release, like "centos-7-x86_64"
        :param sources: path to sources
        :return : path to packages
        """
        return self.driver.build_packages(
            release,
            sources
        )
