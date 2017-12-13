# Container holding a niceman development environment.
#
# To build:
#	docker build -t niceman:latest -f docker/Dockerfile .
#
# To run:
#	docker run -it --name niceman \
#		-v $PWD:/root/niceman \
#		-v /var/run/docker.sock:/var/run/docker.sock \
#		niceman:latest
 
FROM debian:jessie
#FROM ubuntu:xenial

RUN apt-get update \
    && apt-get install -y build-essential libssl-dev libffi-dev vim wget \
    && apt-get install -y python-dev python-pyparsing python-crypto python-pip \
    && pip install --upgrade pip


COPY . /root/niceman
COPY docker/niceman.cfg /root

# TODO: create a matching user here so we could bind mount and develop
# within docker environment
RUN pip install -e '/root/niceman[devel]'

WORKDIR /root

ENTRYPOINT ["/bin/bash"]
