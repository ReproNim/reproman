# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.resource import Resource
import repronim.tests.fixtures


def test_config_changes(repronim_cfg_path):

    resource_list = Resource.get_resource_list(config_path=repronim_cfg_path)
    assert 'remote-docker' in resource_list
    assert 'my-debian' in resource_list
    assert 'my-aws-subscription' in resource_list
    assert 'ec2-workflow' in resource_list

    resource = Resource.factory('ec2-workflow', config_path=repronim_cfg_path)
    assert resource.get_config('resource_id') == 'ec2-workflow'
    assert resource.get_config('resource_type') == 'ec2-environment'
    assert resource.get_config('resource_client') == 'my-aws-subscription'
    assert resource.get_config('region_name') == 'us-east-1'
    assert resource.get_config('instance_type') == 't2.micro'

    config = {
        'new_config_var': 'abc123',
        'instance_type': 'm3.medium'
    }
    resource = Resource.factory('ec2-workflow', config, config_path=repronim_cfg_path)
    assert len(resource._config) == 11
    assert resource.get_config('resource_id') == 'ec2-workflow'
    assert resource.get_config('resource_type') == 'ec2-environment'
    assert resource.get_config('resource_client') == 'my-aws-subscription'
    assert resource.get_config('region_name') == 'us-east-1'
    assert resource.get_config('instance_type') == 'm3.medium'
    assert resource.get_config('new_config_var') == 'abc123'

    resource.set_config('instance_type', 't2.large')
    assert resource.get_config('instance_type') == 't2.large'
