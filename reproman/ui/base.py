# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the ReproMan package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Base classes for UI

"""

__docformat__ = 'restructuredtext'

import abc


from ..utils import auto_repr


@auto_repr
class InteractiveUI(object, metaclass=abc.ABCMeta):
    """Semi-abstract class for interfaces to implement interactive UI"""

    @abc.abstractmethod
    def question(self, text,
                 title=None, choices=None,
                 default=None,
                 error_message=None,
                 hidden=False):
        pass

    def yesno(self, *args, **kwargs):
        default = kwargs.pop('default', None)
        if default:
            if hasattr(default, 'lower'):
                default = default.lower()
            elif isinstance(default, bool):
                default = {True: 'yes', False: 'no'}[default]
        response = self.question(
            *args, choices=['yes', 'no', 'y', 'n'],
            default=default,
            **kwargs
        ).rstrip('\n')
        if response in ('yes', 'y'):
            return True
        elif response in ('no', 'n'):
            return False
        else:
            raise RuntimeError("must not happen but did")
