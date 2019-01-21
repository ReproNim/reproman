# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
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
        # src module can be relative, but has to be relative to the main 'reproman' package
        ('reproman.interface.create', 'Create'),
        ('reproman.interface.install', 'Install'),
        ('reproman.interface.delete', 'Delete'),
        ('reproman.interface.start', 'Start'),
        ('reproman.interface.stop', 'Stop'),
        ('reproman.interface.login', 'Login'),
        ('reproman.interface.execute', 'Execute'),
        ('reproman.interface.run', 'Run'),
    ])

_group_misc = (
    'Miscellaneous commands',
    [
        ('reproman.interface.ls', 'Ls'),
        ('reproman.interface.jobs', 'Jobs'),
        ('reproman.interface.backend_parameters', 'BackendParameters'),
        # ('reproman.interface.trace', 'Trace'),
        # ('reproman.interface.shell', 'Shell'),
        ('reproman.interface.retrace', 'Retrace'),
        ('reproman.interface.diff', 'Diff'),
        ('reproman.interface.test', 'Test'),
    ])
