# Dockerfile for development environment

# Use a base image with Python already installed
FROM python:3.10-slim

# Install pip if it's not already installed, and other packages as needed
RUN python -m ensurepip --default-pip
RUN pip install --upgrade pip
RUN pip install pdm
RUN pip install --upgrade build twine ruff
RUN pip install GitPython
RUN pip install pytest

# Install git
RUN apt-get -y update
RUN apt-get -y install git

# Install curl and tree
RUN apt-get -y install curl
RUN apt-get -y install tree

# Add .local/bin to PATH
ENV PATH=/home/developer/.local/bin:$PATH

# Set the working directory
WORKDIR /workspace/modal_or_local

# Install the Python dependencies listed in the requirements.txt file  
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create the developer user
RUN useradd -s /bin/bash -m developer
USER developer