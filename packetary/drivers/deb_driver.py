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

from contextlib import closing
import copy
import datetime
import fcntl
import gzip
import os

from debian import deb822
from debian import debfile
from debian.debian_support import Version
import six

from packetary.drivers.base import RepositoryDriverBase
from packetary.library.checksum import composite as checksum_composite
from packetary.library.streams import GzipDecompress
from packetary.library import utils
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.schemas import DEB_REPO_SCHEMA


_OPERATORS_MAPPING = {
    '>>': '>',
    '<<': '<',
    '=': '=',
    '>=': '>=',
    '<=': '<=',
}

_ARCHITECTURES = {
    "x86_64": "amd64",
    "i386": "i386",
    "source": "Source",
    "amd64": "x86_64",
}

_PRIORITIES = {
    "required": 1,
    "important": 2,
    "standard": 3,
    "optional": 4,
    "extra": 5
}

# Order is important
_REPOSITORY_FILES = [
    "Packages",
    "Release",
    "Packages.gz"
]

# TODO(should be configurable)
_MANDATORY_PRIORITY = 3

_CHECKSUM_METHODS = (
    "MD5Sum",
    "SHA1",
    "SHA256"
)

_DEFAULT_PRIORITY = 500

_checksum_collector = checksum_composite('md5', 'sha1', 'sha256')


class DebRepositoryDriver(RepositoryDriverBase):
    def get_repository_data_schema(self):
        return DEB_REPO_SCHEMA

    def priority_sort(self, repo_data):
        # DEB repository expects general values from 0 to 1000. 0
        # to have lowest priority and 1000 -- the highest. Note that a
        # priority above 1000 will allow even downgrades no matter the version
        # of the prioritary package
        priority = repo_data.get('priority')
        if priority is None:
            priority = _DEFAULT_PRIORITY
        return -priority

    def get_repository(self, connection, repository_data, arch, consumer):
        url = utils.normalize_repository_url(repository_data['uri'])
        suite = repository_data['suite']
        components = repository_data.get('section')
        path = repository_data.get('path')
        name = repository_data.get('name')

        # TODO(bgaifullin) implement support for flat repisotory format [1]
        # [1] https://wiki.debian.org/RepositoryFormat#Flat_Repository_Format
        if components is None:
            raise ValueError("The flat format does not supported.")

        for component in components:
            release = self._get_url_of_metafile(
                (url, suite, component, arch), "Release"
            )
            try:
                deb_release = deb822.Release(connection.open_stream(release))
            except connection.HTTPError as e:
                if e.code != 404:
                    raise
                # some repositories does not contain release file
                deb_release = {"origin": ""}

            consumer(Repository(
                name=name,
                architecture=arch,
                origin=deb_release["origin"],
                url=url,
                section=(suite, component),
                path=path
            ))

    def get_packages(self, connection, repository, consumer):
        index = self._get_url_of_metafile(repository, "Packages.gz")
        stream = GzipDecompress(connection.open_stream(index))
        self.logger.info("loading packages from %s ...", repository)
        pkg_iter = deb822.Packages.iter_paragraphs(stream)
        counter = 0
        for dpkg in pkg_iter:
            try:
                consumer(Package(
                    repository=repository,
                    name=dpkg["package"],
                    version=Version(dpkg['version']),
                    filesize=int(dpkg.get('size', -1)),
                    filename=dpkg["filename"],
                    checksum=FileChecksum(
                        md5=dpkg.get("md5sum"),
                        sha1=dpkg.get("sha1"),
                        sha256=dpkg.get("sha256"),
                    ),
                    mandatory=self._is_mandatory(dpkg),
                    # Recommends are installed by default (since Lucid)
                    requires=self._get_relations(
                        dpkg, "depends", "pre-depends", "recommends"
                    ),
                    # The deb does not have obsoletes section
                    obsoletes=[],
                    provides=self._get_relations(dpkg, "provides"),
                ))
            except KeyError as e:
                self.logger.error(
                    "Malformed index %s - %s: %s",
                    repository, six.text_type(dpkg), six.text_type(e)
                )
                raise
            counter += 1

        self.logger.info("loaded: %d packages from %s.", counter, repository)

    def add_packages(self, connection, repository, packages):
        basedir = utils.get_path_from_url(repository.url)
        index_file = utils.get_path_from_url(
            self._get_url_of_metafile(repository, "Packages")
        )
        utils.ensure_dir_exist(os.path.dirname(index_file))
        index_gz = index_file + ".gz"
        count = 0
        # load existing packages
        self.get_packages(connection, repository, packages.add)
        with open(index_file, "wb") as fd1:
            with closing(gzip.open(index_gz, "wb")) as fd2:
                writer = utils.composite_writer(fd1, fd2)
                for pkg in packages:
                    filename = os.path.join(basedir, pkg.filename)
                    with closing(debfile.DebFile(filename)) as deb:
                        debcontrol = deb.debcontrol()
                    debcontrol.setdefault("Origin", repository.origin)
                    debcontrol["Size"] = str(pkg.filesize)
                    debcontrol["Filename"] = pkg.filename
                    for k, v in six.moves.zip(_CHECKSUM_METHODS, pkg.checksum):
                        debcontrol[k] = v
                    writer(debcontrol.dump())
                    writer("\n")
                    count += 1
        self.logger.info("saved %d packages in %s", count, repository)
        self._update_suite_index(repository)

    def fork_repository(self, connection, repository, destination,
                        source=False, locale=False):
        # TODO(download gpk)
        # TODO(sources and locales)
        new_repo = copy.copy(repository)
        new_repo.url = utils.normalize_repository_url(destination)
        self._create_repository_structure(new_repo)
        return new_repo

    def create_repository(self, repository_data, arch):
        url = utils.normalize_repository_url(repository_data['uri'])
        suite = repository_data['suite']
        component = repository_data.get('section')
        path = repository_data.get('path')
        name = repository_data.get('name')
        origin = repository_data.get('origin')

        if component is None:
            raise ValueError("The flat format does not supported.")
        if isinstance(component, list):
            if len(component) != 1:
                raise ValueError("The only single component is acceptable.")
            component = component[0]

        repository = Repository(
            name=name,
            url=url,
            architecture=arch,
            origin=origin,
            section=(suite, component),
            path=path
        )
        self._create_repository_structure(repository)
        self.logger.info("Created: %d repository.", repository.name)
        return repository

    def load_package_from_file(self, repository, filename):
        filepath = utils.get_path_from_url(repository.url + filename)
        _, size, checksum = next(iter(utils.get_size_and_checksum_for_files(
            [filepath], _checksum_collector)
        ))
        with closing(debfile.DebFile(filepath)) as deb:
            debcontrol = deb822.Packages(
                deb.control.get_content(debfile.CONTROL_FILE)
            )

        return Package(
            repository=repository,
            name=debcontrol["package"],
            version=Version(debcontrol['version']),
            filesize=int(debcontrol.get('size', size)),
            filename=filename,
            checksum=FileChecksum(*checksum),
            mandatory=self._is_mandatory(debcontrol),
            requires=self._get_relations(
                debcontrol, "depends", "pre-depends",
                "recommends"
            ),
            provides=self._get_relations(debcontrol, "provides"),
            obsoletes=[]
        )

    def get_relative_path(self, repository, filename):
        return "/".join(("pool", repository.section[1], filename[0], filename))

    def _create_repository_structure(self, repository):
        packages_file = utils.get_path_from_url(
            self._get_url_of_metafile(repository, "Packages")
        )
        release_file = utils.get_path_from_url(
            self._get_url_of_metafile(repository, "Release")
        )
        utils.ensure_dir_exist(os.path.dirname(release_file))

        release = deb822.Release()
        release["Origin"] = repository.origin
        release["Label"] = repository.origin
        release["Archive"] = repository.section[0]
        release["Component"] = repository.section[1]
        release["Architecture"] = _ARCHITECTURES[repository.architecture]
        with open(release_file, "wb") as fd:
            release.dump(fd)

        open(packages_file, "ab").close()
        gzip.open(packages_file + ".gz", "ab").close()

    def _update_suite_index(self, repository):
        """Updates the Release file in the suite."""
        path = os.path.join(
            utils.get_path_from_url(repository.url),
            "dists", repository.section[0]
        )
        release_path = os.path.join(path, "Release")
        self.logger.info(
            "added repository suite release file: %s", release_path
        )
        with open(release_path, "a+b") as fd:
            fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
            try:
                fd.seek(0)
                release = deb822.Release(fd)
                self._add_to_release(release, repository)
                for m in _CHECKSUM_METHODS:
                    release.setdefault(m, [])

                self._add_files_to_release(
                    release, path, self._get_metafiles(repository)
                )

                fd.truncate(0)
                release.dump(fd)
            finally:
                fcntl.flock(fd.fileno(), fcntl.LOCK_UN)

    def _get_relations(self, dpkg, *names):
        """Gets the package relations.

        :param dpkg: the debian-package object
        :type dpkg: deb822.Packages
        :param names: the relation names
        :return: the list of PackageRelation objects
        """
        relations = list()
        for name in names:
            for variants in dpkg.relations[name]:
                relation = PackageRelation.from_args(
                    *(self._unparse_relation(v) for v in variants)
                )
                if relation is not None:
                    relations.append(relation)
        return relations

    def _get_metafiles(self, repository):
        """Gets the sequence of metafiles for repository."""
        return (
            utils.get_path_from_url(
                self._get_url_of_metafile(repository, filename)
            )
            for filename in _REPOSITORY_FILES

        )

    @staticmethod
    def _unparse_relation(relation):
        """Gets the relation parameters.

        :param relation: the deb822.Releation object
        :return: tuple(name, version_compare, version_edge)
        """
        name = relation['name']
        version = relation.get("version")
        if version is None:
            return name, None
        else:
            return name, _OPERATORS_MAPPING[version[0]], version[1]

    @staticmethod
    def _is_mandatory(dpkg):
        """Checks that package is mandatory.

        :param dpkg: the debian-package object
        :type dpkg: deb822.Packages
        """
        if dpkg.get("essential") == "yes":
            return True

        return _PRIORITIES.get(
            dpkg.get("priority"), _MANDATORY_PRIORITY + 1
        ) < _MANDATORY_PRIORITY

    @staticmethod
    def _get_url_of_metafile(repo_or_comps, filename):
        """Gets the URL of meta-file.

        :param repo_or_comps: the repository object or
                              tuple(baseurl, suite, component, architecture)
        :param filename: the name of meta-file
        """
        if isinstance(repo_or_comps, Repository):
            baseurl = repo_or_comps.url
            suite, component = repo_or_comps.section
            arch = repo_or_comps.architecture
        else:
            baseurl, suite, component, arch = repo_or_comps

        return "/".join((
            baseurl.rstrip("/"), "dists", suite, component,
            "binary-" + _ARCHITECTURES[arch],
            filename
        ))

    @staticmethod
    def _add_to_release(release, repository):
        """Adds repository information to debian release.

        :param release: the deb822.Release instance
        :param repository: the repository object
        """

        # reset the date
        release["Date"] = datetime.datetime.now().strftime(
            "%a, %d %b %Y %H:%M:%S %Z"
        )
        release.setdefault("Origin", repository.origin)
        release.setdefault("Label", repository.origin)
        release.setdefault("Suite", repository.section[0])
        release.setdefault("Codename", repository.section[0].split("-", 1)[0])
        release.setdefault("Description", "The packages repository.")

        keys = ("Architectures", "Components")
        values = (repository.architecture, repository.section[1])
        for key, value in six.moves.zip(keys, values):
            if key in release:
                release[key] = utils.append_token_to_string(
                    release[key],
                    value
                )
            else:
                release[key] = value

    @staticmethod
    def _add_files_to_release(release, basepath, files):
        """Adds information about meta files to debian release.

        :param release: the deb822.Release instance
        :param basepath: the suite folder path
        :param files: the sequence of files
        """

        files_info = utils.get_size_and_checksum_for_files(
            files, _checksum_collector
        )
        for filepath, size, cs in files_info:
            fname = filepath[len(basepath) + 1:]
            size = six.text_type(size)
            for m, checksum in six.moves.zip(_CHECKSUM_METHODS, cs):
                for v in release[m]:
                    if v["name"] == fname:
                        v[m] = checksum
                        v["size"] = size
                        break
                else:
                    release[m].append(deb822.Deb822Dict({
                        m: checksum,
                        "size": size,
                        "name": fname
                    }))
