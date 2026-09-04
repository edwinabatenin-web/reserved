"""Offline Stripe-format raw-body HMAC check; no event or access admission.

True proves only a match to an explicitly supplied key at the supplied trusted
time. No key custody, JSON parsing, provider identity, replay database, endpoint
or entitlement is established. Inputs are not retained or echoed. Python does
not promise secure memory erasure or protection against hostile in-process code.
"""
import hmac
import re


# Conservative engineering caps, not Stripe provider limits.
MAX_BODY_BYTES = 1_048_576
MAX_HEADER_CHARS = 4096
MAX_HEADER_PARTS = 32
MAX_V1_SIGNATURES = 8
MAX_KEYS = 3
MAX_KEY_BYTES = 512
MAX_TIMESTAMP = 9_999_999_999_999_999
FRESHNESS_SECONDS = 300
_TIMESTAMP = re.compile(r"[0-9]{1,16}\Z")
_SIGNATURE = re.compile(r"[0-9a-fA-F]{64}\Z")


def verify_stripe_signature(raw_body, signature_header, signing_keys, *, now):
    """Return a plain bool for this call, never an authority-bearing handle.

    Body: exact bytes; header: exact printable-ASCII str; keys: exact tuple of
    1..3 nonempty exact bytes; now: exact nonnegative integer Unix seconds.
    Timestamp age must be 0..300 inclusive; any future timestamp is rejected.
    Leading timestamp zeros are allowed but signed exactly as received.
    Invalid input returns only False, with no diagnostics containing inputs.
    """
    if (type(raw_body) is not bytes or len(raw_body) > MAX_BODY_BYTES
            or type(signature_header) is not str
            or not 1 <= len(signature_header) <= MAX_HEADER_CHARS
            or type(signing_keys) is not tuple or not 1 <= len(signing_keys) <= MAX_KEYS
            or type(now) is not int or not 0 <= now <= MAX_TIMESTAMP):
        return False
    if any(type(key) is not bytes or not 1 <= len(key) <= MAX_KEY_BYTES
           for key in signing_keys):
        return False
    if any(ord(char) < 32 or ord(char) > 126 for char in signature_header):
        return False
    if signature_header.count(",") >= MAX_HEADER_PARTS:
        return False

    timestamp = None
    signatures = []
    for part in signature_header.split(","):
        prefix, _, value = part.partition("=")
        if prefix == "t":
            if timestamp is not None or _TIMESTAMP.fullmatch(value) is None:
                return False
            timestamp = value
        elif prefix == "v1":
            if len(signatures) >= MAX_V1_SIGNATURES or _SIGNATURE.fullmatch(value) is None:
                return False
            signatures.append(bytes.fromhex(value))
        # Other schemes/elements cannot contribute to verification.
    if timestamp is None or not signatures:
        return False
    age = now - int(timestamp)
    if not 0 <= age <= FRESHNESS_SECONDS:
        return False

    matched = False
    for key in signing_keys:
        digest = hmac.new(key, digestmod="sha256")
        digest.update(timestamp.encode("ascii"))
        digest.update(b".")
        digest.update(raw_body)
        expected = digest.digest()
        # Evaluate every bounded pair; never reveal which rotation key matched.
        for signature in signatures:
            matched |= hmac.compare_digest(expected, signature)
    return matched
