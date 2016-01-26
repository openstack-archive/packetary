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


from packetary.cli.commands.base import BaseRepoCommand


class CreateCommand(BaseRepoCommand):
    """Creates the new repository."""

    def get_parser(self, prog_name):
        parser = super(CreateCommand, self).get_parser(prog_name)
        # add command line arguments

    def take_repo_action(self, api, parsed_args):
        stat = api.create_repository(
            parsed_args.repository,
            parsed_args.files
        )
        self.stdout.write("Successfully completed.")


def debug(argv=None):
    """Helper to debug the Clone command."""
    from packetary.cli.app import debug
    debug("clone", CreateCommand, argv)


if __name__ == "__main__":
    debug()
