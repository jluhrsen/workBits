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

# Install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Install Powerlevel10k theme
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k

# Install zsh plugins
RUN git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# Copy sanitized .zshrc
COPY --chown=$USER_NAME:$USER_NAME container-files/.zshrc /home/$USER_NAME/.zshrc

# Install golangci-lint - architecture-aware
ARG TARGETARCH
RUN GOARCH=${TARGETARCH} sh -c "curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.56.2"

# Install oc (OpenShift CLI) - architecture-aware, updated to 4.21
ARG TARGETARCH
ARG OC_VERSION=4.21.0
RUN curl -fsSL "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OC_VERSION}/openshift-client-linux-${TARGETARCH}-rhel9-${OC_VERSION}.tar.gz" -o oc.tar.gz && \
    tar -xzf oc.tar.gz -C /tmp && \
    sudo mv /tmp/oc /usr/local/bin/ && \
    sudo mv /tmp/kubectl /usr/local/bin/ && \
    rm oc.tar.gz

# Install gh CLI - architecture-aware
ARG TARGETARCH
RUN curl -fsSL "https://github.com/cli/cli/releases/download/v2.43.1/gh_2.43.1_linux_${TARGETARCH}.rpm" -o gh.rpm && \
    sudo dnf install -y ./gh.rpm && \
    rm gh.rpm && \
    sudo dnf clean all

# Install Python dependencies
USER root
RUN dnf install -y python3-pip && dnf clean all
USER $USER_NAME
RUN pip3 install --user pyyaml regex

# Copy session manager and continuum module
COPY --chown=$USER_NAME:$USER_NAME container-files/session_manager.py /home/$USER_NAME/session_manager.py
COPY --chown=$USER_NAME:$USER_NAME container-files/continuum.py /home/$USER_NAME/continuum.py
RUN chmod +x /home/$USER_NAME/session_manager.py

# Set up basic shell
ENV SHELL=/usr/bin/zsh
SHELL ["/usr/bin/zsh", "-c"]

# Set entrypoint
ENTRYPOINT ["python3", "/home/claude/session_manager.py"]
CMD ["--dangerously-skip-permissions"]
