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

    resource = Resource.factory('remote-docker', config_path=repronim_cfg_path)
    assert len(resource._config) == 0
    assert resource.get_config('type') == 'docker'
    assert resource.get_config('engine_url') == 'tcp://127.0.0.1:2375'
    assert resource.get_config('container') == 'dockercontainer'
    assert resource.get_config('base_image_tag') == 'ubuntu:latest'
    assert resource.get_config('stdin_open') == True

    config = {
        'new-term': 'abc123',
        'base_image_tag': 'ubuntu:trusty'
    }
    resource = Resource.factory('remote-docker', config, config_path=repronim_cfg_path)
    assert len(resource._config) == 2
    assert resource.get_config('type') == 'docker'
    assert resource.get_config('engine_url') == 'tcp://127.0.0.1:2375'
    assert resource.get_config('container') == 'dockercontainer'
    assert resource.get_config('base_image_tag') == 'ubuntu:trusty'
    assert resource.get_config('stdin_open') == True
    assert resource.get_config('new-term') == 'abc123'

    resource.set_config('base_image_tag', 'centos:latest')
    assert resource.get_config('base_image_tag') == 'centos:latest'
