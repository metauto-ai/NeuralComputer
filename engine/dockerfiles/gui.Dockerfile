FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    APT_OPTS="-o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Dpkg::Use-Pty=0"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# apt mirrors can intermittently fail (e.g. transient 502s); retry installs.
RUN set -eux; \
    printf '%s\n' \
    '#!/usr/bin/env bash' \
    'set -euo pipefail' \
    '' \
    'if [[ "$#" -eq 0 ]]; then' \
    '    echo "usage: apt-install-with-retry <packages...>" >&2' \
    '    exit 2' \
    'fi' \
    '' \
    'APT_OPTS=${APT_OPTS:-"-o Acquire::Retries=5 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 -o Dpkg::Use-Pty=0"}' \
    '' \
    'for attempt in 1 2 3 4 5; do' \
    '    if ! apt-get ${APT_OPTS} update; then' \
    '        if [[ "$attempt" -eq 5 ]]; then' \
    '            echo "apt-get update failed after ${attempt} attempts" >&2' \
    '            exit 1' \
    '        fi' \
    '        echo "apt-get update attempt ${attempt} failed; retrying in 5s..." >&2' \
    '        rm -rf /var/lib/apt/lists/*' \
    '        sleep 5' \
    '        continue' \
    '    fi' \
    '' \
    '    installable=()' \
    '    skipped=()' \
    '    for pkg in "$@"; do' \
    '        if apt-cache show "$pkg" >/dev/null 2>&1; then' \
    '            installable+=("$pkg")' \
    '        else' \
    '            skipped+=("$pkg")' \
    '        fi' \
    '    done' \
    '' \
    '    if (( ${#skipped[@]} > 0 )); then' \
    '        echo "Skipping unavailable packages: ${skipped[*]}" >&2' \
    '    fi' \
    '' \
    '    if (( ${#installable[@]} == 0 )); then' \
    '        echo "No installable packages remain after filtering." >&2' \
    '        rm -rf /var/lib/apt/lists/*' \
    '        exit 0' \
    '    fi' \
    '' \
    '    apt-get ${APT_OPTS} install -y --fix-broken || true' \
    '' \
    '    if apt-get ${APT_OPTS} install -y --no-install-recommends --fix-missing "${installable[@]}"; then' \
    '        rm -rf /var/lib/apt/lists/*' \
    '        exit 0' \
    '    fi' \
    '' \
    '    apt-get ${APT_OPTS} install -y --fix-broken || true' \
    '' \
    '    if [[ "$attempt" -eq 5 ]]; then' \
    '        echo "apt-get install failed after ${attempt} attempts: ${installable[*]}" >&2' \
    '        exit 1' \
    '    fi' \
    '' \
    '    echo "apt-get install attempt ${attempt} failed; retrying in 5s..." >&2' \
    '    rm -rf /var/lib/apt/lists/*' \
    '    sleep 5' \
    'done' \
    > /usr/local/bin/apt-install-with-retry; \
    chmod +x /usr/local/bin/apt-install-with-retry

RUN apt-install-with-retry \
    apt-transport-https \
    ca-certificates \
    curl \
    wget \
    gnupg \
    unzip \
    vim \
    nano \
    python3.11 \
    python3.11-dev \
    python3.11-tk \
    python3-pip \
    xvfb \
    x11vnc \
    scrot \
    xdotool \
    x11-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    ffmpeg \
    xfce4 xfce4-goodies xfce4-terminal \
    thunar \
    dbus-x11 \
    xserver-xorg \
    xinit \
    x11-xserver-utils \
    software-properties-common \
    mousepad \
    gnome-mines gnome-sudoku gnome-mahjongg aisleriot gnome-calculator mtpaint \
    git \
    imagemagick \
    # Theme packages
    xfce4-appfinder \
    xfce4-settings \
    gtk2-engines-murrine \
    gtk2-engines-pixbuf \
    gtk3-engines-breeze \
    adwaita-icon-theme \
    gnome-themes-extra \
    # Arc theme packages
    arc-theme \
    papirus-icon-theme \
    # Alternative theme packages if arc-theme not available
    gnome-themes-extra-data \
    ubuntu-mono \
    # Desktop applications and tools
    libreoffice \
    libreoffice-calc \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-draw \
    libreoffice-math \
    vlc \
    vlc-plugin-base \
    vlc-plugin-video-output \
    gimp \
    gimp-data \
    gimp-plugin-registry \
    thunderbird \
    nautilus \
    gnome-terminal \
    htop \
    speedtest-cli \
    x11-apps \
    fonts-liberation \
    fonts-noto \
    fonts-noto-cjk \
    fonts-dejavu \
    fonts-freefont-ttf \
    net-tools \
    libpopt0 \
    iputils-ping \
    traceroute \
    nmap \
    tree \
    # PDF tools
    poppler-utils \
    ghostscript \
    # Audio/video codecs
    libavcodec-extra \
    # Archive tools
    zip \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    # Document conversion
    pandoc \
    && if add-apt-repository -y ppa:mozillateam/ppa; then \
           apt-install-with-retry firefox-esr || echo "Skipping firefox-esr: install failed after retries" >&2; \
       else \
           echo "Skipping firefox-esr: unable to add ppa:mozillateam/ppa" >&2; \
       fi \
    && apt-get clean

# Install Chromium (open-source, supports both amd64 and arm64)
RUN apt-install-with-retry chromium-browser && \
    apt-get clean

# Keep scripts compatible even when firefox-esr is unavailable on arm64.
RUN if ! command -v firefox-esr >/dev/null 2>&1 && command -v chromium-browser >/dev/null 2>&1; then \
        ln -sf /usr/bin/chromium-browser /usr/bin/firefox-esr; \
    fi

# Add Microsoft VS Code repository and install Code editor
RUN install -d -m 0755 /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/packages.microsoft.gpg && \
    echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list && \
    apt-install-with-retry code && \
    apt-get clean

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install Miniconda for Python environment management
RUN arch="$(uname -m)" \
    && case "$arch" in \
        x86_64) miniconda_arch="x86_64" ;; \
        aarch64|arm64) miniconda_arch="aarch64" ;; \
        *) echo "Unsupported architecture for Miniconda: $arch" >&2; exit 1 ;; \
    esac \
    && wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${miniconda_arch}.sh" -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh
ENV PATH="/opt/conda/bin:$PATH"

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-install-with-retry nodejs \
    && apt-get clean

# Debug: Check if theme packages are installed
RUN echo "Checking theme packages..." && \
    ls -la /usr/share/themes/ | grep -i arc || echo "Arc theme not found" && \
    ls -la /usr/share/icons/ | grep -i papirus || echo "Papirus icons not found"

# Install noVNC (keep this for web access)
RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone --branch v0.12.0 https://github.com/novnc/websockify /opt/noVNC/utils/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html && \
    chmod +x /opt/noVNC/utils/novnc_proxy

# setup user (like data_collection but with computeruse user)
ENV USERNAME=computeruse
ENV HOME=/home/$USERNAME
RUN useradd -m -s /bin/bash -d $HOME $USERNAME
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER computeruse
WORKDIR $HOME

# Install Python requirements (simplified - like data_collection)
COPY --chown=$USERNAME:$USERNAME engine/gui/computer_use_agent/requirements_simple.txt $HOME/computer_use_agent/requirements_simple.txt
RUN pip3 install -r $HOME/computer_use_agent/requirements_simple.txt

# Install additional Python packages for data science tasks
RUN pip3 install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    jupyter \
    requests \
    beautifulsoup4 \
    lxml \
    openpyxl \
    xlrd \
    pillow \
    opencv-python \
    selenium \
    webdriver-manager \
    openpyxl \
    xlsxwriter \
    python-docx \
    PyPDF2 \
    reportlab

# setup desktop env & app
COPY --chown=$USERNAME:$USERNAME engine/gui/image/ $HOME
COPY --chown=$USERNAME:$USERNAME engine/gui/computer_use_agent/ $HOME/computer_use_agent/

# Set up virtual display (like data_collection)
ARG DISPLAY_NUM=1
ARG HEIGHT=768
ARG WIDTH=1024
ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH
ENV SCREEN_WIDTH=$WIDTH
ENV SCREEN_HEIGHT=$HEIGHT
ENV SCREEN_DEPTH=24

# Copy background image and icon configuration
COPY engine/gui/image/background.png /usr/share/backgrounds/xfce/
COPY engine/gui/image/icons.screen.latest.rc /usr/share/backgrounds/xfce/

# Copy start script
COPY --chown=computeruse:computeruse engine/gui/runtime/start.sh /home/computeruse/start.sh
RUN chmod +x /home/computeruse/start.sh

# Create desktop directory
RUN mkdir -p $HOME/Desktop

# Use the startup script
CMD [ "/home/computeruse/start.sh" ]
