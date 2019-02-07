# Container holding a reproman development environment.
#
# To build:
#	docker build -t reproman:redhat \
#       -f Dockerfile-redhat \
#		--build-arg IMAGE=centos:7 \
#		--build-arg UNAME=$USER \
#		--build-arg UID=$(id -u) \
#		--build-arg GID=$(id -g) \
#		.
#
#	or docker-compose build redhat (be sure to update IMAGE, UID, and GID in docker-compose.yml)
#
# To run:
#	docker run -it --name reproman-redhat \
#		-v $PWD:/home/$USER/reproman \
#		-v /var/run/docker.sock:/var/run/docker.sock \
#		reproman:redhat
#
#	or docker-compose run redhat

ARG IMAGE=centos:latest
FROM $IMAGE

RUN yum install -y epel-release \
    && yum groupinstall -y 'Development Tools' \
    && yum install -y python-devel.x86_64 python-crypto tar \
    python-argparse.noarch python-pip vim wget sqlite-devel \
    && pip install --upgrade pip setuptools chardet

# Create a container user account that matches a system user account.
ARG UNAME=reproman
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID $UNAME \
	&& useradd -m -u $UID -g $GID -s /bin/bash $UNAME

COPY . /home/$UNAME/reproman
COPY reproman.cfg /home/$UNAME

RUN wget https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh \
    && bash Miniconda2-latest-Linux-x86_64.sh -b \
    && rm Miniconda2-latest-Linux-x86_64.sh \
    && echo 'export PATH=$HOME/miniconda2/bin:$PATH' >> ~/.bashrc \
    && source ~/.bashrc \
    && ~/miniconda2/bin/conda create -y --name reproman python=2.7 \
    && source ~/miniconda2/bin/activate reproman \
    && chown -R $UID.$GID /home/$UNAME \
    && rm -rf '/home/'$UNAME'/reproman/reproman.egg-info' \
    && find '/home/'$UNAME'/reproman' -name "*.pyc" -delete \
    && pip install -e '/home/'$UNAME'/reproman[devel]'

# USER $UID:$GID

WORKDIR /home/$UNAME

ENTRYPOINT ["/bin/bash"]