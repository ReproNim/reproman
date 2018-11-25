# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##


# NOTE: The singularity classes SingularitySession and PTYSingularitySession
# are tested in test_session.test_session_abstract_methods()

import os
import pytest
import tempfile

import logging
import re
from ..singularity import Singularity, SingularitySession
from ...tests.utils import skip_if_no_singularity, skip_if_no_network, \
    swallow_logs, assert_in


@skip_if_no_network
@skip_if_no_singularity
def test_singularity_resource_class():

    # Set working directory to a scratch directory since we will be creating
    # Singularity image files during testing.
    orig_cwd = os.getcwd()
    tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)

    with swallow_logs(new_level=logging.DEBUG) as log:

        # Test creating a new singularity container instance.
        resource = Singularity(name='foo',
            image='shub://truatpasteurdotfr/singularity-alpine')
        assert resource.name == 'foo'
        assert resource.image == 'shub://truatpasteurdotfr/singularity-alpine'
        resource.connect()
        assert resource.id is None
        assert resource.status is None
        resource.create()
        assert resource.id.startswith('foo-')
        assert resource.status == 'running'

        # Test trying to create an already running instance.
        resource_duplicate = Singularity(name='foo',
            image='shub://truatpasteurdotfr/singularity-alpine')
        resource_duplicate.connect()
        assert resource_duplicate.id.startswith('foo-')
        assert resource_duplicate.status == 'running'
        resource_duplicate.create()
        assert_in('Resource foo already exists.', log.lines)

        # Test retrieving instance info.
        info = resource.get_instance_info()
        assert info['name'] == 'foo'
        assert re.match(r'^\d+$', info['pid'])
        assert info['image'].endswith('.simg')

        # Test starting an instance.
        with pytest.raises(NotImplementedError):
            resource.start()

        # Test stopping an instance.
        with pytest.raises(NotImplementedError):
            resource.stop()

        # Test getting a resource session.
        session = resource.get_session()
        assert isinstance(session, SingularitySession)

        # Test deleting an instance.
        resource.delete()
        assert resource.id is None
        assert resource.status is None

        # Test retrieving info from a non-existent instance.
        info = resource.get_instance_info()
        assert info is None

    # Return to original working directory
    os.chdir(orig_cwd)