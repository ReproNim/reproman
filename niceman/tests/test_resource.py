# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from ..resource import Resource
from ..support.exceptions import MissingConfigError
import niceman.tests.fixtures

def test_resource_class(niceman_cfg_path):

    # Test retrieving a resource list.
    resource_list = Resource.get_resource_list(config_path=niceman_cfg_path)
    assert 'remote-docker' in resource_list
    assert 'my-debian' in resource_list
    assert 'my-aws-subscription' in resource_list
    assert 'ec2-workflow' in resource_list

    # Test reading a niceman.cfg file.
    resource = Resource.factory('ec2-workflow', config_path=niceman_cfg_path)
    assert resource['resource_id'] == 'ec2-workflow'
    assert resource['resource_type'] == 'ec2-environment'
    assert resource['resource_client'] == 'my-aws-subscription'
    assert resource['region_name'] == 'us-east-1'
    assert resource['instance_type'] == 't2.micro'

    # Test overriding the settings read from a niceman.cfg file.
    config = {
        'new_config_var': 'abc123',
        'instance_type': 'm3.medium'
    }
    resource = Resource.factory('ec2-workflow', config, config_path=niceman_cfg_path)
    assert len(resource) == 11
    assert resource['resource_id'] == 'ec2-workflow'
    assert resource['resource_type'] == 'ec2-environment'
    assert resource['resource_client'] == 'my-aws-subscription'
    assert resource['region_name'] == 'us-east-1'
    assert resource['instance_type'] == 'm3.medium'
    assert resource['new_config_var'] == 'abc123'

    # Test updating a configuration setting.
    assert resource['instance_type'] == 'm3.medium'
    resource['instance_type'] = 't2.large'
    assert resource['instance_type'] == 't2.large'

    # TODO: Test below is not working in python 3.
    # Python 3 complains that MissingConfigError object has no attribute 'message'
    #
    # Test raising an exception if a config setting is missing.
    # try:
    #     resource['i-do-not-exist']
    # except MissingConfigError as e:
    #     assert e.message == "Missing configuration parameter: 'i-do-not-exist'"
    #
    # # Test trying to retrieve a nonexistent resource.
    # try:
    #     Resource.factory('i-do-not-exist', config_path=niceman_cfg_path)
    # except Exception as e:
    #     assert e.message == "No section: 'resource i-do-not-exist'"
