# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..base import ResourceConfig

def test_resource_class(niceman_cfg_path):

    # Test retrieving a resource list.
    resource_config = ResourceConfig('ec2-workflow', config_path=niceman_cfg_path)

    assert resource_config['name'] == 'ec2-workflow'
    assert resource_config['resource_type'] == 'ec2-instance'
    assert resource_config['resource_backend'] == 'my-aws-subscription'
    assert resource_config['region_name'] == 'us-east-1'
    assert resource_config['instance_type'] == 't2.micro'

    # Test overriding the settings read from a niceman.cfg file.
    new_config = {
        'new_config_var': 'abc123',
        'instance_type': 'm3.medium'
    }
    resource_config = ResourceConfig('ec2-workflow', config=new_config, config_path=niceman_cfg_path)
    assert len(resource_config) == 10
    assert resource_config['name'] == 'ec2-workflow'
    assert resource_config['resource_type'] == 'ec2-instance'
    assert resource_config['resource_backend'] == 'my-aws-subscription'
    assert resource_config['region_name'] == 'us-east-1'
    assert resource_config['instance_type'] == 'm3.medium'
    assert resource_config['new_config_var'] == 'abc123'

    # Test updating a configuration setting.
    assert resource_config['instance_type'] == 'm3.medium'
    resource_config['instance_type'] = 't2.large'
    assert resource_config['instance_type'] == 't2.large'

    # TODO: Test below is not working in python 3.
    # Python 3 complains that MissingConfigError object has no attribute 'message'
    #
    # Test raising an exception if a config setting is missing.
    # try:
    #     resource_config['i-do-not-exist']
    # except MissingConfigError as e:
    #     assert e.message == "Missing configuration parameter: 'i-do-not-exist'"
    #
    # # Test trying to retrieve a nonexistent resource.
    # try:
    #     Resource.factory('i-do-not-exist', config_path=niceman_cfg_path)
    # except Exception as e:
    #     assert e.message == "No section: 'resource i-do-not-exist'"
