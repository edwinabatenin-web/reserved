"""Independent synthetic vectors and bounded offline protocol regressions."""
import ast
import hashlib
import inspect
from pathlib import Path

import pytest

from reserved.billing import stripe_signature_verifier as subject


KEY = b"synthetic-key-only-not-a-credential"
BODY = b'{"synthetic":true}'
NOW = 1_700_000_000


def reference_hmac(key, message):
    """Test-only HMAC composition from SHA-256 pads, not production hmac.new."""
    if len(key) > 64:
        key = hashlib.sha256(key).digest()
    padded = key.ljust(64, b"\x00")
    inner = bytes(value ^ 0x36 for value in padded)
    outer = bytes(value ^ 0x5C for value in padded)
    return hashlib.sha256(outer + hashlib.sha256(inner + message).digest()).hexdigest()


def header(body=BODY, key=KEY, timestamp=str(NOW)):
    signature = reference_hmac(key, timestamp.encode("ascii") + b"." + body)
    return f"t={timestamp},v1={signature}"


def verify(body=BODY, signature=None, keys=(KEY,), now=NOW):
    return subject.verify_stripe_signature(body, header() if signature is None else signature,
                                           keys, now=now)


@pytest.mark.parametrize("key,message,expected", [
    (b"\x0b" * 20, b"Hi There", "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    (b"Jefe", b"what do ya want for nothing?", "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"),
])
def test_independent_reference_matches_rfc4231_known_answers(key, message, expected):
    assert reference_hmac(key, message) == expected
    body = b"synthetic-non-json\x00\xff"
    assert verify(body=body, signature=header(body, key), keys=(key,)) is True


def test_literal_stripe_format_known_answer_cross_checked_with_openssl():
    # Independently produced once using local openssl dgst -sha256 -hmac over
    # literal timestamp/body bytes, then frozen; no external command in tests.
    expected = "a7be023c3b9c3fe2343b801b49c0e4eaa18a4b759cfd0a1f68fc54925101f0c1"
    assert reference_hmac(KEY, b'1700000000.{"synthetic":true}') == expected
    assert verify(signature=f"t=1700000000,v1={expected}") is True


def test_original_timestamp_bytes_are_not_replaced_by_integer_encoding():
    assert verify(signature=header(timestamp="0001700000000")) is True
    assert verify(signature=header().replace("t=1700000000", "t=0001700000000")) is False
    assert verify(signature=header(timestamp=str(NOW - 1))) is True


@pytest.mark.parametrize("body", [b'', b'{}', b'{ "synthetic":true}', BODY + b"\n",
                                 b'{"synthetic": true}', b'\xff', b'\xef\xbb\xbf' + BODY])
def test_raw_body_change_invalidates_original_signature(body):
    assert verify(body=body) is False
    assert verify(body=body, signature=header(body)) is True


def test_encoding_change_cannot_be_normalised():
    utf8 = '{"name":"caf\u00e9"}'.encode("utf-8")
    latin1 = '{"name":"caf\u00e9"}'.encode("latin-1")
    escaped = b'{"name":"caf\\u00e9"}'
    assert verify(utf8, header(utf8)) is True
    assert verify(latin1, header(utf8)) is False
    assert verify(escaped, header(utf8)) is False


def test_wrong_key_schemes_rotation_and_no_early_match_exit(monkeypatch):
    assert verify(keys=(b"synthetic-wrong-key",)) is False
    assert verify(signature=header().replace("v1=", "v0=")) is False
    assert verify(signature=header() + ",v0=not-a-v1,x=ignored") is True
    second = b"synthetic-rotated-key"
    first_mac = header().split("v1=")[1]
    second_mac = header(key=second).split("v1=")[1]
    combined = f"t={NOW},v1={first_mac},v1={second_mac}"
    assert verify(signature=combined, keys=(KEY,)) is True
    assert verify(signature=combined, keys=(second,)) is True
    compared = []
    real_compare = subject.hmac.compare_digest
    def observe(a, b):
        compared.append((len(a), len(b)))  # Never retain key/body/header values.
        return real_compare(a, b)
    monkeypatch.setattr(subject.hmac, "compare_digest", observe)
    assert verify(signature=combined, keys=(KEY, second)) is True
    assert compared == [(32, 32)] * 4


@pytest.mark.parametrize("timestamp", ["", "-1", "+1700000000", "1700000000.0", "1e9",
                                      " 1700000000", "1700000000 ", "\u0661", "9" * 17])
def test_malformed_timestamps_fail(timestamp):
    assert verify(signature=header().replace(f"t={NOW}", f"t={timestamp}")) is False


@pytest.mark.parametrize("suffix", [f",t={NOW}", f",t={NOW - 1}", ",t=bad"])
def test_duplicate_even_equal_timestamps_are_ambiguous(suffix):
    assert verify(signature=header() + suffix) is False


@pytest.mark.parametrize("bad", ["", "a" * 63, "a" * 65, "z" * 64, "00 " * 32,
                                "0x" + "a" * 62, "=" + "a" * 64])
def test_malformed_v1_rejected_even_with_valid_match(bad):
    assert verify(signature=header() + ",v1=" + bad) is False


@pytest.mark.parametrize("bad", ["", "t=1700000000", "v1=" + "a" * 64,
                                "t=1700000000,v0=" + "a" * 64, "t=1700000000,v1",
                                "t=1700000000\n,v1=" + "a" * 64])
def test_missing_scheme_timestamp_and_control_characters_fail(bad):
    assert verify(signature=bad) is False


def test_hex_encoding_and_entry_order():
    t, v = header().split(",")
    assert verify(signature=v + "," + t) is True
    assert verify(signature=t + ",v1=" + v[3:].upper()) is True
    assert verify(signature=t + ", V1=" + v[3:]) is False


@pytest.mark.parametrize("age,accepted", [(0, True), (1, True), (299, True), (300, True),
                                        (301, False), (-1, False), (-300, False)])
def test_fixed_freshness_and_future_boundaries(age, accepted):
    assert verify(now=NOW + age) is accepted


def test_clock_and_timestamp_numeric_extremes():
    assert verify(signature=header(timestamp="0"), now=0) is True
    assert verify(signature=header(timestamp=str(subject.MAX_TIMESTAMP)), now=subject.MAX_TIMESTAMP) is True
    assert verify(now=subject.MAX_TIMESTAMP + 1) is False
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        subject.verify_stripe_signature(BODY, header(), (KEY,), now=NOW, tolerance=0)


class BytesSubclass(bytes):
    pass


class StrSubclass(str):
    pass


class TupleSubclass(tuple):
    pass


class IntSubclass(int):
    pass


class Hostile:
    def __repr__(self):
        raise AssertionError("input repr must not be invoked")
    def __str__(self):
        raise AssertionError("input str must not be invoked")
    def __len__(self):
        raise AssertionError("input len must not be invoked")


@pytest.mark.parametrize("field,value", [
    ("body", None), ("body", bytearray(BODY)), ("body", memoryview(BODY)), ("body", BytesSubclass(BODY)),
    ("body", Hostile()), ("signature", header().encode()), ("signature", StrSubclass(header())),
    ("signature", Hostile()), ("keys", KEY), ("keys", [KEY]), ("keys", TupleSubclass((KEY,))),
    ("keys", (BytesSubclass(KEY),)), ("keys", (Hostile(),)), ("keys", Hostile()),
    ("now", True), ("now", float(NOW)), ("now", str(NOW)), ("now", IntSubclass(NOW)),
    ("now", -1), ("now", Hostile()),
])
def test_exact_types_reject_subclasses_bools_and_hostile_objects(field, value):
    kwargs = dict(body=BODY, signature=header(), keys=(KEY,), now=NOW)
    kwargs[field] = value
    assert verify(**kwargs) is False


def test_resource_caps_at_and_above_boundaries(monkeypatch):
    body = b"x" * subject.MAX_BODY_BYTES
    assert verify(body, header(body)) is True
    assert verify(body + b"x", header(body)) is False
    for key in (b"k", b"k" * subject.MAX_KEY_BYTES):
        assert verify(signature=header(key=key), keys=(key,)) is True
    assert verify(keys=()) is False
    assert verify(keys=(b"",)) is False
    assert verify(keys=(b"k" * (subject.MAX_KEY_BYTES + 1),)) is False
    assert verify(keys=(KEY,) * subject.MAX_KEYS) is True
    assert verify(keys=(KEY,) * (subject.MAX_KEYS + 1)) is False
    sig = header().split(",")[1]
    many = f"t={NOW}," + ",".join([sig] * subject.MAX_V1_SIGNATURES)
    assert verify(signature=many) is True
    assert verify(signature=many + "," + sig) is False
    parts = header() + ",v0=ignored" * (subject.MAX_HEADER_PARTS - 2)
    assert verify(signature=parts) is True
    assert verify(signature=parts + ",v0=ignored") is False
    padded = header() + ",x=" + "a" * (subject.MAX_HEADER_CHARS - len(header()) - 3)
    assert len(padded) == subject.MAX_HEADER_CHARS
    assert verify(signature=padded) is True
    assert verify(signature=padded + "a") is False
    # Rejections must happen before HMAC construction, not just after doing work.
    monkeypatch.setattr(subject.hmac, "new", lambda *a, **k: pytest.fail("expensive work before admission"))
    assert verify(body=b"x" * (subject.MAX_BODY_BYTES + 1)) is False
    assert verify(signature=padded + "a") is False
    assert verify(signature=many + "," + sig) is False
    assert verify(keys=(KEY,) * (subject.MAX_KEYS + 1)) is False


def test_non_json_repeated_delivery_is_not_event_admission_or_replay_detection(caplog, capsys):
    body = b"synthetic-private-body-not-json\x00\xff"
    signed = header(body)
    for _ in range(2):
        assert subject.verify_stripe_signature(body, signed, (KEY,), now=NOW) is True
    assert subject.verify_stripe_signature(body, signed, (KEY,), now=NOW + 301) is False
    assert repr(verify(body, signed)) == "True"
    assert caplog.text == ""
    assert capsys.readouterr() == ("", "")


def test_invalid_inputs_have_only_non_echoing_boolean_diagnostics(caplog, capsys):
    body = b"synthetic-private-payload"
    key = b"synthetic-private-signing-material"
    signed = header(body, key)
    results = [
        subject.verify_stripe_signature(body, signed + ",t=bad", (key,), now=NOW),
        subject.verify_stripe_signature(body, signed + ",v1=synthetic-private-value", (key,), now=NOW),
        subject.verify_stripe_signature(body, signed, (key,), now=NOW + 301),
        subject.verify_stripe_signature(body, signed, (b"synthetic-wrong",), now=NOW),
        subject.verify_stripe_signature(Hostile(), signed, (key,), now=NOW),
    ]
    assert results == [False] * 5
    assert [repr(result) for result in results] == ["False"] * 5
    assert caplog.text == ""
    assert capsys.readouterr() == ("", "")


def test_implementation_has_no_ingress_storage_clock_or_admission_dependencies():
    source = inspect.getsource(subject)
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports == {"hmac", "re"}
    assert not any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree))
    assert not any(isinstance(node, (ast.ClassDef, ast.Raise)) for node in ast.walk(tree))
    assert [node.name for node in tree.body if isinstance(node, ast.FunctionDef)] == ["verify_stripe_signature"]
    assert set(inspect.signature(subject.verify_stripe_signature).parameters) == {
        "raw_body", "signature_header", "signing_keys", "now",
    }
    root = Path(__file__).resolve().parents[1]
    for path in (root / "reserved").rglob("*.py"):
        if path == Path(subject.__file__):
            continue
        _assert_exact_verifier_caller(path.relative_to(root).as_posix(), path.read_text())


def _assert_exact_verifier_caller(path, source):
    """One direct source caller, not a directory exception or dynamic import."""
    module, symbol = 'stripe_signature_verifier', 'verify_stripe_signature'
    tree = ast.parse(source)
    if path != 'reserved/billing/local_stripe_initial_payment.py':
        assert module not in source and symbol not in source, path
        # Also reject literal split-module dynamic imports in this source inventory.
        constants = ''.join(node.value for node in ast.walk(tree)
                            if isinstance(node, ast.Constant) and type(node.value) is str)
        assert module not in constants and symbol not in constants, path
        return
    assert source.count(module) == 1 and source.count(symbol) == 2
    references = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module == module]
    assert len(references) == 1
    imported = references[0]
    assert imported.level == 1 and len(imported.names) == 1
    assert imported.names[0].name == symbol and imported.names[0].asname is None
    names = [node for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == symbol]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == symbol]
    assert len(names) == len(calls) == 1 and names[0] is calls[0].func
    assert len(calls[0].args) == 3 and [arg.arg for arg in calls[0].keywords] == ['now']


@pytest.mark.parametrize('path,source', [
    ('reserved/other.py', 'from .stripe_signature_verifier import verify_stripe_signature'),
    ('reserved/billing/other.py', 'import reserved.billing.stripe_signature_verifier'),
    ('reserved/other.py', '__import__("stripe_signature_" + "verifier")'),
    ('reserved/billing/local_stripe_initial_payment.py', 'from .stripe_signature_verifier import *'),
    ('reserved/billing/local_stripe_initial_payment.py', 'from .stripe_signature_verifier import verify_stripe_signature as check'),
    ('reserved/billing/local_stripe_initial_payment.py', 'from reserved.billing.stripe_signature_verifier import verify_stripe_signature'),
    ('reserved/billing/local_stripe_initial_payment.py', 'check = __import__("stripe_signature_verifier").verify_stripe_signature'),
])
def test_verifier_inventory_rejects_other_paths_and_import_forms(path, source):
    with pytest.raises(AssertionError):
        _assert_exact_verifier_caller(path, source)


def test_verifier_inventory_rejects_extra_reference_and_alias():
    root = Path(__file__).resolve().parents[1]
    path = 'reserved/billing/local_stripe_initial_payment.py'
    source = (root / path).read_text()
    _assert_exact_verifier_caller(path, source)
    for suffix in ('\nextra = verify_stripe_signature\n', '\nverify_stripe_signature(a,b,c,now=1)\n',
                   '\nextra = "stripe_signature_verifier"\n'):
        with pytest.raises(AssertionError):
            _assert_exact_verifier_caller(path, source + suffix)
