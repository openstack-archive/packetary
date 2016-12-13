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

import six

from packetary import objects
from packetary import schemas

from packetary.api.context import Context
from packetary.api.options import RepositoryCopyOptions
from packetary.controllers import RepositoryController
from packetary.library.functions import compose
from packetary.objects.package_relation import PackageRelation

from packetary.api.loaders import get_packages_traverse
from packetary.api.loaders import load_package_relations
from packetary.api.statistics import CopyStatistics
from packetary.api.validators import declare_schema


logger = logging.getLogger(__package__)


_MANDATORY = {
    "exact": "=",
    "newest": ">=",
}


class RepositoryApi(object):
    """Provides high-level API to operate with repositories."""

    CopyOptions = RepositoryCopyOptions

    def __init__(self, controller):
        """Initialises.

        :param controller: the repository controller.
        """
        self.controller = controller

    def _get_repository_data_schema(self):
        return self.controller.get_repository_data_schema()

    def _get_repositories_data_schema(self):
        return {
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'array',
            'items': self._get_repository_data_schema()
        }

    @classmethod
    def create(cls, config, repotype, repoarch):
        """Creates the repository API instance.

        :param config: the configuration
        :param repotype: the kind of repository(deb, yum, etc)
        :param repoarch: the architecture of repository
                         (x86_64, i386 or aarch64)
        """
        context = config if isinstance(config, Context) else Context(config)
        return cls(RepositoryController.load(context, repotype, repoarch))

    @declare_schema(repo_data=_get_repository_data_schema,
                    package_files=schemas.PACKAGE_FILES_SCHEMA)
    def create_repository(self, repo_data, package_files):
        """Create new repository with specified packages.

        :param repo_data: The description of repository
        :param package_files: The list of URLs of packages
        """
        return self.controller.create_repository(repo_data, package_files)

    @declare_schema(repos_data=_get_repositories_data_schema,
                    requirements_data=schemas.REQUIREMENTS_SCHEMA)
    def get_packages(self, repos_data, requirements_data=None):
        """Gets the list of packages from repository(es).

        :param repos_data: The list of repository descriptions
        :param requirements_data: The list of package`s requirements
                                  that should be included
        :return: the set of packages
        """
        repositories = self.controller.load_repositories(repos_data)
        return self._get_packages(repositories, requirements_data)

    @declare_schema(repos_data=_get_repositories_data_schema,
                    requirements_data=schemas.REQUIREMENTS_SCHEMA)
    def clone_repositories(self, repos_data, destination,
                           requirements_data=None, options=None):
        """Creates the clones of specified repositories in local folder.

        :param repos_data: The list of repository descriptions
        :param requirements_data: The list of package`s requirements
                                  that should be included
        :param destination: the destination folder path
        :param options: the repository copy options
        :return: count of copied and total packages.
        """

        repositories = self.controller.load_repositories(repos_data)
        all_packages = self._get_packages(repositories, requirements_data)
        # create a empty package group even repo is empty
        package_groups = {repo: set() for repo in repositories}
        for pkg in all_packages:
            package_groups[pkg.repository].add(pkg)

        stat = CopyStatistics()
        mirrors = defaultdict(set)
        options = options or self.CopyOptions()
        # group packages by mirror
        for repo, packages in six.iteritems(package_groups):
            m = self.controller.fork_repository(repo, destination, options)
            mirrors[m].update(packages)

        # add new packages to mirrors
        for m, pkgs in six.iteritems(mirrors):
            self.controller.assign_packages(m, pkgs, stat.on_package_copied)
        return stat

    @declare_schema(repos_data=_get_repositories_data_schema)
    def get_unresolved_dependencies(self, repos_data):
        """Gets list of unresolved dependencies for repository(es).

        :param repos_data: The list of repository descriptions
        :return: list of unresolved dependencies
        """
        packages = objects.PackagesTree()
        repositories = self.controller.load_repositories(repos_data)
        self._load_packages(repositories, packages.add)
        return packages.get_unresolved_dependencies()

    def _get_packages(self, repositories, requirements):
        if requirements:
            forest = objects.PackagesForest()
            package_relations = []
            load_package_relations(
                requirements.get('packages'), package_relations.append
            )
            packages_traverse = get_packages_traverse(
                requirements.get('repositories'), package_relations.append
            )
            for repo in repositories:
                tree = forest.add_tree(repo.priority)
                self.controller.load_packages(
                    repo,
                    compose(
                        tree.add,
                        packages_traverse
                    )
                )
                mandatory = requirements.get('mandatory')
                if mandatory:
                    for package in tree.mandatory_packages:
                        package_relations.append(
                            PackageRelation.from_args(
                                (package.name,
                                 _MANDATORY[requirements['mandatory']],
                                 package.version)))

            return forest.get_packages(package_relations)

        packages = set()
        self._load_packages(repositories, packages.add)
        return packages

    def _load_packages(self, repos, consumer):
        for repo in repos:
            self.controller.load_packages(repo, consumer)
