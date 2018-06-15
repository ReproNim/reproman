# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the niceman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from os.path import join as opj, dirname, pardir
from pytest import raises
from niceman.formats.niceman import NicemanProvenance
from niceman.distributions.debian import DebianDistribution
from niceman.distributions.conda import CondaDistribution

yaml_dir = opj(dirname(__file__), pardir, pardir, 'interface', 'tests', 'files')
multi_debian_yaml = opj(yaml_dir, 'multi_debian.yaml')
diff_1_yaml = opj(yaml_dir, 'diff_1.yaml')

def test_get_distributions():
    env = NicemanProvenance(multi_debian_yaml).get_environment()
    with raises(ValueError):
        env.get_distribution(DebianDistribution)
    dist = env.get_distribution(CondaDistribution)
    assert dist is None
    env = NicemanProvenance(diff_1_yaml).get_environment()
    dist = env.get_distribution(DebianDistribution)
    assert isinstance(dist, DebianDistribution)
