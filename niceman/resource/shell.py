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


# For now just assuming that local shell is a POSIX shell
# Later we could specialize based on the OS, and that is why
# Resource/Shell is not subclassing Session but rather delegates to .session
class ShellSession(POSIXSession):
    """Local shell session"""

    def __init__(self):
        super(ShellSession, self).__init__()
        self._runner = None

    def open(self):
        super(ShellSession, self).open()
        self._runner = Runner()

    def close(self):
        self._runner = None
        super(ShellSession, self).close()

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


import termios
import struct
import fcntl
import time
from contextlib import contextmanager
import signal

# TODO: make it work with dockerpty'like proper handling of resizing
# try:
#     from dockerpty.tty import size
# except:
def size(fd):
    return map(int, os.popen('stty size', 'r').read().split())

# # borrowed from dockerpty.tty, modified to accept fd as int, not a file descriptor
# def size(fd):
#     """
#     Return a tuple (rows,cols) representing the size of the TTY `fd`.
#
#     The provided file descriptor should be the stdout stream of the TTY.
#
#     If the TTY size cannot be determined, returns None.
#     """
#
#     if not os.isatty(fd):
#         return None
#
#     try:
#         dims = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, 'hhhh'))
#     except:
#         try:
#             dims = (os.environ['LINES'], os.environ['COLUMNS'])
#         except:
#             return None
#
#     return dims


class PTYHandler(object):
    """A helper for handling a PTY session.

    Eventually might acquire some special super-powers
    """

    def __init__(self):
        self.resized = False
        self.fd = None
        self._last_resize = None
        self._dims = 0, 0

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

    @contextmanager
    def WINCHHandler(self):
        """Handler for the SIGWINCH signal.

        Unfortunately not yet working"""
        def handle(signum, frame):
            if signum == signal.SIGWINCH:
                self.set_winsize()
        original = signal.signal(signal.SIGWINCH, handle)
        yield self
        if original is not None:
            signal.signal(signal.SIGWINCH, original)

    def set_winsize(self, row=None, col=None, xpix=0, ypix=0):
        """A helper to set the terminal size to desired size
        """
        if row is None or col is None:
            # query the terminal
            # This is probably Linux specific, although seems to be there also
            # on OSX
            # TODO: avoid calling out to external tool:
            #  (re)use dockerpty since they do have proper handling of the SIGWINCH
            #  signal etc
            dims = size(self.fd)
            if not dims or dims == self._dims:
                return
            self._dims = row, col = dims
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
        self._last_resize = time.time()


class PTYSession(ShellSession):
    """Interactive PTY session for the local shell"""

    # TODO: how could we also execute_command in the same session!?
    # because we do not run it in the background, and because of all the env
    # vars etc, not sure how that is possible.  But we will need to "prime"
    # it with our starting script at least.
    #
    # Besides open/close -- we would need to support multiple stages I guess
    # so we could deploy our needed pieces first in there, then instruct
    # shell to source before actually providing an interactive shell
    def open(self):
        # call ShellSession's parent, not ShellSession... dirty for now
        super(ShellSession, self).open()
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
        # for some reason leads to  (4, 'Interrupted system call') atm
        #with hdlr.WINCHHandler():
        pty.spawn(shell, hdlr)
