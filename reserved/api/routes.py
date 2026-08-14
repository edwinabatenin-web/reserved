import logging

from flask import Blueprint, jsonify

from reserved.database import ping_db

log = logging.getLogger(__name__)

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    """
    Liveness + readiness probe.

    Returns HTTP 200 when the application is up and the database is reachable.
    Returns HTTP 503 when the database cannot be queried, so load-balancers /
    container orchestrators can restart or drain the instance automatically.
    """
    db_ok = ping_db()
    if not db_ok:
        log.error("Health check: database unreachable")

    payload = {
        "status":  "ok" if db_ok else "degraded",
        "service": "reserved",
        "db":      "ok" if db_ok else "error",
    }
    return jsonify(payload), (200 if db_ok else 503)
