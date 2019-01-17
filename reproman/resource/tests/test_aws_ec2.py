# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import logging
from mock import patch, call, MagicMock

from ...utils import swallow_logs
from ...tests.utils import assert_in
from ..base import ResourceManager
from ..ssh import SSH


def test_awsec2_class():

    with patch('boto3.resource') as client, \
            patch.object(SSH, 'get_session', return_value='started_session'), \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Test connecting when a resource doesn't exist.
        client.return_value = MagicMock(
            instances=MagicMock(filter=lambda Filters: [])
        )
        config = {
            'name': 'non-existent-instance',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id'
        }
        resource = ResourceManager.factory(config)
        resource.connect()
        assert resource.id is None
        assert resource.status is None

        # Test catching exception when multiple resources are found at connection.
        client.return_value = MagicMock(
            instances=MagicMock(filter=lambda Filters: [
                MagicMock(
                    instance_id='i-22221ddf096c22bb0',
                    state={'Name': 'running'}
                ),
                MagicMock(
                    instance_id='i-3333f40de2b9b8967',
                    state={'Name': 'running'}
                )
            ])
        )
        config = {
            'name': 'duplicate-instance-name',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id'
        }
        resource = ResourceManager.factory(config)
        try:
            resource.connect()
        except Exception as e:
            assert e.args[0] == "Multiple container matches found"

        # Test connecting to an existing resource.
        client.return_value = MagicMock(
            Instance=lambda id: MagicMock(
                instance_id='i-00002777d52482d9c',
                state={'Name': 'running'}
            )
        )
        config = {
            'name': 'my-instance-name',
            'id': 'i-00002777d52482d9c',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id',
            'key_name': 'my-ssh-key',
            'key_filename': '/home/me/.ssh/id_rsa'
        }
        resource = ResourceManager.factory(config)
        resource.connect()
        assert resource.image == 'ami-c8580bdf'
        assert resource.id == 'i-00002777d52482d9c'
        assert resource.instance_type == 't2.micro'
        assert resource.key_filename == '/home/me/.ssh/id_rsa'
        assert resource.key_name == 'my-ssh-key'
        assert resource.name == 'my-instance-name'
        assert resource.region_name == 'us-east-1'
        assert resource.access_key_id == 'my-aws-access-key-id'
        assert resource.secret_access_key == 'my-aws-secret-access-key-id'
        assert resource.security_group == 'default'
        assert resource.status == 'running'
        assert resource.type == 'aws-ec2'

        # Test creating an existing resource and catch the exception.
        try:
            resource.create()
        except Exception as e:
            assert e.args[0] == "Instance 'i-00002777d52482d9c' already exists in AWS subscription"

        # Test creating resource.
        client.return_value = MagicMock(
            instances=MagicMock(filter=lambda Filters: []),
            Instance=lambda id: MagicMock(
                instance_id='i-11112777d52482d9c',
                state={'Name': 'running'}
            )
        )
        config = {
            'name': 'my-instance-name',
            'type': 'aws-ec2',
            'access_key_id': 'my-aws-access-key-id',
            'secret_access_key': 'my-aws-secret-access-key-id',
            'key_name': 'my-ssh-key',
            'key_filename': '/home/me/.ssh/id_rsa'
        }
        resource = ResourceManager.factory(config)
        resource.connect()
        results = resource.create()
        assert results['id'] == 'i-11112777d52482d9c'
        assert results['status'] == 'running'
        assert_in('EC2 instance i-11112777d52482d9c initialized!', log.lines)
        assert_in('EC2 instance i-11112777d52482d9c to start running!', log.lines)
        assert_in('Waiting for EC2 instance i-11112777d52482d9c to complete initialization...', log.lines)
        assert_in('EC2 instance i-11112777d52482d9c initialized!', log.lines)

        # Test stopping resource.
        resource.stop()
        calls = [
            call.stop()
        ]
        resource._ec2_instance.assert_has_calls(calls, any_order=True)

        # Test starting resource.
        resource.start()
        calls = [
            call.start()
        ]
        resource._ec2_instance.assert_has_calls(calls, any_order=True)

        # Test deleting resource.
        resource.delete()
        calls = [
            call.terminate()
        ]
        resource._ec2_instance.assert_has_calls(calls, any_order=True)

        session = resource.get_session()
        assert session == 'started_session'
