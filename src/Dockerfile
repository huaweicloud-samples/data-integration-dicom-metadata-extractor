###################################################################################################
#
# Multi-stage Docker build for CCE batch processing of DICOM archives.
# Uses Python 3.9 slim base image with pydicom and OBS SDK.
#
###################################################################################################

# Define build arguments
ARG CODE_DIR="/app"
ARG UNAME=dicom
ARG UID=1010
ARG GID=1010

FROM python:3.9-slim AS build-image

# Install build dependencies
RUN apt-get update && \
    apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Include Global Args in this stage
ARG CODE_DIR

# Create app directory
RUN mkdir -p ${CODE_DIR}

# Copy code to directory
COPY src/ ${CODE_DIR}

# Install libraries from requirements.txt file
RUN pip install \
    --target ${CODE_DIR} \
    -r ${CODE_DIR}/requirements.txt

# Multi-stage build: final runtime image
FROM python:3.9-slim

# Include Global Args in this stage
ARG CODE_DIR UID GID UNAME

# Set working directory to function app directory
WORKDIR ${CODE_DIR}

# Create Group and User to run code
RUN groupadd -g $GID -o $UNAME && useradd -m -u $UID -g $GID -o -s /bin/sh $UNAME
USER $UNAME:$UNAME

# Copy code and dependencies from previous stage
COPY --from=build-image ${CODE_DIR} ${CODE_DIR}

# Entrypoint: run app.py directly for CCE batch processing
# The container receives environment variables (OBS_BUCKET, OBS_KEY, etc.)
# and processes the DICOM archive file
ENTRYPOINT ["python3", "app.py"]
