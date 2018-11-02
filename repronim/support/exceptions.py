# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
""" repronim exceptions
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
        to_str = "%s: " % self.__class__.__name__
        if self.cmd:
            to_str += "command '%s'" % (self.cmd,)
        if self.code:
            to_str += " failed with exitcode %d" % self.code
        to_str += "\n%s" % self.msg
        return to_str


class MissingExternalDependency(RuntimeError):
    """External dependency is missing error"""

    def __init__(self, name, ver=None, msg=""):
        super(MissingExternalDependency, self).__init__()
        self.name = name
        self.ver = ver
        self.msg = msg

    def __str__(self):
        to_str = str(self.name)
        if self.ver:
            to_str += " of version >= %s" % self.ver
        to_str += " is missing."
        if self.msg:
            to_str += " %s" % self.msg
        return to_str


class DeprecatedError(RuntimeError):
    """To raise whenever a deprecated entirely feature is used"""
    def __init__(self, new=None, version=None, msg=''):
        """

        Parameters
        ----------
        new : str, optional
          What new construct to use
        version : str, optional
          Since which version is deprecated
        kwargs
        """
        super(DeprecatedError, self).__init__()
        self.version = version
        self.new = new
        self.msg = msg

    def __str__(self):
        s = self.msg if self.msg else ''
        if self.version:
            s += (" is deprecated" if s else "Deprecated") + " since version %s." % self.version
        if self.new:
            s += " Use %s instead." % self.new
        return s


class OutdatedExternalDependency(MissingExternalDependency):
    """External dependency is present but outdated"""

    def __init__(self, name, ver=None, ver_present=None, msg=""):
        super(OutdatedExternalDependency, self).__init__(name, ver=ver, msg=msg)
        self.ver_present = ver_present

    def __str__(self):
        to_str = super(OutdatedExternalDependency, self).__str__()
        to_str += ". You have version %s" % self.ver_present \
            if self.ver_present else \
            " Some unknown version of dependency found."
        return to_str


class CommandNotAvailableError(CommandError):
    """Thrown if a command is not available due to certain circumstances.
    """
    pass


class InsufficientArgumentsError(ValueError):
    """To be raise instead of `ValueError` when use help output is desired"""
    pass
