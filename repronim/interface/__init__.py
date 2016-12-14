# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
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
    'Commands for computation environments manipulation',
    [
        # source module, source object[, dest. cmdline name[, dest python name]]
        # src module can be relative, but has to be relative to the main 'repronim' package
        ('repronim.interface.create', 'Create'),
        ('repronim.interface.install', 'Install'),
        # ('repronim.distribution.run', 'Run'),
    ])

_group_misc = (
    'Miscellaneous commands',
    [
        ('repronim.interface.ls', 'Ls'),
        # ('repronim.interface.trace', 'Trace'),
        # ('repronim.interface.shell', 'Shell'),
        ('repronim.interface.retrace', 'Retrace'),
        ('repronim.interface.test', 'Test'),
    ])
