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

import logging
import os

import six
import stevedore

from packetary.library import utils

logger = logging.getLogger(__package__)

urljoin = six.moves.urllib.parse.urljoin


class RepositoryController(object):
    """Implements low-level functionality to communicate with drivers."""

    _drivers = None

    def __init__(self, context, driver, arch):
        self.context = context
        self.driver = driver
        self.arch = arch

    @classmethod
    def load(cls, context, driver_name, repoarch):
        """Creates the repository manager.

        :param context: the context
        :param driver_name: the name of required driver
        :param repoarch: the architecture of repository (x86_64 or i386)
        """
        if cls._drivers is None:
            cls._drivers = stevedore.ExtensionManager(
                "packetary.drivers", invoke_on_load=True
            )
        try:
            driver = cls._drivers[driver_name].obj
        except KeyError:
            raise NotImplementedError(
                "The driver {0} is not supported yet.".format(driver_name)
            )
        return cls(context, driver, repoarch)

    def load_repositories(self, repositories_data):
        """Loads the repository objects from url.

        :param repositories_data: the list of repository`s descriptions
        :return: the list of repositories sorted according to priority
        """

        connection = self.context.connection
        repositories_data.sort(key=self.driver.priority_sort)
        repos = []
        for repo_data in repositories_data:
            self.driver.get_repository(
                connection, repo_data, self.arch, repos.append
            )
        return repos

    def load_packages(self, repository, consumer):
        """Loads packages from repository.

        :param repository: the repository object
        :param consumer: the callback to consume objects
        """
        connection = self.context.connection
        self.driver.get_packages(connection, repository, consumer)

    def fork_repository(self, repository, destination, source, locale):
        """Creates copy of repositories.

        :param repository: the origin repository
        :param destination: the target folder
        :param source: If True, the source packages will be copied too.
        :param locale: If True, the localisation will be copied too.
        :return: the mapping origin to cloned repository.
        """
        new_path = os.path.join(
            destination,
            repository.path or utils.get_path_from_url(repository.url, False)
        )
        logger.info("cloning repository '%s' to '%s'", repository, new_path)
        return self.driver.fork_repository(
            self.context.connection, repository, new_path, source, locale
        )

    def assign_packages(self, repository, packages, observer=None):
        """Assigns new packages to the repository.

         It replaces the current repository`s packages.

        :param repository: the target repository
        :param packages: the set of new packages
        :param observer: the package copying process observer
        """
        if not isinstance(packages, set):
            packages = set(packages)
        else:
            packages = packages.copy()

        self._copy_packages(repository, packages, observer)
        self.driver.add_packages(
            self.context.connection, repository, packages
        )

    def create_repository(self, repository_data, package_files):
        """Creates new repository from specified packages.

        :param repository_data: the description of repository
        :param package_files: the list of paths of packages
        :return : the new repository
        """
        repo = self.driver.create_repository(repository_data, self.arch)
        packages = set()
        with self.context.async_section() as section:
            for url in package_files:
                section.execute(self._add_package, repo, url, packages.add)

        self.assign_packages(repo, packages)
        return repo

    def get_repository_data_schema(self):
        """Return jsonschema to validate data for required driver.

        :return : Return a jsonschema represented as a dict
        """
        return self.driver.get_repository_data_schema()

    def _copy_packages(self, target, packages, observer):
        with self.context.async_section() as section:
            for package in packages:
                section.execute(
                    self._copy_package, target, package, observer
                )

    def _copy_package(self, target, package, observer):
        if package.repository is None:
            src_url = package.filename
            dst_path = self.driver.get_relative_path(
                target, utils.get_filename_from_uri(package.filename)
            )
        elif target.url != package.repository.url:
            src_url = urljoin(package.repository.url, package.filename)
            dst_path = package.filename
        else:
            return

        bytes_copied = self.context.connection.retrieve(
            src_url,
            utils.get_path_from_url(urljoin(target.url, dst_path)),
            size=package.filesize
        )
        if package.filesize < 0:
            package.filesize = bytes_copied
        if observer:
            observer(bytes_copied)

    def _add_package(self, repository, src_url, consumer):
        dst_path = self.driver.get_relative_path(
            repository, utils.get_filename_from_uri(src_url)
        )
        self.context.connection.retrieve(
            src_url,
            utils.get_path_from_url(urljoin(repository.url, dst_path))
        )
        consumer(self.driver.load_package_from_file(repository, dst_path))
