# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Resource sub-class to provide management of the localhost environment."""

import attr
import shutil

from .base import Resource
from niceman.cmd import Runner
from niceman.dochelpers import borrowdoc
from niceman.resource.session import Session
from niceman.support.exceptions import CommandError

import logging
lgr = logging.getLogger('niceman.resource.shell')

import os

from .session import POSIXSession, get_updated_env


# For now just assuming that local shell is a POSIX shell
# Later we could specialize based on the OS, and that is why
# Resource/Shell is not subclassing Session but rather delegates to .session
class ShellSession(POSIXSession):
    """Local shell session"""

    def __init__(self):
        super(ShellSession, self).__init__()
        self._runner = None

    @borrowdoc(Session)
    def open(self):
        self._runner = Runner()

    @borrowdoc(Session)
    def close(self):
        self._runner = None

    @borrowdoc(Session)
    def _execute_command(self, command, env=None, cwd=None):
        # XXX should it be a generic behavior to auto-start?
        if self._runner is None:
            self.open()
        run_kw = {}
        if env:
            # if anything custom, then we need to get original full environment
            # and update it with custom settings which we either "accumulated"
            # via set_envvar, or it was passed into this call.
            run_kw['env'] = get_updated_env(os.environ, env)

        return self._runner.run(
            command,
            # For now we do not ERROR out whenever command fails or provides
            # stderr -- analysis will be done outside
            expect_fail=True,
            expect_stderr=True,
            cwd=cwd,
            **run_kw
        )  # , shell=True)

    @borrowdoc(Session)
    def isdir(self, path):
        return os.path.isdir(path)

    @borrowdoc(Session)
    def mkdir(self, path, parents=False):
        if not os.path.exists(path):
            if parents:
                os.makedirs(path)
            else:
                try:
                    os.mkdir(path)
                except OSError:
                    raise CommandError(
                        msg="Failed to make directory {}".format(path))

    @borrowdoc(Session)
    def get(self, src_path, dest_path, uid=-1, gid=-1):
        dest_dir, dest_basename = os.path.split(dest_path)
        if not self.exists(dest_dir):
            self.mkdir(dest_dir, parents=True)
        shutil.copy(src_path, dest_path)
        if uid > -1 or gid > -1:
            self.chown(dest_path, uid, gid, recursive=True)

    @borrowdoc(Session)
    def put(self, src_path, dest_path, uid=-1, gid=-1):
        # put is the same as get for the shell resource
        self.get(src_path, dest_path, uid, gid)


    def put(self, src_path, dest_path, preserve_perms=False,
            owner=None, group=None, recursive=False):
        """Take file on the local file system and copy over into the session
        """
        # TODO: Add unit tests!
        if recursive:
            raise NotImplementedError
        shutil.copy(src_path, dest_path)
        if preserve_perms:
            shutil.copystat(src_path, dest_path)
        if owner or group:
            shutil.chown(dest_path, owner, group)


@attr.s
class Shell(Resource):

    # Container properties
    name = attr.ib()
    id = attr.ib(default=None)
    type = attr.ib(default='shell')

    status = attr.ib(default=None)

    def create(self):
        """
        Create a running environment.

        Parameters
        ----------
        name : string
            Name identifier of the environment to be created.
        """
        # Generic logic to reside in Resource???
        if self.id is None:
            self.id = Resource._generate_id()
        return {
            'id': self.id,
            'status': 'N/A'
        }

    def connect(self):
        """
        Connect to an existing environment.
        """
        return self

    def delete(self):
        """
        Remove this environment from the backend.
        """
        return

    def start(self):
        """
        Start this environment in the backend.
        """
        return self

    def stop(self):
        """
        Stop this environment in the backend.
        """
        return

    def get_session(self, pty=False, shared=None):
        """
        Log into a container and get the command line
        """
        if pty:
            raise NotImplementedError
        if shared:
            raise NotImplementedError
        return ShellSession()