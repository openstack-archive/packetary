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

import abc
import logging

import six


@six.add_metaclass(abc.ABCMeta)
class RepositoryDriverBase(object):
    """The super class for Repository Drivers.

    For implementing support of new type of repository:
    - inherit this class
    - implement all abstract methods
    - register implementation in 'packetary.drivers' namespace
    """

    def __init__(self):
        self.logger = logging.getLogger(__package__)

    @abc.abstractmethod
    def get_repository(self, connection, repository_data, arch, consumer):
        """Loads the repository meta information from URL.

        :param connection: the connection manager instance
        :param repository_data: the repository`s url
        :param arch: the repository`s architecture
        :param consumer: the callback to consume result
        """

    @abc.abstractmethod
    def get_packages(self, connection, repository, consumer):
        """Loads packages from repository.

        :param connection: the connection manager instance
        :param repository: the repository object
        :param consumer: the callback to consume result
        """

    @abc.abstractmethod
    def fork_repository(self, connection, repository, destination, options):
        """Creates the new repository with same metadata.

        :param connection: the connection manager instance
        :param repository: the source repository
        :param destination: the destination folder
        :param options: the options
        :return: The copy of repository
        """

    @abc.abstractmethod
    def add_packages(self, connection, repository, packages):
        """Adds new packages to the repository.

        :param connection: the connection manager instance
        :param repository: the target repository
        :param packages: the set of packages
        """

    @abc.abstractmethod
    def create_repository(self, connection, repository_data, arch):
        """Create new repository.

        :param connection: the connection manager instance
        :param repository_data: repository input data
        :param arch: the repository`s architecture
        :return: new repository object
        """

    @abc.abstractmethod
    def load_package_from_file(self, repository, filepath):
        """Create package object from file.

        :param repository: the repository object
        :param filepath: the package path
        :return: new package object
        """

    @abc.abstractmethod
    def get_relative_path(self, repository, filename):
        """Gets the relative path from filename of package.

        :param repository: the repository object
        :param filename: the full package url
        :return: relative path
        """

    @abc.abstractmethod
    def get_priority(self, repo_data):
        """Get repository priority.

        :param repo_data: the repository`s description
        :return: the integer value that is relevant repository`s priority
                 less number means greater priority
        """

    @abc.abstractmethod
    def get_repository_data_schema(self):
        """Gets the json scheme for repository data validation."""


@six.add_metaclass(abc.ABCMeta)
class PackagingDriverBase(object):
    """The super class for Packaging Drivers.

    For implementing support of new type of packaging:
    - inherit this class
    - implement all abstract methods
    - register implementation in 'packetary.packaging_drivers' namespace
    """

    def __init__(self):
        self.logger = logging.getLogger(__package__)

    @abc.abstractmethod
    def get_data_schema(self):
        """Gets the json-schema to validate input data."""

    @abc.abstractmethod
    def get_for_caching(self, data):
        """Gets the list of url(s), that should be added to cache."""

    @abc.abstractmethod
    def build_packages(self, data, cache, output_dir, consumer):
        """Build package from sources.

        :param data: the input data
        :param cache: the cache instance with resources, which is downloaded
        :param output_dir: directory for new packages
        :param consumer: callable, that will be called for each built package
        """
