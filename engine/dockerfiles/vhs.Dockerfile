FROM tsl0922/ttyd:alpine AS ttyd
FROM alpine:latest AS fontcollector

# Install extended font set used during recordings.
# Edge repositories can intermittently time out; retry to avoid flaky builds.
RUN set -eux; \
    for attempt in 1 2 3 4 5; do \
        apk add --no-cache \
            --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
            --repository=https://dl-cdn.alpinelinux.org/alpine/edge/community \
            --repository=https://dl-cdn.alpinelinux.org/alpine/edge/testing \
            font-adobe-source-code-pro font-source-code-pro-nerd \
            font-dejavu font-dejavu-sans-mono-nerd \
            font-fira-code font-fira-code-nerd \
            font-hack font-hack-nerd \
            font-ibm-plex-mono-nerd \
            font-inconsolata font-inconsolata-nerd \
            font-jetbrains-mono font-jetbrains-mono-nerd \
            font-liberation font-liberation-mono-nerd \
            font-noto \
            font-roboto-mono \
            font-ubuntu-mono-nerd \
            font-noto-emoji && break; \
        if [ "$attempt" -eq 5 ]; then \
            echo "apk add failed after ${attempt} attempts" >&2; \
            exit 1; \
        fi; \
        echo "apk add attempt ${attempt} failed; retrying in 5s..." >&2; \
        sleep 5; \
    done

FROM debian:stable-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    HOSTNAME=NeuralComputer

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Core packages + tooling carried over from the previous Ubuntu image.
# This install set is large and can fail on transient mirror/network issues.
RUN set -eux; \
    APT_OPTS="-o Acquire::Retries=2 -o Acquire::http::Timeout=20 -o Acquire::https::Timeout=20 -o Acquire::ForceIPv4=true -o Dpkg::Use-Pty=0"; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    for attempt in 1 2 3; do \
        apt-get ${APT_OPTS} update && \
        apt-get ${APT_OPTS} install -y --no-install-recommends \
        bash \
        bc \
        ca-certificates \
        chromium \
        coreutils \
        curl \
        wget \
        zip \
        xz-utils \
        bzip2 \
        grep \
        ffmpeg \
        findutils \
        fonts-dejavu \
        fonts-firacode \
        fontconfig \
        git \
        gnupg \
        htop \
        iproute2 \
        iputils-ping \
        hostname \
        less \
        locales \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libcups2 \
        libdrm2 \
        libgdk-pixbuf-2.0-0 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxrender1 \
        libxss1 \
        libxtst6 \
        man-db \
        make \
        build-essential \
        pkg-config \
        cmake \
        clang \
        gdb \
        lldb \
        nano \
        net-tools \
        netcat-openbsd \
        socat \
        dnsutils \
        traceroute \
        nodejs \
        npm \
        sysstat \
        procps \
        python3 \
        python3-pip \
        python3-venv \
        python-is-python3 \
        sqlite3 \
        tar \
        tree \
        unzip \
        util-linux \
        vim \
        jq \
        ripgrep \
        parallel \
        tmux \
        screen \
        zsh \
        fish \
        silversearcher-ag \
        fd-find \
        bat \
        moreutils \
        fzf \
        figlet \
        toilet \
        cmatrix \
        bsdmainutils \
        lm-sensors \
        && rm -rf /var/lib/apt/lists/* && break; \
        if [ "$attempt" -eq 3 ]; then \
            echo "apt-get install failed after ${attempt} attempts" >&2; \
            exit 1; \
        fi; \
        echo "apt-get attempt ${attempt} failed; retrying in 5s..." >&2; \
        rm -rf /var/lib/apt/lists/*; \
        sleep 5; \
    done

# Bring in pre-collected fonts and ttyd binary
COPY --from=fontcollector /usr/share/fonts/ /usr/share/fonts
COPY engine/cli/vhs/docker/fonts/ /usr/local/share/fonts/custom/
RUN fc-cache -f
COPY --from=ttyd /usr/bin/ttyd /usr/bin/ttyd

RUN sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANGUAGE=en_US:en

VOLUME /neuralcomputer

# Install VHS directly inside the image
ARG VHS_VERSION=0.10.0
RUN curl -fsSL \
        "https://github.com/charmbracelet/vhs/releases/download/v${VHS_VERSION}/vhs_${VHS_VERSION}_Linux_x86_64.tar.gz" \
        -o /tmp/vhs.tar.gz && \
    tar -xzf /tmp/vhs.tar.gz \
        -C /usr/local/bin \
        --strip-components=1 \
        "vhs_${VHS_VERSION}_Linux_x86_64/vhs" && \
    rm /tmp/vhs.tar.gz

RUN ln -sf /usr/bin/python3 /usr/local/bin/python

COPY engine/cli/vhs/docker/init_tmp_assets.py /tmp/init_tmp_assets.py
RUN python3 /tmp/init_tmp_assets.py && rm /tmp/init_tmp_assets.py

# Create an unprivileged user for running captures
ARG USERNAME=NeuralComputer
ARG USER_UID=1976
ARG USER_GID=1976
RUN addgroup --gid "${USER_GID}" --force-badname "${USERNAME}" && \
    adduser --uid "${USER_UID}" --home "/home/${USERNAME}" --shell /bin/bash \
        --disabled-password --gecos "" --ingroup "${USERNAME}" --force-badname "${USERNAME}"

RUN mkdir -p /workspace /outputs /neuralcomputer && \
    chown -R "${USERNAME}":"${USERNAME}" /workspace /outputs /neuralcomputer && \
    echo "NeuralComputer" > /etc/hostname

ENV USER=${USERNAME}
ENV PATH=/home/${USERNAME}/.local/bin:${PATH}
ENV VHS_OUTPUT_DIR=/outputs
ENV ROD_CHROMIUM_BIN=/usr/bin/chromium
ENV VHS_PORT=1976
ENV VHS_HOST=0.0.0.0
ENV VHS_GID=${USER_GID}
ENV VHS_UID=${USER_UID}
ENV VHS_KEY_PATH=/neuralcomputer/ssh_key
ENV VHS_AUTHORIZED_KEYS_PATH=
ENV VHS_NO_SANDBOX=true

WORKDIR /workspace
USER ${USERNAME}

CMD ["/bin/bash"]
