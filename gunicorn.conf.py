"""
Gunicorn configuration for Spike Sorting Lab Hub.

SSL/TLS is passed directly on the command line — Gunicorn handles the
handshake itself with no reverse proxy needed.

Usage:
    HTTP:   gunicorn -c gunicorn.conf.py labhub.wsgi:application
    HTTPS:  gunicorn -c gunicorn.conf.py --certfile=cert.crt --keyfile=cert.key -b 0.0.0.0:9443 labhub.wsgi:application

On Linux, binding to port 443 requires one of:
    sudo gunicorn ...
    sudo setcap 'cap_net_bind_service=+ep' $(which gunicorn)   # one-time, no sudo needed after
"""

import multiprocessing

# -----------------------------------------------------------------------------
# Server socket  (overridden by -b on the command line when using HTTPS)
# -----------------------------------------------------------------------------
bind = "0.0.0.0:9000"
backlog = 2048

# -----------------------------------------------------------------------------
# SSL / TLS
# Cert files are NOT set here — pass --certfile and --keyfile on the CLI.
# This keeps HTTP and HTTPS launch commands explicit and avoids accidental
# SSL mode when you only want plain HTTP dev mode.
#
# TLS hardening applied when Gunicorn detects --certfile is present:
# -----------------------------------------------------------------------------
# Gunicorn 25+ uses ssl_context instead of the deprecated ssl_version/ciphers settings.
# ssl_context is a callable that returns a configured ssl.SSLContext.
# This enforces TLS 1.2+, forward-secret ciphers, and completes the handshake
# before handing the connection to a worker process.
import ssl as _ssl

def ssl_context(conf, default_ssl_context_factory):
    ctx = default_ssl_context_factory()                  # starts with Gunicorn's defaults
    ctx.minimum_version = _ssl.TLSVersion.TLSv1_2        # reject TLS 1.0 and 1.1
    ctx.set_ciphers(
        "ECDHE-ECDSA-AES256-GCM-SHA384:"
        "ECDHE-RSA-AES256-GCM-SHA384:"
        "ECDHE-ECDSA-CHACHA20-POLY1305:"
        "ECDHE-RSA-CHACHA20-POLY1305:"
        "ECDHE-ECDSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES128-GCM-SHA256"
    )
    return ctx

do_handshake_on_connect = True   # complete TLS handshake before worker receives request

# -----------------------------------------------------------------------------
# Worker processes
# -----------------------------------------------------------------------------
# (2 × CPU cores) + 1 is the standard rule for I/O-bound apps (Django waits
# on DB queries, not CPU), so more workers = more concurrent requests handled.
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"      # sync is correct for SQLite; switch to "gevent" for async I/O
worker_connections = 1000  # only used by async worker classes
timeout = 30               # kill a worker that hangs longer than 30 s
keepalive = 5              # seconds to hold an idle keep-alive connection open
graceful_timeout = 30      # time given to finish in-flight requests on shutdown

# -----------------------------------------------------------------------------
# Logging  (stdout/stderr — captured by systemd, Docker, or your terminal)
# -----------------------------------------------------------------------------
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
capture_output = True   # forward worker stdout/stderr into the error log

# -----------------------------------------------------------------------------
# Process naming & request limits
# -----------------------------------------------------------------------------
proc_name = "labhub-gunicorn"
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
