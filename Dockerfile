# Build basic python-alpine image
FROM python:3.12-alpine as base
LABEL maintainer="noirpi@noircoding.de"

WORKDIR /svc
COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

# Setup final Image
FROM python:3.12-alpine
# Copy all pip packages to the new image!
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Setup Environment Variables
ENV TZ="Europe/Berlin"
ENV LANG="en_US.UTF-8"
ENV LC_ALL="en_US.UTF-8"
ENV TOKEN=""

# Sync Timezone with Host and start Image
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# Set working directory
WORKDIR /bot

# Copy project files into image
COPY . .

# Permission setup
RUN chown 1000:1000 /bot -R

# Set to non-root user
USER 1000:1000

#Start Image
#ENTRYPOINT [ "tail", "-f", "/dev/null" ]
ENTRYPOINT ["python3", "rampage.py"]
