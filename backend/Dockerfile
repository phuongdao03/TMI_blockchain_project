FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip wheel --wheel-dir /wheels .


FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS poster-builder

# Build only the codecs and filters needed to read a retained video and emit
# one JPEG. The distro package pulls in unrelated GUI/audio codec dependencies.
RUN apk add --no-cache build-base nasm curl xz
WORKDIR /build/ffmpeg
RUN curl --fail --show-error --location --retry 3 \
        https://ffmpeg.org/releases/ffmpeg-8.0.3.tar.xz -o source.tar.xz \
    && echo '6136812ea6d4e68bdba27e33c2a94382711cdf4f8602ffef056ff792bd6f9818  source.tar.xz' | sha256sum -c - \
    && tar -xJf source.tar.xz --strip-components=1 \
    && ./configure \
        --prefix=/opt/poster \
        --disable-autodetect --disable-everything \
        --disable-network --disable-doc --disable-debug --disable-ffprobe \
        --disable-shared --enable-static --enable-small \
        --extra-ldflags=-static \
        --enable-protocol=file,pipe \
        --enable-demuxer=mov,matroska,avi \
        --enable-indev=lavfi \
        --enable-decoder=h264,hevc,vp8,vp9,mjpeg,mpeg4,wrapped_avframe \
        --enable-parser=h264,hevc,vp8,vp9,mpeg4video \
        --enable-encoder=mjpeg,mpeg4 \
        --enable-muxer=image2pipe,avi \
        --enable-filter=scale,format,color \
    && make -j2 \
    && make install \
    && test "$(wc -c < /opt/poster/bin/ffmpeg)" -lt 20971520

# Exercise the actual retained-video poster arguments at image build time.
RUN /opt/poster/bin/ffmpeg -nostdin -v error \
        -f lavfi -i color=c=red:s=32x32:d=1 -c:v mpeg4 /tmp/poster-source.avi \
    && /opt/poster/bin/ffmpeg -nostdin -v error -threads 1 \
        -max_alloc 67108864 -protocol_whitelist file,pipe \
        -format_whitelist mov,matroska,webm,avi \
        -i /tmp/poster-source.avi -map 0:v:0 -frames:v 1 \
        -vf scale=960:540:force_original_aspect_ratio=decrease \
        -an -sn -dn -threads 1 -f image2pipe -c:v mjpeg /tmp/poster.jpg \
    && test -s /tmp/poster.jpg


FROM python:3.12.13-alpine3.24@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/app/.local/bin:$PATH

RUN apk upgrade --no-cache \
    && addgroup -g 10001 -S app \
    && adduser -u 10001 -S -D -G app app

WORKDIR /app

COPY --from=poster-builder /opt/poster/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=poster-builder /build/ffmpeg/COPYING.LGPLv2.1 /usr/local/share/licenses/ffmpeg/COPYING.LGPLv2.1
RUN ffmpeg -version

COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-compile /wheels/*.whl \
    && rm -rf /wheels \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip* \
        /usr/local/bin/pip*

COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
