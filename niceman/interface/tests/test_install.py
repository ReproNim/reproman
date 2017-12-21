# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from niceman.cmdline.main import main

import logging
from mock import patch, call, MagicMock

from ...utils import swallow_logs
from ...tests.utils import assert_in


def test_install_interface(demo1_spec, niceman_cfg_path):

    with patch('docker.Client') as client, \
        patch('niceman.distributions.debian.DebianDistribution.install_packages'), \
        patch('niceman.resource.ResourceManager.set_inventory'), \
        patch('niceman.resource.ResourceManager.get_inventory') as get_inventory, \
        swallow_logs(new_level=logging.DEBUG) as log:

        client.return_value = MagicMock(
            containers=lambda all: [
                {
                    'Id': '326b0fdfbf838',
                    'Names': ['/my-resource'],
                    'State': 'running'
                }
            ]
        )

        get_inventory.return_value = {
            "my-resource": {
                "status": "running",
                "engine_url": "tcp://127.0.0.1:2375",
                "type": "docker-container",
                "name": "my-resource",
                "id": "326b0fdfbf838"
            }
        }

        args = ['install',
                '--spec', demo1_spec,
                '--name', 'my-resource',
                '--config', niceman_cfg_path
        ]
        main(args)

        def container_call(cmd):
            return call().exec_create(
                cmd=cmd,
                container={'State': 'running', 'Id': '326b0fdfbf838', 'Names': ['/my-resource']}
            )

        calls = [
            call(base_url='tcp://127.0.0.1:2375'),
            call().exec_create(cmd=['[', '-e', '/etc/apt/sources.list.d/niceman.sources.list', ']'], container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd='sh -c \'echo "# Niceman repo sources" > /etc/apt/sources.list.d/niceman.sources.list\'', container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="grep -q 'deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main contrib non-free' /etc/apt/sources.list.d/niceman.sources.list", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="sh -c 'echo deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list'", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="grep -q 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free' /etc/apt/sources.list.d/niceman.sources.list", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="sh -c 'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list'", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="grep -q 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free' /etc/apt/sources.list.d/niceman.sources.list", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="sh -c 'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list'", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd=['apt-key', 'adv', '--recv-keys', '--keyserver', 'hkp://pool.sks-keyservers.net:80', '0xA5D32F012649A5A9'], container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="grep -q 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free' /etc/apt/sources.list.d/niceman.sources.list", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="sh -c 'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list'", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="grep -q 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free' /etc/apt/sources.list.d/niceman.sources.list", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd="sh -c 'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list'", container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd=['apt-key', 'adv', '--recv-keys', '--keyserver', 'hkp://pool.sks-keyservers.net:80', '0xA5D32F012649A5A9'], container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
            call().exec_create(cmd=['apt-get', '-o', 'Acquire::Check-Valid-Until=false', 'update'], container={'Id': '326b0fdfbf838', 'Names': ['/my-resource'], 'State': 'running'}),
        ]

        client.assert_has_calls(calls, any_order=True)

        assert_in('Adding Debian update to environment command list.', log.lines)
        assert_in("Running command ['[', '-e', '/etc/apt/sources.list.d/niceman.sources.list', ']']", log.lines)
        assert_in('Running command \'sh -c \\\'echo "# Niceman repo sources" > /etc/apt/sources.list.d/niceman.sources.list\\\'\'', log.lines)
        assert_in('Running command "grep -q \'deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main contrib non-free\' /etc/apt/sources.list.d/niceman.sources.list"', log.lines)
        assert_in("Adding line 'deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Running command "sh -c \'echo deb http://snapshot.debian.org/archive/debian/20170531T084046Z/ sid main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list\'"', log.lines)
        assert_in('Running command "grep -q \'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free\' /etc/apt/sources.list.d/niceman.sources.list"', log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Running command "sh -c \'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list\'"', log.lines)
        assert_in('Running command "grep -q \'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free\' /etc/apt/sources.list.d/niceman.sources.list"', log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Running command "sh -c \'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list\'"', log.lines)
        assert_in("Running command ['apt-key', 'adv', '--recv-keys', '--keyserver', 'hkp://pool.sks-keyservers.net:80', '0xA5D32F012649A5A9']", log.lines)
        assert_in('Running command "grep -q \'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free\' /etc/apt/sources.list.d/niceman.sources.list"', log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Running command "sh -c \'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171208T032012Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list\'"', log.lines)
        assert_in('Running command "grep -q \'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free\' /etc/apt/sources.list.d/niceman.sources.list"', log.lines)
        assert_in("Adding line 'deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free' to /etc/apt/sources.list.d/niceman.sources.list", log.lines)
        assert_in('Running command "sh -c \'echo deb http://snapshot-neuro.debian.net:5002/archive/neurodebian/20171212T140401Z/ xenial main contrib non-free >> /etc/apt/sources.list.d/niceman.sources.list\'"', log.lines)
        assert_in("Running command ['apt-key', 'adv', '--recv-keys', '--keyserver', 'hkp://pool.sks-keyservers.net:80', '0xA5D32F012649A5A9']", log.lines)
        assert_in("Running command ['apt-get', '-o', 'Acquire::Check-Valid-Until=false', 'update']", log.lines)
