ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEIMWMS_DATA_DIR=/data

# HA base images are Alpine-based; install Python + libs for reportlab/pillow.
RUN apk add --no-cache \
      python3 \
      py3-pip \
      jpeg \
      zlib \
      freetype

WORKDIR /app

COPY requirements.txt .
RUN apk add --no-cache --virtual .build-deps \
      gcc musl-dev python3-dev jpeg-dev zlib-dev freetype-dev \
  && pip3 install --no-cache-dir --break-system-packages -r requirements.txt \
  && apk del .build-deps

COPY app ./app
COPY scripts ./scripts
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
