# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
#   Originally written by Yaroslav Halchenko  for Fail2Ban and later
#   adopted for use in DataLad and ReproMan and thus relicensed under MIT/Expat.
#   Relicensing was conveyed via email to other contributors.
#
#  ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
from __future__ import absolute_import

import collections


class UnknownKeyError(KeyError):
    def __init__(self, *args, known=None):
        super().__init__(*args)
        self.known = known

    def __str__(self):
        return super().__str__() + ". Known keys: %s" % ', '.join(map(str, self.known or []))


class KnownKeysDict(collections.OrderedDict):
    """A derived class which would provide a KeyError message listing available keys
    """

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError as exc:
            raise UnknownKeyError(*exc.args, known=list(self)) from exc