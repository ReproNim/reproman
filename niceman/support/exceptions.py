# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" niceman exceptions
"""


class CommandError(RuntimeError):
    """Thrown if a command call fails.
    """

    def __init__(self, cmd="", msg="", code=None, stdout="", stderr=""):
        RuntimeError.__init__(self, msg)
        self.cmd = cmd
        self.msg = msg
        self.code = code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        to_str = "%s: command '%s'" % (self.__class__.__name__, self.cmd)
        if self.code:
            to_str += " failed with exitcode %d" % self.code
        to_str += ".\n%s" % self.msg
        return to_str


class CommandNotAvailableError(CommandError):
    """Thrown if a command is not available due to certain circumstances.
    """
    pass


class InsufficientArgumentsError(ValueError):
    """To be raise instead of `ValueError` when use help output is desired"""
    pass


class SpecLoadingError(IOError):
    """To be raised when spec file fails to load"""
    pass


class MissingConfigError(RuntimeError):
    """To be raised when missing configuration a parameter"""
    pass


class MissingConfigFileError(RuntimeError):
    """To be raised when missing the configuration file"""
    pass


class MultipleReleaseFileMatch(RuntimeError):
    """Multiple release files were matched while retracing on Debian"""
    pass


class ResourceError(RuntimeError):
    """To be raised when there is a problem with a niceman resource"""
    pass


# Session errors
class SessionRuntimeError(RuntimeError):
    pass

#
# SSH support errors, largely adopted from starcluster
#

class SSHError(Exception):
    """Base class for all SSH related errors"""
    def __init__(self, *args):
        self.args = args
        self.msg = args[0]

    def __str__(self):
        return self.msg

    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)


class SSHConnectionError(SSHError):
    """Raised when ssh fails to to connect to a host (socket error)"""
    def __init__(self, host, port):
        self.msg = "failed to connect to host %s on port %s" % (host, port)


class SSHAuthException(SSHError):
    """Raised when an ssh connection fails to authenticate"""
    def __init__(self, user, host):
        self.msg = "failed to authenticate to host %s as user %s" % (host,
                                                                     user)


class SSHAccessDeniedViaAuthKeys(BaseException):
    """
    Raised when SSH access for a given user has been restricted via
    authorized_keys (common approach on UEC AMIs to allow root SSH access to be
    'toggled' via cloud-init)
    """
    def __init__(self, user):
        self.msg = "access for user '%s' denied via authorized_keys" % user
