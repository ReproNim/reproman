# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Classes to manage compute resources."""

import attr
from importlib import import_module
import abc

import yaml
from os.path import basename
from os.path import dirname
from os.path import exists
from os.path import join as opj
from glob import glob
import os.path

# from ..config import ConfigManager
from .. import cfg
from ..dochelpers import exc_str
from ..support.exceptions import InsufficientArgumentsError
from ..support.exceptions import ResourceError
from ..support.exceptions import ResourceNotFoundError
from ..support.exceptions import ResourceAlreadyExistsError
from ..support.exceptions import MultipleResourceMatches
from ..support.exceptions import MissingConfigError, MissingConfigFileError
from ..ui import ui


import logging
lgr = logging.getLogger('niceman.resource.base')


def attrib(*args, **kwargs):
    """
    Extend the attr.ib to include our metadata elements.
    
    ATM we support additional keyword args which are then stored within
    `metadata`:
    - `doc` for documentation to describe the attribute (e.g. in --help)
    """
    doc = kwargs.pop('doc', None)
    metadata = kwargs.get('metadata', {})
    if doc:
        metadata['doc'] = doc
    if metadata:
        kwargs['metadata'] = metadata
    return attr.ib(*args, **kwargs)


class ResourceManager(object):
    """
    A manager of the available resources.

    Provides a registry of the resources known to the user.
    Should provide API to find an existing or allocate a new
    resource and register it within the registry.
    Typically a NICEMAN process will have a single ResourceManager
    instance.
    """

    __metaclass__ = abc.ABCMeta

    # The keys which are known to be secret and should not be exposed
    SECRET_KEYS = ('access_key_id', 'secret_access_key')

    # TODO: might want an alternative
    def __init__(self):  # , config_path=None):
        self.config_manager = cfg  # ResourceManager.get_config_manager(config_path)
        self._inventory_path = self.config_manager.getpath(
            'general', 'inventory_file', opj(cfg.dirs.user_config_dir, 'inventory.yml')
        )
        # inventory is just a list of dict so can't do much on its own
        # TODO: RF later to hide away all the get/set inventory
        self.inventory = None
        self.inventory = self.get_inventory()
        # ATM inventory is actually containing just "configs", but ideally
        # it should contain the actual representation of the resource
        # objects, so we could easily reflect their state etc back within
        # the inventory upon changes/exit
        # XXX should we associate any resource we create with a manager and then
        #  update registry representation on any field (name, state etc) change?

    @staticmethod
    def factory(config):
        """
        Factory method for creating the appropriate Container sub-class.

        Parameters
        ----------
        resource_config : dict
            Configuration parameters for the resource.

        Returns
        -------
        Resource sub-class instance.
        """
        if 'type' not in config:
            raise MissingConfigError("Resource 'type' parameter missing for resource.")

        type_ = config['type']
        module_name = '_'.join(type_.split('-'))
        class_name = ''.join([token.capitalize() for token in type_.split('-')])
        try:
            module = import_module('niceman.resource.{}'.format(module_name))
        except Exception as exc:
            # although typically it should be an ImportError, it might happen
            # that it leads to some other error being thrown by the beast
            # so we shouldn't blow with original msg
            raise ResourceError(
                "Failed to import resource: {}.  Known ones are: {}".format(
                    exc_str(exc),
                    ', '.join(ResourceManager._discover_types()))
            )
        instance = getattr(module, class_name)(**config)
        return instance

    # TODO: Following methods might better be in their own class
    @staticmethod
    def _discover_types():
        l = []
        for f in glob(opj(dirname(__file__), '*.py')):
            f_ = basename(f)
            if f_ in ('base.py',) or f_.startswith('_'):
                continue
            l.append(f_[:-3])
        return sorted(l)

    def get_resource_config(self, name_id=None, name=None, id_=None):
        """
        Sort through the parameters supplied by the user at the command line and then
        request the ones that are missing that are needed to find the config and
        inventory files and then build the config dictionary needed to connect
        to the environment.

        Parameters
        ----------
        name_id : string, optional
        name : string, optional
            Name of the resource
        id_ : string, optional
            The identifier of the resource as assigned to it by the backend

        Returns
        -------
        config : dict
            The config settings for the name.
        """

        # TODO: handle name_id
        if not (name_id or name or id_):
            raise InsufficientArgumentsError("Specify resource name or id")

        # make it easy on us for now
        if name_id:
            if name or id_:
                raise ValueError("If you specify name_id, do not specify name or id explicitly")
            # we need to search for the specific name/id
            match = None
            for iname, iconfig in self.inventory.items():
                iname2 = iconfig.get('name')
                if iname2 and iname2 != iname:
                    lgr.warning(
                        "Config name (%s) does not match name in the inventory %s",
                        iname, iname2
                    )

                iid = iconfig.get('id')
                if (iname and iname.startswith(name_id)) or \
                    (iid and iid.startswith(name_id)):
                    if match:
                        raise MultipleResourceMatches(
                            "Resource %s matches %s, although another matched before: %s"
                            % (iconfig, name_id, match)
                        )
                    match = iname, iconfig
                    # keep going so we check if there is no multiple matches
            if not match:
                raise ResourceNotFoundError(
                    "Could not find a resource having a name or an id "
                    "starting with %s" % name_id)
            inventory_name, inventory_config = match
        else:
            assert name or id_, "either name or id_ should be specified"

            inventory_config = None
            if name:
                if name not in self.inventory:
                    raise ResourceNotFoundError(
                        "No resource with name %s in the inventory. Present: %s"
                        % (name, ', '.join(self.inventory))
                    )
                inventory_config = self.inventory[name]
                inventory_name = name
                iid = inventory_config.get('id')
                if id_ and iid and (id_ != iid):
                    raise ResourceNotFoundError(
                        "Found resource with name %s does not have requested "
                        "id %s" % (name, id_)
                    )
            elif id_:
                for iname, i in self.inventory.items():
                    if i.get('id') == id_:
                        inventory_config = i
                        inventory_name = name

        if not inventory_config:
            raise ResourceNotFoundError(
                "Could not find a resource with name=%s and/or id=%s"
                % (name, id_)
            )
        if not inventory_config.get('name'):
            inventory_config['name'] = inventory_name

        # XXX so what is our convention here on SMTH-SMTH defining the type?
        config = dict(
            self.config_manager.items(inventory_config['type'].split('-')[0])
        )
        config.update(inventory_config)
        return config

    def get_resource(self, name_id=None, name=None, id_=None):
        config = self.get_resource_config(name_id=name_id, name=name, id_=id_)
        if not config:
            raise ResourceNotFoundError(
                "Haven't found resource given name=%s id=%s" % (name, id_))
        return self.factory(config)

    def create_resource(self, name=None, id_=None, type_=None):
        # TODO: place the logic I removed which would create the beast and
        # return it
        config = self.get_resouce_config(name, id_=id_)
        if config:
            raise ResourceAlreadyExistsError("TODO: provide details: %s" % str(config))
        # TODO: create the resource config and pass into the factory
        # TODO: register within the inventory

    def names(self):
        """Return names of the registered resources"""
        return self.inventory.keys()

    def ids(self):
        """Return ids of the registered resources"""
        return [
            x['id']
            for x in self.inventory.values()
            if x.get('id')
        ]

    def __len__(self):
        return len(self.inventory)

    def __iter__(self):
        for r in self.inventory:
            yield r

    # sugaring
    def __getitem__(self, name_id):
        return self.get_resource(name_id=name_id)

    # # XXX why do we need yet another ConfigManager here and not using the
    # # niceman.cfg???
    # @staticmethod
    # def get_config_manager(config_path=None):
    #     """
    #     Returns the information stored in the niceman.cfg file.
    #
    #     Parameters
    #     ----------
    #     config_path : string
    #         Path to the niceman.cfg file. (optional)
    #
    #     Returns
    #     -------
    #     cm : ConfigManager object
    #         Information stored in the niceman.cfg file.
    #     """
    #     def get_cm(config_path):
    #         if config_path:
    #             cm = ConfigManager([config_path], False)
    #         else:
    #             cm = ConfigManager()
    #         return cm
    #
    #     # Look for a niceman.cfg file in the local directory if none given.
    #     if not config_path and os.path.isfile('niceman.cfg'):
    #         config_path = 'niceman.cfg'
    #     cm = get_cm(config_path=config_path)
    #     if not config_path and len(cm._sections) == 1:
    #         config = ui.question("Enter a config file", default="niceman.cfg")
    #         cm = get_cm(config_path=config)
    #     if len(cm._sections) == 1:
    #         raise MissingConfigFileError(
    #             "Unable to locate config file: {}".format(config_path))
    #
    #     return cm

    # TODO: shouldn't be used by outsiders.  Inventory, if any explicitly,
    #  should be manipulated transparently
    def get_inventory(self):
        """
        Returns a dictionary containing the config information for all resources
        created by niceman.

        Parameters
        ----------
        inventory_path : string
            Path to the inventory file which is declared in the niceman.cfg file.

        Returns
        -------
        inventory : dict
            Hash whose key is resource name and value is the config settings for
            the resource.
        """
        inventory_path = self._inventory_path
        if not inventory_path:
            raise MissingConfigError(
                "No resource inventory path is known to %s" % self
            )

        # Create inventory file if it does not exist.
        if not os.path.isfile(inventory_path):
            lgr.info("Creating resources inventory file %s", inventory_path)
            # initiate empty inventory
            self.set_inventory()


        with open(inventory_path, 'r') as fp:
            inventory = yaml.safe_load(fp)

        return inventory

    # TODO: rename to _save inventory
    def set_inventory(self):
        """
        Save the resource inventory
        """

        # Operate on a copy so there is no side-effect of modifying original
        # inventory
        inventory = {} if not self.inventory else self.inventory.copy()

        for key in list(inventory):  # go through a copy of all keys since we modify

            # A resource without an ID has been deleted.
            inventory_item = inventory[key]
            if 'id' in inventory_item and not inventory_item['id']:
                del inventory[key]

            # Remove AWS credentials
            # TODO: split away handling of credentials.  Resource should probably
            # just provide some kind of an id for a credential which should be
            # stored in a safe credentials storage
            for secret_key in ResourceManager.SECRET_KEYS:
                if secret_key in inventory_item:
                    del inventory_item[secret_key]

        if not exists(dirname(self._inventory_path)):
            os.makedirs(dirname(self._inventory_path))

        with open(self._inventory_path, 'w') as fp:
            yaml.safe_dump(inventory, fp, default_flow_style=False)


class Resource(object):
    """
    Base class for creating and managing compute resources.
    """

    __metaclass__ = abc.ABCMeta

    # TODO: it seems we rely on resources having a name and an id
    # so we should define them here

    def __repr__(self):
        return 'Resource({})'.format(self.name)

    def refresh(self):
        """Connect to the resource possibly refreshing the status etc"""
        self.connect()

    @abc.abstractmethod
    def connect(self):
        pass

    def add_command(self, command, env=None):
        """
        Add a command to the command buffer so that all commands can be
        run at once in a batch submit to the environment.

        Parameters
        ----------
        command : string or list
            Command string or list of command string tokens.

        env : dict
            Additional (or replacement) environment variables which are applied
            only to the current call
        """
        if not hasattr(self, '_command_buffer'):
            self._command_buffer = []  # Each element is a dictionary in the
                                       # form {command=[], env={}}
        self._command_buffer.append({'command': command, 'env': env})

    def execute_command_buffer(self, session=None):
        """
        Send all the commands in the command buffer to the environment for
        execution.
        """
        if not session:
            session = self.get_session(pty=False)
        for command in self._command_buffer:
            lgr.debug("Running command '%s'", command['command'])
            session.execute_command(command['command'], env=command['env'])

    def set_envvar(self, var, value):
        """
        Save an environment variable for inclusion in the environment

        Parameters
        ----------
        var : string
            Variable name
        value : string
            Variable value

        Returns
        -------

        """
        # TODO: This wouldn't work correctly since pretty much each command
        # then should have its desired env recorded since set_envvar
        # could be interleaved with add_command calls
        if not hasattr(self, '_env'):
            self._env = {}

        self._env[var] = value

    def get_updated_env(self, custom_env):
        """
        Returns an env dictionary with additional or replaced values.

        Parameters
        ----------
        custom_env : dict
            Environment variables to merge into the existing list of declared
            environment variables stored in self._env

        Returns
        -------
        dictionary
        """
        if hasattr(self, '_env'):
            merged_env = self._env.copy()
            if custom_env:
                merged_env.update(custom_env)
            return merged_env

        return custom_env

    @classmethod
    def _generate_id(cls):
        import uuid
        # just a random uuid for now, TODO: think if we somehow could
        # fingerprint it so to later be able to decide if it is 'ours'? ;)
        return str(uuid.uuid1())

