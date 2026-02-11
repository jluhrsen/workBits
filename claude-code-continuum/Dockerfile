# Claude Code Continuum
# Containerized Claude Code environment with cross-machine session continuity

FROM registry.access.redhat.com/ubi9/ubi:latest

LABEL maintainer="jluhrsen"
LABEL description="Claude Code Continuum - pause anywhere, resume everywhere"
LABEL version="0.1.0"

# Create non-root user
ARG USER_NAME=claude
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USER_NAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USER_NAME && \
    echo "$USER_NAME ALL=(ALL) NOPASSWD: /usr/bin/dnf, /usr/bin/mv, /usr/bin/tee" >> /etc/sudoers

# Install system packages
RUN dnf install -y --allowerasing \
    git \
    vim \
    zsh \
    curl \
    wget \
    make \
    gcc \
    gcc-c++ \
    tar \
    gzip \
    unzip \
    sudo \
    && dnf clean all

# Install Node.js (required for Claude Code CLI)
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    dnf clean all

# Install Claude Code CLI globally (before switching to non-root user)
RUN npm install -g @anthropic-ai/claude-code

# Install Go (latest stable)
ARG GO_VERSION=1.22.0
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o go.tar.gz && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/home/${USER_NAME}/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Switch to non-root user
USER $USER_NAME
WORKDIR /home/$USER_NAME

# Install golangci-lint
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.56.2

# Install oc (OpenShift CLI)
RUN curl -fsSL "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/4.15.2/openshift-client-linux.tar.gz" -o oc.tar.gz && \
    tar -xzf oc.tar.gz -C /tmp && \
    sudo mv /tmp/oc /usr/local/bin/ && \
    sudo mv /tmp/kubectl /usr/local/bin/ && \
    rm oc.tar.gz

# Install gh CLI
RUN curl -fsSL "https://github.com/cli/cli/releases/download/v2.43.1/gh_2.43.1_linux_amd64.rpm" -o gh.rpm && \
    sudo dnf install -y ./gh.rpm && \
    rm gh.rpm && \
    sudo dnf clean all

# Set up basic shell
ENV SHELL=/usr/bin/zsh
SHELL ["/usr/bin/zsh", "-c"]

CMD ["/usr/bin/zsh"]
