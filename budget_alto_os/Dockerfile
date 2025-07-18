ARG image_repo=ubuntu
ARG image_tag=22.04
#
FROM ${image_repo}:${image_tag} AS volttron_base
#
SHELL [ "bash", "-c" ]
#
ENV OS_TYPE=debian
ENV DIST=bookworm 
ENV VOLTTRON_GIT_BRANCH=main
ENV VOLTTRON_USER_HOME=/home/volttron
ENV VOLTTRON_HOME=${VOLTTRON_USER_HOME}/.volttron
ENV CODE_ROOT=/code
ENV VOLTTRON_ROOT=${CODE_ROOT}/volttron
ENV VOLTTRON_USER=volttron
ENV USER_PIP_BIN=${VOLTTRON_USER_HOME}/.local/bin
# ENV CONFIG=/home/volttron/configs
ENV LOCAL_USER_ID=1000
#ENV RMQ_ROOT=${VOLTTRON_USER_HOME}/rabbitmq_server
#ENV RMQ_HOME=${RMQ_ROOT}/rabbitmq_server-3.7.7
#
USER root
#
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirror.math.princeton.edu/pub/ubuntu/|g' /etc/apt/sources.list
RUN set -eux; apt-get update; apt-get install -y --no-install-recommends \
    procps \
    gosu \
    nano \
    tree \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    openssl \
    libssl-dev \
    libevent-dev \
    git \
    gnupg \
    dirmngr \
    apt-transport-https \
    wget \
    curl \
    ca-certificates \
    libffi-dev \
    sqlite3
#
# Set timezone
RUN echo UTC > /etc/timezone

# Set default 'python' to 'python3'
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
#
# Upgrade pip so that we get a pre-compiled wheel for 'cryptopgraphy', which is a dependency of Volttron
# See https://cryptography.io/en/latest/faq/#installing-cryptography-fails-with-error-can-not-find-rust-compiler
RUN pip install --upgrade pip
#
# Create a user called 'volttron'
RUN id -u $VOLTTRON_USER &>/dev/null || adduser --disabled-password --gecos "" $VOLTTRON_USER
#
RUN mkdir -p /code && chown $VOLTTRON_USER.$VOLTTRON_USER /code && \
    echo "export PATH=/home/volttron/.local/bin:$PATH" > /home/volttron/.bashrc
#
############################################
# ENDING volttron_base stage
# Creating volttron_core stage
############################################
FROM volttron_base AS volttron_core
#
# copy over /core, i.e. the custom startup scripts for this image
RUN mkdir /startup $VOLTTRON_HOME && \
    chown $VOLTTRON_USER.$VOLTTRON_USER $VOLTTRON_HOME
COPY ./docker /startup
RUN chmod +x /startup/*
#
# copy over volttron repo
USER $VOLTTRON_USER
COPY --chown=volttron:volttron volttron /code/volttron
WORKDIR /code/volttron
RUN pip install -e . --user
RUN echo "package installed at `date`"

# copy default configs
COPY --chown=volttron:volttron ./platform_config.yml /platform_config.yml
COPY --chown=volttron:volttron ./Agents /code/volttron/Agents
COPY --chown=volttron:volttron ./docker /startup
COPY --chown=volttron:volttron ./libraries /home/volttron/.volttron/libraries
COPY --chown=volttron:volttron ./requirements.txt /requirements.txt
COPY --chown=volttron:volttron ./scripts/pre_install_agents.py /pre_install_agents.py
COPY --chown=volttron:volttron ./requirements.py /code/volttron/requirements.py
# COPY --chown=volttron:volttron ./site_configs /code/volttron/site_configs
# COPY --chown=volttron:volttron ./configs /home/volttron/configs
RUN pip3 install --user -r /requirements.txt
RUN python3 /startup/install_deps.py
##
#############################################
## RABBITMQ SPECIFIC INSTALLATION
#############################################
## the ARG install_rmq must be declared twice due to scope; see https://docs.docker.com/engine/reference/builder/#using-arg-variables
#USER root
#ARG install_rmq
#RUN if [ "${install_rmq}" = "false" ] ; then \
#      echo "Not installing RMQ dependencies.";  \
#    else \
#      ./scripts/rabbit_dependencies.sh $OS_TYPE $DIST && \
#      python -m pip install gevent-pika; \
#    fi
##
#USER $VOLTTRON_USER
#ARG install_rmq
#RUN if [ "${install_rmq}" = "false" ] ; then \
#      echo "Not installing RMQ"; \
#    else \
#      mkdir $RMQ_ROOT && \
#      set -eux && \
#      wget -P $VOLTTRON_USER_HOME https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.7.7/rabbitmq-server-generic-unix-3.7.7.tar.xz && \
#      tar -xf $VOLTTRON_USER_HOME/rabbitmq-server-generic-unix-3.7.7.tar.xz --directory $RMQ_ROOT && \
#      $RMQ_HOME/sbin/rabbitmq-plugins enable rabbitmq_management rabbitmq_federation rabbitmq_federation_management rabbitmq_shovel rabbitmq_shovel_management rabbitmq_auth_mechanism_ssl rabbitmq_trust_store;  \
#    fi
############################################
########################################
# The following lines should be run from any Dockerfile that
# is inheriting from this one as this will make the volttron
# run in the proper location.
#
# The user must be root at this point to allow gosu to work
########################################
USER root
RUN chmod +x /startup/*.sh
WORKDIR ${VOLTTRON_USER_HOME}
ENTRYPOINT ["/startup/entrypoint.sh"]
CMD ["/startup/bootstart.sh"]