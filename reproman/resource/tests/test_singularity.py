# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##


# NOTE: The singularity classes SingularitySession and PTYSingularitySession
# are tested in test_session.test_session_abstract_methods()

import os.path as op

import pytest

import logging
import uuid
import re

from ..singularity import Singularity, SingularitySession
from ...cmd import Runner
from ...tests.skip import mark
from ...utils import swallow_logs


def test_singularity_resource_image_required():
    with pytest.raises(TypeError):
        Singularity(name='foo')


@pytest.mark.xfail(reason="Singularity Hub is down")
@mark.skipif_no_network
@mark.skipif_no_singularity
def test_singularity_resource_class(tmpdir):
    tmpdir = str(tmpdir)
    with swallow_logs(new_level=logging.DEBUG) as log:
        Runner(cwd=tmpdir).run(
            ['singularity', 'pull', '--name', 'img',
             'shub://truatpasteurdotfr/singularity-alpine'])

        # ATTN: Apparently an instance name can't contain a hyphen.
        name = "reproman_test_{}".format(str(uuid.uuid4())[:4])
        image = op.join(tmpdir, 'img')
        # Test creating a new singularity container instance.
        resource = Singularity(name=name, image=image)
        assert resource.name == name
        assert resource.image == image
        resource.connect()
        assert resource.id is None
        assert resource.status is None
        list(resource.create())
        to_delete = [resource]
        try:
            assert resource.id.startswith(name + "-")
            assert resource.status == 'running'

            # Test trying to create an already running instance.
            resource_duplicate = Singularity(name=name, image=image)
            resource_duplicate.connect()
            assert resource_duplicate.id.startswith(name + "-")
            assert resource_duplicate.status == 'running'
            list(resource_duplicate.create())
            assert "Resource '{}' already exists".format(name) in log.out

            # But using a different name with the same image would work.
            resource_nondup = Singularity(name=name + "_nondup", image=image)
            resource_nondup.connect()
            resource_nondup.name = name + "_nondup"
            to_delete.append(resource_nondup)

            # Test retrieving instance info.
            info = resource.get_instance_info()
            assert info['name'] == name
            assert re.match(r'^\d+$', info['pid'])

            info["image"] = image

            # Test starting an instance.
            with pytest.raises(NotImplementedError):
                resource.start()

            # Test stopping an instance.
            with pytest.raises(NotImplementedError):
                resource.stop()

            # Test getting a resource session.
            session = resource.get_session()
            assert isinstance(session, SingularitySession)
        finally:
            # Test deleting an instance, but do it here to try to
            # unregister the test instance even if a check above fails.
            for res in to_delete:
                res.delete()

        assert resource.id is None
        assert resource.status is None

        # Test retrieving info from a non-existent instance.
        info = resource.get_instance_info()
        assert info is None
