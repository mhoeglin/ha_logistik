ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEIMWMS_DATA_DIR=/data

WORKDIR /app

# Debian (glibc) base: reportlab, pillow, uvicorn ship manylinux wheels,
# so no compiler/toolchain is required.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
