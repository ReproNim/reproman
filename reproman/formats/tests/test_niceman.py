# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##

from __future__ import absolute_import

import io

from reproman.distributions.base import EnvironmentSpec
from reproman.distributions.conda import CondaChannel
from reproman.distributions.conda import CondaDistribution
from reproman.distributions.conda import CondaEnvironment
from reproman.distributions.conda import CondaPackage
from reproman.distributions.debian import APTSource
from reproman.distributions.debian import DEBPackage
from reproman.distributions.debian import DebianDistribution
from reproman.distributions.vcs import GitDistribution
from reproman.distributions.vcs import GitRepo
from reproman.distributions.vcs import SVNDistribution
from reproman.distributions.vcs import SVNRepo
from reproman.distributions.venv import VenvDistribution
from reproman.distributions.venv import VenvEnvironment
from reproman.distributions.venv import VenvPackage
from reproman.formats.reproman import RepromanProvenance

from .constants import REPROMAN_SPEC1_YML_FILENAME


def test_write():
    output = io.StringIO()
    # just load
    file_format = RepromanProvenance(REPROMAN_SPEC1_YML_FILENAME)
    env = file_format.get_environment()
    # just a basic test that we loaded stuff correctly
    assert len(env.distributions) == 2
    assert env.distributions[0].name == "conda"
    assert len(env.distributions[1].apt_sources) == 3
    # and save
    RepromanProvenance.write(output, env)
    out = output.getvalue()
    env_reparsed = RepromanProvenance(out).get_environment()
    # and we could do the full round trip while retaining the same "value"
    assert env == env_reparsed


def test_spec_round_trip():
    # FIXME: This should also test GitDistribution's, but RepromanProvenance
    # can't currently load those (gh-222).

    spec = EnvironmentSpec(
        distributions=[
            DebianDistribution(
                name="debian",
                apt_sources=[
                    APTSource(
                        name="apt_Debian_stable_main_0",
                        component="main",
                        archive="stable",
                        architecture="amd64",
                        codename="stretch",
                        origin="Debian",
                        label="Debian",
                        site="ftp.us.debian.org",
                        archive_uri="http://ftp.us.debian.org/debian",
                        date="2018-03-10 10:21:19+00:00",
                    )
                ],
                packages=[
                    DEBPackage(name="debpackage"),
                    DEBPackage(
                        name="libc-bin",
                        upstream_name=None,
                        version="2.24-11+deb9u3",
                        architecture="amd64",
                        source_name="glibc",
                        source_version=None,
                        size="779468",
                        md5="3b9aaa83b5253895b8e13509659662e4",
                        sha1=None,
                        sha256="aaa",
                        versions={
                            "2.24-11+deb9u1": ["apt_Debian_stable_foo"],
                            "2.24-11+deb9u3": ["apt_Debian_stable_bar", "apt__now__0"],
                        },
                        install_date="2018-03-12 10:55:13+00:00",
                        files=["/usr/bin/zdump"],
                    ),
                ],
                version="9.4",
            ),
            CondaDistribution(
                name="conda",
                path="/path/to/miniconda3",
                conda_version="4.4.10",
                python_version="3.6.3.final.0",
                platform="linux-64",
                environments=[
                    CondaEnvironment(
                        name="root",
                        path="/path/to/miniconda3",
                        packages=[
                            CondaPackage(name="condapkg"),
                            CondaPackage(
                                version="36.5.0",
                                build="py36he42e2e1_0",
                                name="setuptools",
                                md5="cb1383539629db998105faf7e91e2bc7",
                                url="https://somewhere",
                            ),
                        ],
                        channels=[CondaChannel(name="defaults", url="https://somewhere")],
                    ),
                    CondaEnvironment(
                        name="other", path="/path/to/miniconda3", packages=[CondaPackage(name="condapkg2")]
                    ),
                ],
            ),
            GitDistribution(name="git", packages=[GitRepo(path="/path/to/repo")]),
            SVNDistribution(name="svn", packages=[SVNRepo(path="/path/to/repo")]),
            VenvDistribution(
                name="venv0",
                path="/usr/bin/virtualenv",
                venv_version="15.1.0",
                environments=[
                    VenvEnvironment(
                        path="venv-reproman",
                        python_version="3.5.3",
                        packages=[
                            VenvPackage(
                                version="3.12", name="PyYAML", location="/path/to/venv/site-packages", local=True
                            )
                        ],
                    )
                ],
            ),
            VenvDistribution(name="venv1"),
        ]
    )

    output = io.StringIO()
    RepromanProvenance.write(output, spec)
    loaded = RepromanProvenance(output.getvalue()).get_environment()
    assert spec == loaded
