"""Pure W9-S3D current-session owner binding for the W9-S3C adapter.

The adapter reads only Reserved's already-authenticated, signed-session
``users.id`` boundary, converts that exact positive integer through the
accepted canonical owner mapper, and supplies it to W9-S3C.  It neither
authenticates a token nor queries business ownership.  The caller must supply
an already-authorised business reference, which W9-S3C binds exactly to the
admitted projection.  Every returned operation remains detached and grants no
persistence or production authority.
"""

from __future__ import annotations

import types as _types
from datetime import date as _date

import reserved.auth as _auth
import reserved.annual_position_projection_repository_adapter as _s3c
import reserved.billing.event_inbox_contract as _owner_contract


ADAPTER_VERSION = "reserved-annual-position-authenticated-owner-adapter/1.0"
AUTHORITY_STATUS = (
    "current_signed_session_users_id_snapshot_bound_business_membership_external"
)
SOURCE_S3C_COMMIT = "c9bdaa6538d68c0c64b2dcde97f224a69c089d30"
SOURCE_S3C_INTEGRATION_COMMIT = "5f5a948891e1e812a5c74ff6c7266d153bb492fa"
SOURCE_S3C_SHA256 = "052712341ab06ca1cdabd407bfacc1ee4cd1603ba3c49f7fc95575465311d9dd"
SOURCE_AUTH_COMMIT = "dd08b48f8dbc735c42a6fc832f5b6a12d95e48bb"
SOURCE_AUTH_SHA256 = "adfe50a348a94e1f1a7405a41d92ec39b5d1a9db8c92b64222410701af39ae91"
SOURCE_OWNER_MAPPER_COMMIT = "5bc29bcb30c95ea7a5a9430104653b366d709eb6"
SOURCE_OWNER_MAPPER_SHA256 = (
    "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed"
)


class AuthenticatedOwnerAdapterError(ValueError):
    """Fail-closed W9-S3D runtime-owner boundary error."""


def _build_adapter():
    typ, length, id_fn, zip_fn = type, len, id, zip
    T, S, I, D, L = tuple, str, int, dict, list
    any_fn, set_type = any, set
    function_type = _types.FunctionType
    date_type = _date
    type_error, value_error, exception_type = TypeError, ValueError, Exception
    error = AuthenticatedOwnerAdapterError

    session_proxy = _auth.session
    session_user_id_key = _auth._SK_USER_ID
    auth_namespace = _auth.__dict__
    if typ(session_user_id_key) is not S or session_user_id_key != "_v2_user_id":
        raise RuntimeError("Reserved authentication owner key is inconsistent")
    canonical_owner = _owner_contract.canonical_owner_id_from_users_id
    adapt_s3c = _s3c.adapt_admitted_projection_to_structural_candidate
    validate_s3c = _s3c.validate_projection_repository_adapter_operation

    expected_s3c_version = "reserved-annual-position-projection-repository-adapter/1.0"
    if (
        typ(_s3c.ADAPTER_VERSION) is not S
        or _s3c.ADAPTER_VERSION != expected_s3c_version
        or typ(_s3c.SOURCE_S3A_COMMIT) is not S
        or _s3c.SOURCE_S3A_COMMIT != "c489c25bab669c64e1c11d28caf29fcde9678fdd"
        or typ(_s3c.SOURCE_S3B_COMMIT) is not S
        or _s3c.SOURCE_S3B_COMMIT != "110a90043dfc770c70059482be9d7b7e237749a6"
    ):
        raise RuntimeError("W9-S3C source boundary does not match W9-S3D")

    input_fields = (
        "projection",
        "authenticated_business_reference",
        "evaluated_on",
        "previous_projection",
        "previous_structural_candidate",
    )

    def snapshot(functions):
        seen, stack, rows = set_type(), L(functions), []
        while stack:
            fn = stack.pop()
            if typ(fn) is not function_type:
                raise RuntimeError("W9-S3D dependency is not an exact function")
            if id_fn(fn) in seen:
                continue
            seen.add(id_fn(fn))
            contents = []
            for cell in fn.__closure__ or ():
                try:
                    value = cell.cell_contents
                except value_error:
                    value = cell
                contents.append((cell, value))
                if typ(value) is function_type:
                    stack.append(value)
            rows.append(
                (fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__, T(contents))
            )
        return T(rows)

    dependency_snapshot = snapshot(
        (canonical_owner, adapt_s3c, validate_s3c)
    )

    def require_dependencies():
        for fn, code, defaults, kwdefaults, contents in dependency_snapshot:
            if (
                typ(fn) is not function_type
                or fn.__code__ is not code
                or fn.__defaults__ is not defaults
                or fn.__kwdefaults__ is not kwdefaults
            ):
                raise error("captured W9-S3D dependency was altered")
            cells = fn.__closure__ or ()
            if length(cells) != length(contents):
                raise error("captured W9-S3D dependency closure was altered")
            for cell, (expected_cell, expected_value) in zip_fn(
                cells, contents, strict=True
            ):
                if cell is not expected_cell:
                    raise error("captured W9-S3D dependency closure was replaced")
                try:
                    value = cell.cell_contents
                except value_error:
                    value = cell
                if value is not expected_value:
                    raise error("captured W9-S3D dependency closure state was altered")
        if (
            auth_namespace.get("session") is not session_proxy
            or auth_namespace.get("_SK_USER_ID") != session_user_id_key
            or typ(auth_namespace.get("_SK_USER_ID")) is not S
        ):
            raise error("captured authentication session boundary was altered")

    def adapt_authenticated_owner_projection(*args, **kwargs):
        if args or typ(kwargs) is not D or length(kwargs) != length(input_fields):
            raise type_error("W9-S3D inputs must use the exact named call shape")
        if (
            any_fn(typ(key) is not S for key in kwargs)
            or set_type(kwargs) != set_type(input_fields)
        ):
            raise type_error("W9-S3D inputs must use the exact named call shape")

        require_dependencies()
        try:
            # One request-local lookup is the complete owner snapshot.  A
            # second authentication/current-user read could observe a changed
            # backend and produce a split identity decision.
            runtime_user_id = session_proxy.get(session_user_id_key)
        except exception_type:
            raise error("current signed-session owner snapshot is unavailable") from None
        if typ(runtime_user_id) is not I or runtime_user_id <= 0:
            raise error("authenticated runtime owner must be an exact positive users.id")

        business_reference = kwargs["authenticated_business_reference"]
        if typ(business_reference) is not S:
            raise error("authenticated business reference must be an exact string")
        evaluated_on = kwargs["evaluated_on"]
        if typ(evaluated_on) is not date_type:
            raise error("evaluation date must be an exact date")

        try:
            owner_reference = canonical_owner(runtime_user_id)
            operation = adapt_s3c(
                projection=kwargs["projection"],
                authenticated_user_id=owner_reference,
                authenticated_business_id=business_reference,
                evaluated_on=evaluated_on,
                previous_projection=kwargs["previous_projection"],
                previous_structural_candidate=kwargs[
                    "previous_structural_candidate"
                ],
            )
            validated = validate_s3c(operation)
        except (type_error, value_error) as exc:
            raise error("authenticated owner projection binding failed closed") from exc

        mapped = D(validated)
        if (
            typ(mapped.get("authenticated_user_id")) is not S
            or mapped["authenticated_user_id"] != owner_reference
            or typ(mapped.get("authenticated_business_id")) is not S
            or mapped["authenticated_business_id"] != business_reference
        ):
            raise error("authenticated owner binding changed during validation")
        require_dependencies()
        return validated

    return adapt_authenticated_owner_projection


adapt_authenticated_owner_projection = _build_adapter()
del _build_adapter


__all__ = [
    "ADAPTER_VERSION",
    "AUTHORITY_STATUS",
    "SOURCE_S3C_COMMIT",
    "SOURCE_S3C_INTEGRATION_COMMIT",
    "SOURCE_S3C_SHA256",
    "SOURCE_AUTH_COMMIT",
    "SOURCE_AUTH_SHA256",
    "SOURCE_OWNER_MAPPER_COMMIT",
    "SOURCE_OWNER_MAPPER_SHA256",
    "AuthenticatedOwnerAdapterError",
    "adapt_authenticated_owner_projection",
]
