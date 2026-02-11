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
    useradd --uid $USER_UID --gid $USER_GID -m $USER_NAME

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
    && dnf clean all

# Install Node.js (required for Claude Code CLI)
RUN curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - && \
    dnf install -y nodejs && \
    dnf clean all

# Install Claude Code CLI globally (before switching to non-root user)
RUN npm install -g @anthropic-ai/claude-code

# Switch to non-root user
USER $USER_NAME
WORKDIR /home/$USER_NAME

# Set up basic shell
ENV SHELL=/usr/bin/zsh
SHELL ["/usr/bin/zsh", "-c"]

CMD ["/usr/bin/zsh"]
