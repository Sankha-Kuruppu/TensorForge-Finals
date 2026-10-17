from jobshield.data.sl_generator import SCAM, SCAM_SHIFT, _split_pool, generate
from jobshield.features import detect_lang, normalize, red_flags, redact


def test_redaction_removes_contact_details():
    text = "WhatsApp 077-1234567 or +94 71 234 5678, mail a.b@x.example, NIC 199012345678, see www.x.com"
    out = redact(text)
    for secret in ("1234567", "234 5678", "a.b@", "199012345678", "www.x.com"):
        assert secret not in out
    assert "PHONE" in out and "EMAIL" in out and "NIC" in out and "URL" in out


def test_masked_placeholders_normalised():
    assert normalize("WhatsApp only: 07X-XXXXXXX") == "WhatsApp only: PHONE"


def test_red_flags_multilingual():
    assert "upfront_fee" in red_flags("Pay Rs. 100,000 registration fee today")
    assert "upfront_fee" in red_flags("පහත ගිණුමට රු. 100,000 තැන්පත් කරන්න")
    assert "crypto_or_wallet" in red_flags("Pay 300 USDT to reserve your visa slot")
    assert red_flags("Interviews at our office, bring certificates") == []


def test_language_detection():
    assert detect_lang("කොරියාවේ රැකියා අවස්ථා") == "si"
    assert detect_lang("visa fee eka ada ma gewanna oni") == "singlish"
    assert detect_lang("Electricians needed in Qatar") == "en"


def test_phrasing_split_is_disjoint():
    for pools in SCAM.values():
        for pool in pools.values():
            assert not set(_split_pool(pool, "train")) & set(_split_pool(pool, "test"))


def test_shifted_split_is_disjoint_and_never_empty():
    for pools in SCAM_SHIFT.values():
        for pool in pools.values():
            train, test = _split_pool(pool, "shift_train"), _split_pool(pool, "shift_test")
            assert train and test and not set(train) & set(test)


def test_generator_is_deterministic():
    a = generate(20, "current", "train", 0.5, seed=1)
    b = generate(20, "current", "train", 0.5, seed=1)
    assert a.equals(b)
