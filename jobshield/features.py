"""Text normalisation, privacy redaction and explainable red-flag features."""
import hashlib
import re

_PHONE = re.compile(r"(\+94[\s-]?|0)7[0-9X][\s-]?[0-9X]{3}[\s-]?[0-9X]{4}|011-[0-9X]{7}|#PHONE_[^#]+#")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+|#EMAIL_[^#]+#")
_URL = re.compile(r"https?://\S+|www\.\S+|t\.me/\S+|\b[\w-]+\.example(/\S*)?|#URL_[^#]+#")
_NIC = re.compile(r"\b(\d{9}[VvXx]|\d{12})\b")
_SPACES = re.compile(r"[ \t]+")


def normalize(text: str) -> str:
    """Replace contact details with placeholder tokens so the model learns
    the pattern ("asks you to WhatsApp a number") rather than specific values."""
    text = str(text)
    text = _URL.sub(" URL ", text)
    text = _EMAIL.sub(" EMAIL ", text)
    text = _PHONE.sub(" PHONE ", text)
    text = _NIC.sub(" NIC ", text)
    return _SPACES.sub(" ", text).strip()


def redact(text: str) -> str:
    """Privacy-safe version of an input for logging (PDPA): no contact details."""
    return normalize(text)[:500]


def text_hash(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:16]


# Red flags: human-readable reasons shown to the user and reviewer.
# Each pattern covers English, Sinhala and Singlish wording.
RED_FLAGS = {
    "upfront_fee": r"deposit|d3posit|advance payment|registration fee|processing (fee|charge)|visa fee|f33|"
                   r"ගාස්තු|තැන්පත්|අත්තිකාරම්|gewanna|ewanna|salli",
    "guaranteed_visa": r"guarantee|100%|visa sure|සහතිකයි|සහතික",
    "no_checks": r"no experience|no interview|no age limit|without any qualification|no language test|"
                 r"oni naha|interview naha|අවශ්‍ය නැත|පරීක්ෂණයක් නැත|සීමාවක් නැත",
    "chat_app_only": r"whats\s?app|w\.h\.a\.t\.s|telegram|t e l e g r a m|tiktok|inbox us|dm us",
    "urgency": r"urgent|hurry|last chance|seats left|closes today|limited|ikman|ඉක්මන්|අද දිනයෙන්|ada withrai",
    "crypto_or_wallet": r"usdt|crypto|bitcoin|qr code|qr eka|mobile wallet|top up|reload|wallet|රීලෝඩ්|QR කේතය",
    "personal_account": r"personal account|account below|pahala account|පහත ගිණුමට",
    "licensed_agency": r"slbfe|licen[cs]e no|බලපත්‍ර|කාර්යාංශ",
}
_RED_FLAG_RE = {k: re.compile(v, re.IGNORECASE) for k, v in RED_FLAGS.items()}


def red_flags(text: str) -> list[str]:
    return [k for k, rx in _RED_FLAG_RE.items() if rx.search(str(text))]


def detect_lang(text: str) -> str:
    text = str(text)
    sinhala = sum(1 for c in text if "඀" <= c <= "෿")
    tamil = sum(1 for c in text if "஀" <= c <= "௿")
    letters = sum(1 for c in text if c.isalpha()) or 1
    if sinhala / letters > 0.3:
        return "si"
    if tamil / letters > 0.3:
        return "ta"
    if re.search(r"\b(ekak|wenna|karanna|naha|oni|eka|walata|witharai|gewanna)\b", text, re.IGNORECASE):
        return "singlish"
    return "en"
