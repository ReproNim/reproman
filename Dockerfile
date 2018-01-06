# Container holding a niceman development environment.
#
# To build:
#	docker build -t niceman:latest \
#		--build-arg IMAGE=debian:jessie \
#		--build-arg UNAME=$USER \
#		--build-arg UID=$(id -u) \
#		--build-arg GID=$(id -g) \
#		.
#
#	or docker-compose build (be sure to update IMAGE, UID, and GID in docker-compose.yml)
#
# To run:
#	docker run -it --name niceman \
#		-v $PWD:/home/$USER/niceman \
#		-v /var/run/docker.sock:/var/run/docker.sock \
#		niceman:latest
#
#	or docker-compose run niceman

ARG IMAGE=ubuntu:xenial
FROM $IMAGE

RUN apt-get update \
    && apt-get install -y build-essential libssl-dev libffi-dev vim wget \
    && apt-get install -y python-dev python-pyparsing python-crypto python-pip \
    && pip install --upgrade pip

# Create a container user account that matches a system user account.
ARG UNAME=niceman
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID $UNAME \
	&& useradd -m -u $UID -g $GID -s /bin/bash $UNAME

COPY . /home/$UNAME/niceman
COPY niceman.cfg /home/$UNAME

RUN chown -R $UID.$GID /home/$UNAME \
	&& pip install -e '/home/'$UNAME'/niceman[devel]'

USER $UID:$GID

WORKDIR /home/$UNAME

ENTRYPOINT ["/bin/bash"]