# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Helper utility to copy files to an environment
"""

__docformat__ = 'restructuredtext'

import os

from .base import Interface
import niceman.interface.base # Needed for test patching
from ..support.param import Parameter
from ..support.constraints import EnsureStr, EnsureNone
from ..resource import ResourceManager

from logging import getLogger
lgr = getLogger('niceman.api.put')


class Put(Interface):
    """Copy a file to a computation environment

    Examples
    --------

      $ niceman put local-file remote-file --name=my-resource

    """

    _params_ = dict(
        paths=Parameter(
            doc="source and destination paths",
            metavar='PATHS',
            nargs="+",
            constraints=EnsureStr(),
        ),
        mode=Parameter(
            args=("-m", "--mode"),
            doc="mode of file that is created",
            metavar='MODE',
            constraints=EnsureStr(),
        ),
        owner=Parameter(
            args=("-o", "--owner"),
            doc="owner of the file on the remote environment",
            metavar='OWNER',
            constraints=EnsureStr(),
        ),
        group=Parameter(
            args=("-g", "--group"),
            doc="group of the file on the remote environment",
            metavar='GROUP',
            constraints=EnsureStr(),
        ),
        name=Parameter(
            args=("-n", "--name"),
            doc="""Name of the resource to consider. To see
            available resource, run the command 'niceman ls'""",
            constraints=EnsureStr(),
        ),
        # XXX reenable when we support working with multiple instances at once
        # resource_type=Parameter(
        #     args=("-t", "--resource-type"),
        #     doc="""Resource type to work on""",
        #     constraints=EnsureStr(),
        # ),
        resource_id=Parameter(
            args=("-id", "--resource-id",),
            doc="ID of the environment container",
            # constraints=EnsureStr(),
        ),
        # TODO: should be moved into generic API
        config=Parameter(
            args=("-c", "--config",),
            doc="path to niceman configuration file",
            metavar='CONFIG',
            # constraints=EnsureStr(),
        ),
    )

    @staticmethod
    def __call__(paths, mode, owner, group, name,
                 resource_id=None, config=None):

        source_path = paths[0]
        if len(paths) < 2:
            dest_path = source_path
        else:
            dest_path = paths[1]

        from niceman.ui import ui
        if not name and not resource_id:
            name = ui.question(
                "Enter a resource name",
                error_message="Missing resource name"
            )

        # Get configuration and environment inventory
        # TODO: this one would ask for resource type whenever it is not found
        #       why should we???
        resource_info, inventory = ResourceManager.get_resource_info(config,
                                                            name, resource_id)

        # Delete resource environment
        env_resource = ResourceManager.factory(resource_info)
        env_resource.connect()

        if not env_resource.id:
            raise ValueError("No resource found given the info %s" % str(resource_info))

        session = env_resource.get_session()
        session.copy_to(source_path, dest_path)

        if mode:
            session.chmod(int(mode, 8), dest_path)

        if owner or group:
            if not owner: owner = os.stat(source_path).st_uid
            if not group: group = os.stat(source_path).st_gid
            session.chown(int(owner), int(group), dest_path)

        ResourceManager.set_inventory(inventory)

        lgr.info("Copied %s from the environment %s", source_path, name)