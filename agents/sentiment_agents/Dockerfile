FROM amazonlinux:2023
ARG TARGETARCH
ENV TARGETARCH=${TARGETARCH}

# Install Python 3.12, pip and basic build tools
RUN dnf -y update && \
    dnf -y install \
      python3.12 \
      python3.12-pip \
      python3.12-devel \
      gcc \
      gcc-c++ \
      make \
      shadow-utils \
      tar \
      gzip \
      xz && \
    dnf clean all

# Use python3.12 explicitly and add convenience symlinks
RUN ln -sf /usr/bin/python3.12 /usr/bin/python && \
    ln -sf /usr/bin/pip3.12 /usr/bin/pip && \
    python3.12 -m pip install --upgrade pip

# Install system dependencies for Playwright (Amazon Linux 2023 uses dnf)
RUN dnf -y install \
      alsa-lib \
      atk \
      cups-libs \
      gtk3 \
      ipa-gothic-fonts \
      libXcomposite \
      libXcursor \
      libXdamage \
      libXext \
      libXi \
      libXrandr \
      libXScrnSaver \
      libXtst \
      pango \
      xorg-x11-fonts-100dpi \
      xorg-x11-fonts-75dpi \
      xorg-x11-fonts-cyrillic \
      xorg-x11-fonts-Type1 \
      xorg-x11-utils \
    && dnf clean all

# Install ffmpeg for video processing (static build; auto-detect arch)
RUN set -eux; \
    if [ "${TARGETARCH}" = "arm64" ] || [ "${TARGETARCH}" = "aarch64" ]; then \
      FFARCH="arm64"; \
    else \
      FFARCH="amd64"; \
    fi; \
    curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFARCH}-static.tar.xz" -o /tmp/ffmpeg.tar.xz; \
    mkdir -p /opt/ffmpeg && tar -xJf /tmp/ffmpeg.tar.xz -C /opt/ffmpeg --strip-components=1; \
    mv /opt/ffmpeg/ffmpeg /usr/local/bin/ffmpeg && \
    mv /opt/ffmpeg/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/ffmpeg.tar.xz /opt/ffmpeg

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

# Install AWS Lambda Runtime Interface Client
RUN python3.12 -m pip install --no-cache-dir awslambdaric

# Playwright deps on Amazon Linux (no apt here)
RUN dnf -y install \
      at-spi2-atk \
      dbus-libs \
      glib2 \
      libX11 \
      libxcb \
      libXcomposite \
      libXdamage \
      libXext \
      libXfixes \
      libXi \
      libXrandr \
      libxshmfence \
      libdrm \
      mesa-libgbm \
      nss \
    && dnf clean all
RUN python3.12 -m playwright install chromium

# Add AWS Lambda Runtime Interface Emulator (for local testing)
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/local/bin/aws-lambda-rie
RUN chmod +x /usr/local/bin/aws-lambda-rie

# Copy source code
COPY sentiment_final.py query_builder.py websearch.py \
     video_ingestion.py tiktok_discovery.py text_content.py \
     sentiment_agent.py lambda_function.py ./


# Lambda handler
CMD [ "python3.12", "-m", "awslambdaric", "lambda_function.handler" ]