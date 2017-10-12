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
from .base import Resource
from niceman.cmd import Runner

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

    def start(self):
        self._runner = Runner()

    def stop(self):
        self._runner = None

    #
    # Commands fulfilling a "Session" interface to interact with the environment
    #
    def _execute_command(self, command, env=None, cwd=None):
        """
        Execute the given command in the environment.

        Parameters
        ----------
        command : list
            Shell command string or list of command tokens to send to the
            environment to execute.
        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call

        Returns
        -------
        out, err
        """
        # XXX should it be a generic behavior to auto-start?
        if self._runner is None:
            self.start()
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
            'id': self.id
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
        if shared:
            raise NotImplementedError
        return PTYSession() if pty else ShellSession()


import termios
import struct
import fcntl
import time

class PTYHandler(object):
    """A helper for handling a PTY session.

    Eventually might acquire some special super-powers
    """

    def __init__(self):
        self.resized = False
        self.fd = None
        self._last_resize = None

    def __call__(self, fd):
        if not self.fd:
            self.fd = fd
            self.set_winsize()
        else:
            # paranoid Yarik does not know if fd could somehow miraculously
            # change
            if self.fd != fd:
                lgr.warning("fd was changed from %s to %s", self.fd, fd)
                self.fd = fd
            if not self._last_resize or time.time() - self._last_resize > 1:
                self.set_winsize()

        data = os.read(fd, 1024)
        # TODO: here we could potentially log
        # lgr.debug("is it fun???")
        return data

    def set_winsize(self, row=None, col=None, xpix=0, ypix=0):
        """A helper to set the terminal size to desired size
        """
        if row is None or col is None:
            # query the terminal
            # This is probably Linux specific, although seems to be there also
            # on OSX
            row, col = map(int, os.popen('stty size', 'r').read().split())
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
        self._last_resize = time.time()


class PTYSession(ShellSession):

    def open(self):

        lgr.debug("Opening local TTY connection.")
        # TODO: probably call to super to assure that we have it running?
        import pty
        # With /bin/sh  I am loosing proper ANSI characters rendering
        # etc.  With /bin/bash all good
        shell = "/bin/bash"  # TODO: should be a (config?) option!!!
        # the problem remains about size not matching the terminal size
        # so we will use the PTYHandler which would dynamically adjust it
        # (from tim to time)
        hdlr = PTYHandler()
        pty.spawn(shell, hdlr)

    def close(self):
        # XXX ?
        pass
