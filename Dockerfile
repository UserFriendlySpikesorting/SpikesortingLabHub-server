# ============================================================
# SpikesortingLabHub — Production Image
#
# Self-contained: downloads the repo from GitHub so anyone can
# reproduce this image without needing the local source tree.
# ============================================================

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------
# 1. System packages
# ------------------------------------------------------------
RUN apt-get update && apt-get upgrade -y --no-install-recommends
RUN apt-get install -y --no-install-recommends \
        python3 \
        python3-venv \
        python3-pip \
        build-essential \
        libpq-dev \
        openssl \
        ca-certificates \
        curl \
        git \
        nodejs \
        npm \
        wget \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# 2. Download repository (docker branch) and unpack
# ------------------------------------------------------------
WORKDIR /app
RUN wget -q https://github.com/UserFriendlySpikesorting/SpikesortingLabHub-server/archive/refs/heads/developing_branch.zip \
    && unzip -q developing_branch.zip \
    && mv SpikesortingLabHub-server-developing_branch/* . \
    && rm -rf developing_branch.zip SpikesortingLabHub-server-developing_branch

# ------------------------------------------------------------
# 3. Set up Python virtual environment and install requirements
# ------------------------------------------------------------
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Install SpikesortingLabHub-CLI (patch setup.py for Python 3.12)
RUN wget https://github.com/UserFriendlySpikesorting/SpikesortingLabHub-CLI/archive/refs/heads/main.zip \
    && unzip main.zip \
    && sed -i 's|3.13|3.12|' SpikesortingLabHub-CLI-main/setup.py \
    && /app/venv/bin/pip install --no-cache-dir SpikesortingLabHub-CLI-main/

ENV PATH="/app/venv/bin:$PATH"

# ------------------------------------------------------------
# 4. Build the React frontend
#    my-app/build/ is gitignored so it must be compiled here.
# ------------------------------------------------------------
RUN cd my-app && npm ci --omit=dev && npm run build

# ------------------------------------------------------------
# 5. Placeholder directories for bind mounts
#    Docker Compose overlays the real host paths at runtime.
#    /data        ← trurnasdata (read-only NAS database)
#    /django_db   ← persistentdata (Django SQLite DB + logs)
#    /experiments ← binary recording files (read-only)
# ------------------------------------------------------------
RUN mkdir -p /data /app/django_db /app/experiments /app/secrets

# ------------------------------------------------------------
# 6. Entrypoint — already in the repo after download.
#    Runs pre-flight checks, collectstatic, migrate, then Gunicorn.
# ------------------------------------------------------------
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# ------------------------------------------------------------
# 7. Expose ports
#    9000 — plain HTTP
#    9443 — HTTPS (Gunicorn with --certfile / --keyfile)
# ------------------------------------------------------------
EXPOSE 9000 9443

# ------------------------------------------------------------
# 8. Default command — passed to entrypoint.sh via exec "$@".
# ------------------------------------------------------------
CMD ["gunicorn", "-c", "gunicorn.conf.py", "labhub.wsgi:application"]
