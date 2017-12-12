# Container holding a niceman development environment.
#
# To build:
#	docker build -t niceman:latest -f docker/Dockerfile .
#
# To run:
#	docker run -it --name niceman \
#		-v /path/to/your/local/niceman:/niceman \
#		-v /var/run/docker.sock:/var/run/docker.sock \
#		niceman:latest
 
FROM debian:jessie
#FROM ubuntu:xenial

COPY . /niceman
COPY docker/niceman.cfg /root

RUN apt-get update \
    && apt-get install -y build-essential libssl-dev libffi-dev vim wget \
    && apt-get install -y python-dev python-pyparsing python-crypto python-pip \
    && pip install --upgrade pip \
    && pip install setuptools==33.1.1 pytest docker-py boto3 dockerpty nose \
    && pip install -e /niceman

WORKDIR /root

ENTRYPOINT ["/bin/bash"]
