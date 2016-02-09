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

from collections import defaultdict
import logging

import jsonschema
import six

from packetary.controllers import RepositoryController
from packetary.library.connections import ConnectionsManager
from packetary.library.executor import AsynchronousSection
from packetary.objects import PackageRelation
from packetary.objects import PackagesForest
from packetary.objects import PackagesTree
from packetary.objects.statistics import CopyStatistics
from packetary.schemas import PACKAGE_FILES_SCHEMA
from packetary.schemas import PACKAGES_SCHEMA

logger = logging.getLogger(__package__)


class Configuration(object):
    """The configuration holder."""

    def __init__(self, http_proxy=None, https_proxy=None,
                 retries_num=0, retry_interval=0, threads_num=0,
                 ignore_errors_num=0):
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
        """

        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.ignore_errors_num = ignore_errors_num
        self.retries_num = retries_num
        self.retry_interval = retry_interval
        self.threads_num = threads_num


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

    @property
    def connection(self):
        """Gets the connection."""
        return self._connection

    def async_section(self, ignore_errors_num=None):
        """Gets the execution scope.

        :param ignore_errors_num: custom value for ignore_errors_num,
                                  the class value is used if omitted.
        """
        if ignore_errors_num is None:
            ignore_errors_num = self._ignore_errors_num

        return AsynchronousSection(self._threads_num, ignore_errors_num)


class RepositoryApi(object):
    """Provides high-level API to operate with repositories."""

    def __init__(self, controller):
        """Initialises.

        :param controller: the repository controller.
        """
        self.controller = controller

    @classmethod
    def create(cls, config, repotype, repoarch):
        """Creates the repository API instance.

        :param config: the configuration
        :param repotype: the kind of repository(deb, yum, etc)
        :param repoarch: the architecture of repository (x86_64 or i386)
        """
        context = config if isinstance(config, Context) else Context(config)
        return cls(RepositoryController.load(context, repotype, repoarch))

    def create_repository(self, repo_data, package_files):
        """Create new repository with specified packages.

        :param repo_data: The description of repository
        :param package_files: The list of URLs of packages
        """
        self._validate_repo_data(repo_data)
        self._validate_package_files(package_files)
        return self.controller.create_repository(repo_data, package_files)

    def get_packages(self, repos_data, requirements_data=None,
                     include_mandatory=False):
        """Gets the list of packages from repository(es).

        :param repos_data: The list of repository descriptions
        :param requirements_data: The list of package`s requirements
                                  that should be included
        :param include_mandatory: if True, all mandatory packages will be
        :return: the set of packages
        """
        repos = self._load_repositories(repos_data)
        requirements = self._load_requirements(requirements_data)
        return self._get_packages(repos, requirements, include_mandatory)

    def clone_repositories(self, repos_data, requirements_data, destination,
                           include_source=False, include_locale=False,
                           include_mandatory=False):
        """Creates the clones of specified repositories in local folder.

        :param repos_data: The list of repository descriptions
        :param requirements_data: The list of package`s requirements
                                  that should be included
        :param destination: the destination folder path
        :param include_source: if True, the source packages
                               will be copied as well.
        :param include_locale: if True, the locales will be copied as well.
        :param include_mandatory: if True, all mandatory packages will be
                                  included
        :return: count of copied and total packages.
        """

        repos = self._load_repositories(repos_data)
        reqs = self._load_requirements(requirements_data)
        all_packages = self._get_packages(repos, reqs, include_mandatory)
        package_groups = defaultdict(set)
        for pkg in all_packages:
            package_groups[pkg.repository].add(pkg)

        stat = CopyStatistics()
        mirrors = defaultdict(set)
        # group packages by mirror
        for repo, packages in six.iteritems(package_groups):
            mirror = self.controller.fork_repository(
                repo, destination, include_source, include_locale
            )
            mirrors[mirror].update(packages)

        # add new packages to mirrors
        for mirror, packages in six.iteritems(mirrors):
            self.controller.assign_packages(
                mirror, packages, stat.on_package_copied
            )
        return stat

    def get_unresolved_dependencies(self, repos_data):
        """Gets list of unresolved dependencies for repository(es).

        :param repos_data: The list of repository descriptions
        :return: list of unresolved dependencies
        """
        packages = PackagesTree()
        self._load_packages(self._load_repositories(repos_data), packages.add)
        return packages.get_unresolved_dependencies()

    def _get_packages(self, repos, requirements, include_mandatory):
        if requirements is not None:
            forest = PackagesForest()
            for repo in repos:
                self.controller.load_packages(repo, forest.add_tree().add)
            return forest.get_packages(requirements, include_mandatory)

        packages = set()
        self._load_packages(repos, packages.add)
        return packages

    def _load_packages(self, repos, consumer):
        for repo in repos:
            self.controller.load_packages(repo, consumer)

    def _load_repositories(self, repos_data):
        for repo_data in repos_data:
            self._validate_repo_data(repo_data)
        return self.controller.load_repositories(repos_data)

    def _load_requirements(self, requirements_data):
        if requirements_data is None:
            return

        self._validate_requirements_data(requirements_data)
        result = []
        for r in requirements_data:
            versions = r.get('versions', None)
            if versions is None:
                result.append(PackageRelation.from_args((r['name'],)))
            else:
                for version in versions:
                    result.append(PackageRelation.from_args(
                        ([r['name']] + version.split(None, 1))
                    ))
        return result

    def _validate_repo_data(self, repo_data):
        schema = self.controller.get_repository_data_schema()
        self._validate_data(repo_data, schema)

    def _validate_requirements_data(self, requirements_data):
        self._validate_data(requirements_data, PACKAGES_SCHEMA)

    def _validate_package_files(self, package_files):
        self._validate_data(package_files, PACKAGE_FILES_SCHEMA)

    def _validate_data(self, data, schema):
        """Validate the input data using jsonschema validation.

        :param data: a data to validate represented as a dict
        :param schema: a schema to validate represented as a dict;
                       must be in JSON Schema Draft 4 format.
        """
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            self._raise_validation_error("data", e.message, e.absolute_path)
        except jsonschema.SchemaError as e:
            self._raise_validation_error(
                "schema", e.message, e.absolute_schema_path
            )

    @staticmethod
    def _raise_validation_error(what, details, path):
        message = "Invalid {0}: {1}.".format(what, details)
        if path:
            message += "\nField: [{0}]".format(
                "][".join(repr(p) for p in path)
            )
        raise ValueError(message)
