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

import copy
import os
import rpmUtils
import shutil
import tempfile

import createrepo
import lxml.etree as etree
import six

from packetary.drivers.base import RepositoryDriverBase
from packetary.library.checksum import composite as checksum_composite
from packetary.library.streams import GzipDecompress
from packetary.library import utils
from packetary.objects.base import ComparableObject
from packetary.objects import FileChecksum
from packetary.objects import Package
from packetary.objects import PackageRelation
from packetary.objects import Repository
from packetary.objects import VersionRange
from packetary.schemas import RPM_REPO_SCHEMA


urljoin = six.moves.urllib.parse.urljoin

# TODO(configurable option for drivers)
_CORE_GROUPS = ("core", "base")

_MANDATORY_TYPES = ("mandatory", "default")

# The namespaces are used in metadata xml of repository
_NAMESPACES = {
    "main": "http://linux.duke.edu/metadata/common",
    "md": "http://linux.duke.edu/metadata/repo",
    "rpm": "http://linux.duke.edu/metadata/rpm"
}

_checksum_collector = checksum_composite('md5', 'sha1', 'sha256')

_OPERATORS_MAPPING = {
    None: None,
    'GT': '>',
    'LT': '<',
    'EQ': '=',
    'GE': '>=',
    'LE': '<=',
}

_DEFAULT_PRIORITY = 99


class CreaterepoCallBack(object):
    """Callback object for createrepo"""

    def __init__(self, logger):
        self.logger = logger

    def errorlog(self, msg):
        """Error log output."""
        self.logger.error(msg)

    def log(self, msg):
        """Logs message."""
        self.logger.info(msg)

    def progress(self, item, current, total):
        """"Progress bar."""
        pass


class RpmPackageVersion(ComparableObject):
    """The Package version."""

    __slots__ = ["epoch", "version", "release"]

    def __init__(self, epoch, version, release=None):
        self.epoch = epoch
        self.version = version
        self.release = release or ''

    @classmethod
    def from_string(cls, text):
        """Constructs from string.

        :param text: the version in format '[{epoch-}]-{version}-{release}'
        """
        (epoch, version, release) = rpmUtils.miscutils.stringToVersion(text)
        return cls(epoch, version, release)

    def cmp(self, other):
        if not isinstance(other, RpmPackageVersion):
            other = RpmPackageVersion.from_string(str(other))
        # if some package doesn't have release then we are processing
        # some Require section, so let's assume foo-1.2 == foo-1.2-45
        # in order to build correct list of providers
        if self.release == '' or other.release == '':
            return rpmUtils.miscutils.compareEVR(
                (self.epoch, self.version, ''),
                (other.epoch, other.version, '')
            )
        # we have full evr, so let's compare them all
        return rpmUtils.miscutils.compareEVR(
            (self.epoch, self.version, self.release),
            (other.epoch, other.version, other.release)
        )

    def __eq__(self, other):
        if other is self:
            return True
        return self.cmp(other) == 0

    def __str__(self):
        if self.release:
            return "{0}:{1}-{2}".format(
                self.epoch,
                self.version,
                self.release,
            )
        else:
            return "{0}:{1}".format(
                self.epoch,
                self.version,
            )


class RpmRepositoryDriver(RepositoryDriverBase):
    def get_repository_data_schema(self):
        return RPM_REPO_SCHEMA

    def get_priority(self, repo_data):
        # RPM repository expects general values from 0 to 99. 0
        # to have the highest priority and 99 -- the lowest.
        priority = repo_data.get('priority')
        if priority is None:
            priority = _DEFAULT_PRIORITY
        return priority

    def get_repository(self, connection, repository_data, arch, consumer):
        consumer(Repository(
            name=repository_data['name'],
            url=utils.normalize_repository_url(repository_data["uri"]),
            architecture=arch,
            path=repository_data.get('path'),
            origin="",
            priority=self.get_priority(repository_data)
        ))

    def get_packages(self, connection, repository, consumer):
        baseurl = repository.url
        repomd = urljoin(baseurl, "repodata/repomd.xml")
        self.logger.debug("repomd: %s", repomd)

        repomd_tree = etree.parse(connection.open_stream(repomd))
        mandatory = self._get_mandatory_packages(
            self._load_db(
                connection, baseurl, repomd_tree, "group_gz", "group"
            )
        )
        primary_db = self._load_db(connection, baseurl, repomd_tree, "primary")
        if primary_db is None:
            raise ValueError("Malformed repository: {0}".format(repository))

        counter = 0
        for tag in primary_db.iterfind("./main:package", _NAMESPACES):
            try:
                name = tag.find("./main:name", _NAMESPACES).text
                consumer(Package(
                    repository=repository,
                    name=tag.find("./main:name", _NAMESPACES).text,
                    version=self._unparse_version_attrs(
                        tag.find("./main:version", _NAMESPACES).attrib
                    ),
                    filesize=int(
                        tag.find("./main:size", _NAMESPACES)
                        .attrib.get("package", -1)
                    ),
                    filename=tag.find(
                        "./main:location", _NAMESPACES
                    ).attrib["href"],
                    checksum=self._get_checksum(tag),
                    mandatory='>=' if name in mandatory else None,
                    requires=self._get_relations(tag, "requires"),
                    obsoletes=self._get_relations(tag, "obsoletes"),
                    provides=self._get_provides_from_xml(tag),
                    group=tag.find("./main:format/rpm:group",
                                   _NAMESPACES).text,
                ))
            except (ValueError, KeyError) as e:
                self.logger.error(
                    "Malformed tag %s - %s: %s",
                    repository, etree.tostring(tag), six.text_type(e)
                )
                raise
            counter += 1
        self.logger.info("loaded: %d packages from %s.", counter, repository)

    def add_packages(self, connection, repository, packages):
        groupstree = self._load_groups(connection, repository)
        self._rebuild_repository(connection, repository, packages, groupstree)

    def fork_repository(self, connection, repository, destination, options):
        # TODO(download gpk)
        # TODO(sources and locales)
        new_repo = copy.copy(repository)
        new_repo.url = utils.normalize_repository_url(destination)
        utils.ensure_dir_exist(destination)
        groupstree = self._load_groups(connection, repository)
        self._rebuild_repository(connection, new_repo, set(), groupstree)
        return new_repo

    def create_repository(self, connection, repository_data, arch):
        repository = Repository(
            name=repository_data['name'],
            url=utils.normalize_repository_url(repository_data["uri"]),
            architecture=arch,
            path=repository_data.get('path'),
            origin=repository_data.get('origin'),
            priority=self.get_priority(repository_data)
        )
        utils.ensure_dir_exist(utils.get_path_from_url(repository.url))
        self._rebuild_repository(connection, repository, None, None)
        return repository

    def load_package_from_file(self, repository, filepath):
        fullpath = utils.get_path_from_url(repository.url + filepath)
        _, size, checksum = next(iter(utils.get_size_and_checksum_for_files(
            [fullpath], _checksum_collector)
        ))
        pkg = createrepo.yumbased.YumLocalPackage(filename=fullpath)
        hdr = pkg.returnLocalHeader()
        return Package(
            repository=repository,
            name=hdr["name"],
            version=RpmPackageVersion(
                hdr['epoch'], hdr['version'], hdr['release']
            ),
            filesize=int(hdr['size']),
            filename=filepath,
            checksum=FileChecksum(*checksum),
            mandatory=None,
            requires=self._parse_package_relations(pkg.requires),
            obsoletes=self._parse_package_relations(pkg.obsoletes),
            provides=self._get_provides_from_rpm(pkg),
            group=hdr["group"],
        )

    def get_relative_path(self, repository, filename):
        return "packages/" + filename

    def _rebuild_repository(self, conn, repo, packages, groupstree=None):
        basepath = utils.get_path_from_url(repo.url)
        self.logger.info("rebuild repository in %s", basepath)
        md_config = createrepo.MetaDataConfig()
        mdfile_path = os.path.join(
            basepath, md_config.finaldir, md_config.repomdfile
        )
        update = packages is not None and os.path.exists(mdfile_path)
        groupsfile = None
        if groupstree is None and update:
            # The createrepo lose the groups information on update
            # to prevent this set group info manually
            groupstree = self._load_groups(conn, repo)

        if groupstree is not None:
            groupsfile = os.path.join(tempfile.gettempdir(), "groups.xml")
            with open(groupsfile, "w") as fd:
                groupstree.write(fd)
        try:
            md_config.workers = 1
            md_config.directory = str(basepath)
            md_config.groupfile = groupsfile
            md_config.update = update
            if not packages:
                # only generate meta-files, without packages info
                md_config.excludes = ["*"]

            mdgen = createrepo.MetaDataGenerator(
                config_obj=md_config, callback=CreaterepoCallBack(self.logger)
            )
            mdgen.doPkgMetadata()
            mdgen.doRepoMetadata()
            mdgen.doFinalMove()
        except createrepo.MDError as e:
            err_msg = six.text_type(e)
            self.logger.exception(
                "failed to create yum repository in %s: %s",
                basepath,
                err_msg
            )
            shutil.rmtree(
                os.path.join(md_config.outputdir, md_config.tempdir),
                ignore_errors=True
            )
            raise RuntimeError(
                "Failed to create yum repository in {0}."
                .format(err_msg))
        finally:
            if groupsfile is not None:
                os.unlink(groupsfile)

    def _load_groups(self, connection, repository):
        repomd = urljoin(repository.url, "repodata/repomd.xml")
        self.logger.debug("load repomd: %s", repomd)
        repomd_tree = etree.parse(connection.open_stream(repomd))
        return self._load_db(
            connection, repository.url, repomd_tree, "group_gz", "group"
        )

    def _load_db(self, connection, baseurl, repomd, *aliases):
        """Loads database.

        :param connection: the connection object
        :param baseurl: the base repository URL
        :param repomd: the parsed metadata of repository
        :param aliases: the aliases of database name
        :return: parsed database file or None if db does not exist
        """

        for dbname in aliases:
            self.logger.debug("loading %s database...", dbname)
            node = repomd.find(
                "./md:data[@type='{0}']".format(dbname), _NAMESPACES
            )
            if node is not None:
                break
        else:
            return

        url = urljoin(
            baseurl,
            node.find("./md:location", _NAMESPACES).attrib["href"]
        )
        self.logger.debug("loading %s - %s...", dbname, url)
        stream = connection.open_stream(url)
        if url.endswith(".gz"):
            stream = GzipDecompress(stream)
        return etree.parse(stream)

    def _get_mandatory_packages(self, groups_db):
        """Get the set of mandatory package names.

        :param groups_db: the parsed groups database
        """
        package_names = set()
        if groups_db is None:
            return package_names
        count = 0
        for name in _CORE_GROUPS:
            result = groups_db.xpath("./group/id[text()='{0}']".format(name))
            if len(result) == 0:
                self.logger.warning("the group '%s' is not found.", name)
                continue
            group = result[0].getparent()
            for t in _MANDATORY_TYPES:
                xpath = "./packagelist/packagereq[@type='{0}']".format(t)
                for tag in group.iterfind(xpath):
                    package_names.add(tag.text)
                    count += 1
        self.logger.info("detected %d mandatory packages.", count)
        return package_names

    def _get_provides_from_xml(self, pkg_tag):
        """Gets the package provides from package tag.

        Tag provides contains virtual packages.
        Tag files contains binary files that is provided by package.

        :param pkg_tag: the xml-tag with package description
        :return: list of PackageRelation objects
        """
        provides = self._get_relations(pkg_tag, "provides")
        files_iter = pkg_tag.iterfind("./main:format/main:file", _NAMESPACES)
        append = provides.append
        for file_tag in files_iter:
            append(PackageRelation(file_tag.text))
        return provides

    def _get_provides_from_rpm(self, pkg):
        """Gets the package provides from YumPackage.

        :param pkg: the YumPackage Instance
        :return: list of PackageRelation objects
        """
        provides = self._parse_package_relations(pkg.provides)
        append = provides.append
        for filename in pkg.returnFileEntries('file', True):
            append(PackageRelation(filename))
        return provides

    def _get_relations(self, pkg_tag, name):
        """Gets package relations by name from package tag.

        :param pkg_tag: the xml-tag with package description
        :param name: the relations name
        :return: list of PackageRelation objects
        """
        relations = list()
        append = relations.append
        tags_iter = pkg_tag.iterfind(
            "./main:format/rpm:%s/rpm:entry" % name,
            _NAMESPACES
        )
        for elem in tags_iter:
            append(PackageRelation.from_args(
                self._unparse_relation_attrs(elem.attrib)
            ))

        return relations

    @staticmethod
    def _parse_package_relations(relations):
        """Parses yum package relations.

        :param relations: list of tuples
                          (name, flags, (epoch, version, release))
        :return: list of PackageRelation objects
        """
        return [
            PackageRelation(
                x[0], VersionRange(
                    _OPERATORS_MAPPING[x[1]], x[1] and RpmPackageVersion(*x[2])
                )
            )
            for x in relations
        ]

    def _get_checksum(self, pkg_tag):
        """Gets checksum from package tag."""
        checksum = dict.fromkeys(("md5", "sha1", "sha256"), None)
        checksum_tag = pkg_tag.find("./main:checksum", _NAMESPACES)
        checksum[checksum_tag.attrib["type"]] = checksum_tag.text
        return FileChecksum(**checksum)

    def _unparse_relation_attrs(self, attrs):
        """Gets the package relation from attributes.

        :param attrs: the relation tag attributes
        :return tuple(name, version_op, version_edge)
        """

        name = attrs['name']
        if "flags" not in attrs:
            return name, None

        return (
            name,
            _OPERATORS_MAPPING[attrs["flags"]],
            self._unparse_version_attrs(attrs)
        )

    @staticmethod
    def _unparse_version_attrs(attrs):
        """Gets the package version from attributes.

        :param attrs: the relation tag attributes
        :return: the RpmPackageVersion object
        """

        return RpmPackageVersion(
            attrs.get("epoch", "0"),
            attrs.get("ver", "0.0"),
            attrs.get("rel")
        )
