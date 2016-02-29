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

import os

from cliff import command

from packetary.cli.commands.utils import read_from_file
from packetary import RepositoryApi


class SerialCloneCommand(command.Command):
    """Runs several clone actions one by one."""

    def get_parser(self, prog_name):
        parser = super(SerialCloneCommand, self).get_parser(prog_name)
        parser.add_argument(
            '-f', '--file',
            dest='clone_data',
            type=read_from_file,
            required=True,
            metavar='FILENAME',
            help="The path to the yaml file."
        )
        parser.add_argument(
            "-d", "--destination",
            default=os.getcwd(),
            dest='base_destination',
            help="The path to the base destination folder."
        )
        return parser

    def take_action(self, parsed_args):
        """Runs clone subcommand several times.

        :param parsed_args: command-line arguments
        """
        for action in parsed_args.clone_data:
            if action.get('action') != 'clone':
                continue
            api = RepositoryApi.create(
                self.app_args, action.get('type', 'deb'),
                action.get('arch', 'x86_64')
            )
            if action.get('packages') is not None and \
                    action.get('filters') is not None:
                raise ValueError(
                    "Packages and filters can not be used at the same time"
                )
            stat = api.clone_repositories(
                action['repos'],
                action.get('packages'),
                os.path.abspath(
                    os.path.join(parsed_args.base_destination,
                                 action.get('destination', ''))),
                action.get('sources', False),
                action.get('locales', False),
                action.get('include_mandatory', True),
                filter_data=action.get('filters'),
            )
            self.app.stdout.write(
                "Packages copied: {0.copied}/{0.total}.\n".format(stat)
            )


def debug(argv=None):
    """Helper to debug the Clone command."""
    from packetary.cli.app import debug
    debug("serial-clone", SerialCloneCommand, argv)


if __name__ == "__main__":
    debug()
