# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil; coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

import docker
import pytest

from ...distributions.docker import DockerDistribution
from ...distributions.docker import DockerImage
from ...distributions.docker import DockerTracer
from ...resource.session import get_local_session
from ...support.exceptions import CommandError
from ...tests.utils import skip_if_no_docker_engine, skip_if_no_network


@skip_if_no_network
@skip_if_no_docker_engine
def test_docker_trace_tag():
    client = docker.Client()
    client.pull('alpine:3.6')

    tracer = DockerTracer()

    files = ['alpine:3.6', 'non-existent-image']
    dist, remaining_files = next(tracer.identify_distributions(files))
    assert dist.name == 'docker'
    assert dist.images[0].architecture == 'amd64'
    assert dist.images[0].operating_system == 'linux'
    assert dist.images[0].repo_digests[0].startswith('alpine@sha256:')
    assert dist.images[0].repo_tags[0] == 'alpine:3.6'
    assert 'non-existent-image' in remaining_files


@skip_if_no_network
@skip_if_no_docker_engine
def test_docker_trace_id():
    client = docker.Client()
    repo_id = 'sha256:f625bd3ff910ad2c68a405ccc5e294d2714fc8cfe7b5d80a8331c72ad5cc7630'
    name = 'alpine@' + repo_id
    client.pull(name)

    tracer = DockerTracer()

    files = [name]
    dist, remaining_files = next(tracer.identify_distributions(files))
    assert dist.name == 'docker'
    assert dist.images[0].id == 'sha256:77144d8c6bdce9b97b6d5a900f1ab85da' + \
        '325fe8a0d1b0ba0bbff2609befa2dda'
    assert dist.images[0].architecture == 'amd64'
    assert dist.images[0].operating_system == 'linux'
    assert dist.images[0].id == 'sha256:77144d8c6bdce9b97b6d5a900f1ab85da' + \
        '325fe8a0d1b0ba0bbff2609befa2dda'
    assert dist.images[0].created == '2018-01-09T21:10:38.538173323Z'


@skip_if_no_network
@skip_if_no_docker_engine
def test_docker_trace_local_image():
    client = docker.Client()
    client.pull('alpine:3.6')
    tracer = DockerTracer()
    # Test tracing a local image not saved in a repository
    container = client.create_container(image='alpine:3.6',
        command='echo foo > test.txt')
    new_image = client.commit(container, repository='test-container',
        tag="001")
    client.remove_container(container)
    tracer = DockerTracer()
    files = [new_image['Id']]
    dist, _ = next(tracer.identify_distributions(files))
    assert dist.name == 'docker'
    assert dist.images[0].repo_tags[0] == 'test-container:001'

    # Clean up docker engine
    client.remove_image(new_image['Id'])


@skip_if_no_network
@skip_if_no_docker_engine
def test_docker_distribution():

    client = docker.Client()
    session = get_local_session()

    # Verify alpine:3.5 image is not stored locally
    try:
        client.remove_image('sha256:6c6084ed97e5851b5d216b20ed185230127' +
            '8584c3c6aff915272b231593f6f98')
    except docker.errors.NotFound:
        pass

    # Test tracing valid images
    dist = DockerDistribution('docker')
    dist.images = [
        DockerImage(
            'sha256:6c6084ed97e5851b5d216b20ed1852301278584c3c6aff915272' +
                'b231593f6f98',
            repo_digests=['alpine@sha256:9148d069e50eee519ec45e5683e56a1' +
                'c217b61a52ed90eb77bdce674cc212f1e'],
            repo_tags=['alpine:3.5']
        ),
        DockerImage(
            'sha256:77144d8c6bdce9b97b6d5a900f1ab85da325fe8a0d1b0ba0bbff2' +
                '609befa2dda',
            repo_digests=['alpine@sha256:f625bd3ff910ad2c68a405ccc5e294d2' +
                '714fc8cfe7b5d80a8331c72ad5cc7630'],
            repo_tags=['alpine:3.6']
        )
    ]
    dist.initiate(session)
    dist.install_packages(session)
    alpine_3_5 = client.inspect_image(dist.images[0].id)
    assert alpine_3_5['Id'] == 'sha256:6c6084ed97e5851b5d216b20ed18523012' + \
        '78584c3c6aff915272b231593f6f98'
    assert 'alpine@sha256:9148d069e50eee519ec45e5683e56a1c217b61a52ed90eb' + \
        '77bdce674cc212f1e' in alpine_3_5['RepoDigests']
    alpine_3_6 = client.inspect_image(dist.images[1].id)
    assert alpine_3_6['Id'] == 'sha256:77144d8c6bdce9b97b6d5a900f1ab85da3' + \
        '25fe8a0d1b0ba0bbff2609befa2dda'

    # FIXME: Tag checks are disabled to avoid errors from unstable IDs.  We
    # should switch to using images that under our control.  See gh-254.
    #
    # assert 'alpine:3.5' in alpine_3_5['RepoTags']
    # assert 'alpine:3.6' in alpine_3_6['RepoTags']

    # Clean up docker engine
    client.remove_image(dist.images[0].id)
    client.remove_image(dist.images[1].id)

    # Test installing a non-existent image
    dist.images = [
        DockerImage(
            'sha256:000000000000000000000000000000000000000000000000000000',
            repo_digests=['foo@00000000000000000000000000000000000000000'],
            repo_tags=['foo:latest']
        )
    ]
    with pytest.raises(CommandError):
        dist.install_packages(session)
