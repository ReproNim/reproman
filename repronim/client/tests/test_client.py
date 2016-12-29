# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the repronim package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from repronim.environment import Environment

import logging
from mock import patch, call, MagicMock

from repronim.utils import swallow_logs
from repronim.tests.utils import assert_in
from repronim.cmd import Runner
from repronim.resource import Resource
import repronim.tests.fixtures


def test_sending_command_to_localhost(repronim_cfg_path):
    """
    Test installing 2 Debian packages to the localhost.
    """
    resource = Resource.factory('localhost-shell', config_path=repronim_cfg_path)

    with patch.object(Runner, 'run', return_value='installed package') \
        as MockRunner, patch('os.environ.copy') as MockOS:

        MockOS.return_value = {}
        DEBIAN_TARGET_ENV = {'DEBIAN_FRONTEND': 'noninteractive'}

        with Environment.factory(resource) as environment:
            environment.add_command(['apt-get', 'update'])
            environment.add_command(['apt-get', 'install', '-y', 'base-files'],
                                  env=DEBIAN_TARGET_ENV)
            environment.add_command(['apt-get', 'install', '-y', 'bc'],
                                  env=DEBIAN_TARGET_ENV)

        # Verify code output.
        assert environment._command_buffer == [
            {'command':['apt-get', 'update'], 'env':None},
            {'command':['apt-get', 'install', '-y', 'base-files'], 'env':DEBIAN_TARGET_ENV},
            {'command':['apt-get', 'install', '-y', 'bc'], 'env':DEBIAN_TARGET_ENV}
        ]

        assert MockRunner.call_count == 3
        calls = [
            call(['apt-get', 'update']),
            call(['apt-get', 'install', '-y', 'base-files'], env=DEBIAN_TARGET_ENV),
            call(['apt-get', 'install', '-y', 'bc'], env=DEBIAN_TARGET_ENV),
        ]
        MockRunner.assert_has_calls(calls, any_order=True)


def test_sending_command_to_docker(repronim_cfg_path):
    """
    Test installing 2 Debian packages in a Docker instance.
    """
    resource = Resource.factory('remote-docker', config_path=repronim_cfg_path)

    with patch('docker.DockerClient') as MockClient, \
            swallow_logs(new_level=logging.DEBUG) as log:

        # Set up return values for mocked docker.Client methods.
        # client = MockClient.return_value
        # client.build.return_value = ['{"stream": "Successfully built 9a754690460d\\n"}']
        # client.create_container.return_value = {u'Id': u'd4cb4ee', u'Warnings': None}
        # client.start.return_value = None
        # client.logs.return_value = 'container standard output'
        # client.exec_create.return_value = {u'Id': u'b3245cd55'}
        # client.exec_start.return_value = ['stdout', 'from', 'container']

        # Section of code being tested.
        DEBIAN_TARGET_ENV = {'DEBIAN_FRONTEND': 'noninteractive'}

        container_config = {
            'engine_url': 'tcp://127.0.0.1:2376'
        }
        with Environment.factory(resource, config=container_config) as environment:
            environment.add_command(['apt-get', 'update'])
            environment.add_command(['apt-get', 'install', '-y', 'base-files'], env=DEBIAN_TARGET_ENV)
            environment.add_command(['apt-get', 'install', '-y', 'bc'], env=DEBIAN_TARGET_ENV)

        # Verify code output.
        calls = [
            call.exec_run(cmd=['apt-get', 'update'], stream=True),
            call.exec_run(
                cmd=['export DEBIAN_FRONTEND=noninteractive;', 'apt-get',
                     'install', '-y', 'base-files'], stream=True),
            call.exec_run(
                cmd=['export DEBIAN_FRONTEND=noninteractive;', 'apt-get',
                     'install', '-y', 'bc'], stream=True),
        ]
        environment._container.assert_has_calls(calls, any_order=True)
        assert_in("Running command '['apt-get', 'update']'", log.lines)
        assert_in("Running command '['apt-get', 'install', '-y', 'base-files']'", log.lines)
        assert_in("Running command '['apt-get', 'install', '-y', 'bc']'", log.lines)

def test_sending_command_to_ec2(repronim_cfg_path):

    with patch('boto3.resource') as MockAWS, patch('paramiko.SSHClient') as MockSSH, \
            swallow_logs(new_level=logging.DEBUG) as log:

        ssh_client = MockSSH.return_value
        ssh_client.exec_command.return_value = (MagicMock(), MagicMock(), MagicMock())

        resource = Resource.factory('repronim-aws', config_path=repronim_cfg_path)
        DEBIAN_TARGET_ENV = {'DEBIAN_FRONTEND': 'noninteractive'}

        with Environment.factory(resource) as environment:
            environment.add_command(['apt-get', 'update'])
            environment.add_command(['apt-get', 'install', '-y', 'base-files'], env=DEBIAN_TARGET_ENV)
            environment.add_command(['apt-get', 'install', '-y', 'bc'], env=DEBIAN_TARGET_ENV)

        # Run tests.
        calls = [
            call('ec2', aws_access_key_id='AWS_ACCESS_KEY_ID',
                 aws_secret_access_key='AWS_SECRET_ACCESS_KEY',
                 region_name='us-east-1'),
            call().create_instances(ImageId='ami-c8580bdf',
                                    InstanceType='t2.micro',
                                    KeyName='aws-key-name', MaxCount=1,
                                    MinCount=1, SecurityGroups=['SSH only']),
        ]
        MockAWS.assert_has_calls(calls)

        calls = [
            call().exec_command('apt-get update'),
            call().exec_command(
                'export DEBIAN_FRONTEND=noninteractive; apt-get install -y base-files'),
            call().exec_command(
                'export DEBIAN_FRONTEND=noninteractive; apt-get install -y bc'),
        ]
        MockSSH.assert_has_calls(calls)

        assert environment._command_buffer[0]['command'] == ['apt-get', 'update']
        assert environment._command_buffer[1]['command'] == ['apt-get', 'install', '-y', 'base-files']
        assert environment._command_buffer[2]['command'] == ['apt-get', 'install', '-y', 'bc']

        assert_in("Running command '['apt-get', 'update']'", log.lines)
        assert_in("Command 'apt-get update' failed, exit status = 1", log.lines)
        assert_in("Running command '['apt-get', 'install', '-y', 'base-files']'", log.lines)
        assert_in("Command 'export DEBIAN_FRONTEND=noninteractive; apt-get install -y base-files' failed, exit status = 1", log.lines)
        assert_in("Running command '['apt-get', 'install', '-y', 'bc']'", log.lines)
        assert_in("Command 'export DEBIAN_FRONTEND=noninteractive; apt-get install -y bc' completed, exit status = 1", log.lines)


