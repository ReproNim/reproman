# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""High-level interface definition

"""

__docformat__ = 'restructuredtext'


# the following should be series of import definitions for interface implementations
# that shall be exposed in the Python API and the cmdline interface
# all interfaces should be associated with (at least) one of the groups below
_group_dataset = (
    'Commands for manipulating computation environments',
    [
        # source module, source object[, dest. cmdline name[, dest python name]]
        # src module can be relative, but has to be relative to the main 'niceman' package
        ('niceman.interface.create', 'Create'),
        ('niceman.interface.install', 'Install'),
        ('niceman.interface.delete', 'Delete'),
        ('niceman.interface.start', 'Start'),
        ('niceman.interface.stop', 'Stop'),
        ('niceman.interface.login', 'Login'),
        ('niceman.interface.execute', 'Execute'),
        # ('niceman.distribution.run', 'Run'),
    ])

_group_misc = (
    'Miscellaneous commands',
    [
        ('niceman.interface.ls', 'Ls'),
        ('niceman.interface.backend_parameters', 'BackendParameters'),
        # ('niceman.interface.trace', 'Trace'),
        # ('niceman.interface.shell', 'Shell'),
        ('niceman.interface.retrace', 'Retrace'),
        ('niceman.interface.diff', 'Diff'),
        ('niceman.interface.test', 'Test'),
    ])
