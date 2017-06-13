Bootstrap:docker
From:repronim/simple_workflow:latest

# so if image is executed we just enter the environment
%runscript
    echo "Welcome to the NICEMAN development environment."
    echo "Reprozip pre-installed via pip.  "
    echo "Niceman git repo under /opt/niceman and installed for development systemwide"
    /bin/bash

%post
    echo "Adding niceman pieces"
    umask 022
    # knock
    curl -s http://neuro.debian.net/_files/knock-snapshots;
    apt-get update -q
    eatmydata apt-get install -y strace python-pip gcc python-virtualenv python-dev git-annex-standalone git libsqlite3-dev python-yaml python-pytest

    # additional pieces peculiar to reprozip
    eatmydata apt-get install -y locales
    echo 'en_US.UTF-8 UTF-8' > /etc/locale.gen
    locale-gen

    # additional depends for niceman
    eatmydata apt-get install -y libffi-dev libssl-dev  python-apt

    # Generate our shareable env
    rm -rf /opt/niceman; mkdir -p /opt/niceman
    # not available within singularity's shell so will do system wide
    # virtualenv --system-site-packages /opt/niceman/venv
    # source /opt/niceman/venv/bin/activate
    git clone git://github.com/repronim/niceman /opt/niceman
    pip install reprozip
    # we need updated cryptography (I guess paramiko lacks versioned depends)
    pip install --upgrade cryptography
    pip install -e /opt/niceman

    # So outside 'staff' ppl could modify inside as well
    chown nobody.staff -R /opt/niceman
    chmod g+rwX -R /opt/niceman /usr/local
    chmod o+rwX -R /opt/niceman /usr/local
