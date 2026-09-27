"""Separate disabled-first route for linked durable HICBC composition."""

from flask import abort, current_app, g, jsonify, request

from reserved.auth import is_production_environment, require_auth
from reserved.config import linked_hicbc_annual_enabled
from reserved.database import get_user
from reserved.web.hicbc import hicbc


@hicbc.get("/linked-current-annual-position")
@require_auth
def linked_current_annual_position():
    """Return only the signed-in user's bounded linked-source consequence."""
    if (is_production_environment() or not linked_hicbc_annual_enabled()
            or request.args or request.content_length not in (None, 0)):
        abort(404)
    from reserved.hicbc_linked_endpoint import (
        LinkedHicbcRuntime,
        linked_current_annual_position_payload,
    )
    try:
        runtime = current_app.extensions.get("reserved.hicbc.linked_annual_endpoint")
        if type(runtime) is not LinkedHicbcRuntime:
            raise ValueError
        if type(g.user_id) is not int or g.user_id <= 0 or get_user(g.user_id) is None:
            raise ValueError
        payload = linked_current_annual_position_payload(runtime, g.user_id)
    except Exception:
        # A fixed 404 is used for every missing/invalid runtime dependency. Once
        # admitted, all link/source insufficiency is the same fixed null result.
        abort(404)
    return jsonify(payload)
