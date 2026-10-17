"""Synthetic Sri Lankan overseas-job posts in English, Sinhala and Singlish.

Every post is synthetic. Phone numbers are masked (07X-XXXXXXX), links use the
reserved .example domain and agency names are invented.

Two eras:
  current  - what scams look like today (Gulf / Malaysia jobs, agency fees,
             bank deposits, WhatsApp contact). Used for train / val / test.
  shifted  - "tomorrow's" scams: new destinations (Israel, Japan, Korea,
             Europe), new fee tricks (QR payments, USDT, mobile wallets, app
             top-ups), new channels (Telegram, TikTok, links), more Singlish
             and obfuscated spelling. Used only for the drift demo.

The current era uses a phrasing-disjoint split: every component pool is cut
into a train part and a test part, so test posts are built from sentences the
model never saw in training.
"""
import random

import pandas as pd

DEST_CURRENT = {
    "en": ["Dubai", "Qatar", "Saudi Arabia", "Kuwait", "Oman", "Malaysia", "Maldives"],
    "si": ["ඩුබායි", "කටාර්", "සෞදි අරාබිය", "කුවේට්", "ඕමානය", "මැලේසියාව", "මාලදිවයින"],
}
DEST_SHIFTED = {
    "en": ["Israel", "Japan", "South Korea", "Romania", "Poland", "Canada"],
    "si": ["ඊශ්‍රායලය", "ජපානය", "දකුණු කොරියාව", "රුමේනියාව", "පෝලන්තය", "කැනඩාව"],
}
CITIES = {
    "en": ["Colombo", "Kandy", "Kurunegala", "Galle", "Negombo", "Matara"],
    "si": ["කොළඹ", "මහනුවර", "කුරුණෑගල", "ගාල්ල", "මීගමුව", "මාතර"],
}
AGENCIES = [
    "Ceylon Horizon Manpower", "Island Path Recruiters", "Blue Lotus Placements",
    "Serendib Careers Abroad", "Ruhuna Global Staffing", "Kelani Bridge Employment",
    "Sigiri Overseas Services", "Lion Gate Manpower",
]

# --------------------------------------------------------------------------
# Current-era pools
# --------------------------------------------------------------------------
SCAM = {
    "en": {
        "hook": [
            "URGENT VACANCIES in {dest}!!!",
            "Golden chance to work in {dest}",
            "Direct visa jobs in {dest} - no agent needed",
            "100% guaranteed jobs in {dest}",
            "Work abroad and change your life! {dest} jobs available now",
            "Hiring now for {dest} - male and female",
            "Free visa and air ticket to {dest}",
            "Last chance!! {dest} company direct recruitment",
            "{agency} (SLBFE Licence No. {lic}) - urgent recruitment for {dest}",
            "Vacancies in {dest} through {agency}",
        ],
        "job": [
            "Factory workers", "Housemaids", "Light vehicle drivers", "Hotel cleaners",
            "Construction labourers", "Packing helpers", "Supermarket cashiers", "Farm workers",
        ],
        "pay": [
            "Salary Rs. {big_salary} per month",
            "Monthly salary {big_salary} LKR plus OT",
            "Earn up to Rs. {big_salary} monthly",
            "Salary {big_usd} USD, food and accommodation free",
        ],
        "perk": [
            "No experience needed", "No interview", "No age limit",
            "No O/L or A/L required", "Visa guaranteed within 7 days", "No language test",
            "Without any qualifications", "Government approved agency",
            "Online interview by video call", "Offer letter within 2 days",
        ],
        "fee": [
            "Pay Rs. {fee} registration fee to confirm your seat",
            "Only Rs. {fee} advance payment, balance after visa",
            "Deposit Rs. {fee} to the account below to start processing",
            "Visa fee Rs. {fee} must be paid today",
            "Send Rs. {fee} for medical and file opening",
            "Refundable deposit of Rs. {fee} required",
            "Rs. {fee} processing fee to our manager's personal account",
            "Pay Rs. {fee} and get your visa copy in 3 days",
        ],
        "contact": [
            "WhatsApp only: 07X-XXXXXXX",
            "Call or WhatsApp Mr. Nimal 07X-XXXXXXX",
            "Inbox us now",
            "Send your passport copy by WhatsApp to 07X-XXXXXXX",
            "Contact our agent, no office visits",
            "WhatsApp +94 7X XXX XXXX for details",
        ],
        "urgency": [
            "Only 10 seats left!", "Offer closes today", "First come first served",
            "Hurry, limited slots", "Apply before Friday", "Don't miss this chance!!",
        ],
    },
    "si": {
        "hook": [
            "{dest} රැකියා අවස්ථා!!!",
            "{dest} රැකියා සඳහා විශේෂ අවස්ථාවක්",
            "100% සහතික {dest} රැකියා",
            "{dest} සෘජු වීසා - ඒජන්තවරු නැහැ",
            "ඔබේ ජීවිතය වෙනස් කරගන්න! {dest} රැකියා දැන්ම",
            "{dest} සඳහා නොමිලේ වීසා සහ ගුවන් ටිකට්",
            "{agency} (බලපත්‍ර අංක {lic}) - {dest} හදිසි බඳවා ගැනීම්",
        ],
        "job": [
            "කර්මාන්තශාලා සේවකයින්", "ගෘහ සේවිකාවන්", "රියදුරන්",
            "හෝටල් පිරිසිදු කිරීමේ සේවකයින්", "ඉදිකිරීම් කම්කරුවන්", "ඇසුරුම් සහායකයින්",
        ],
        "pay": [
            "මාසික වැටුප රු. {big_salary}",
            "මසකට රු. {big_salary} දක්වා උපයන්න",
            "වැටුප රු. {big_salary} + අතිකාල දීමනා",
            "කෑම බීම නවාතැන් නොමිලේ, වැටුප රු. {big_salary}",
        ],
        "perk": [
            "පළපුරුද්ද අවශ්‍ය නැත", "සම්මුඛ පරීක්ෂණයක් නැත", "වයස් සීමාවක් නැත",
            "සා/පෙළ උ/පෙළ අවශ්‍ය නැත", "දින 7කින් වීසා සහතිකයි", "භාෂා පරීක්ෂණයක් නැත",
            "රජයේ අනුමැතිය ඇති ආයතනයක්", "වීඩියෝ ඇමතුමකින් ඔන්ලයින් සම්මුඛ පරීක්ෂණය",
        ],
        "fee": [
            "ඔබේ ස්ථානය තහවුරු කිරීමට රු. {fee} ලියාපදිංචි ගාස්තුවක් ගෙවන්න",
            "අත්තිකාරම් ලෙස රු. {fee} පමණයි, ඉතිරිය වීසා ලැබුණු පසු",
            "පහත ගිණුමට රු. {fee} තැන්පත් කරන්න",
            "වීසා ගාස්තුව රු. {fee} අදම ගෙවිය යුතුයි",
            "වෛද්‍ය පරීක්ෂණයට සහ ලිපිගොනු සඳහා රු. {fee} එවන්න",
            "ආපසු ගෙවන තැන්පතුවක් ලෙස රු. {fee} අවශ්‍යයි",
        ],
        "contact": [
            "WhatsApp පමණයි: 07X-XXXXXXX",
            "විස්තර සඳහා WhatsApp කරන්න 07X-XXXXXXX",
            "ඔබේ ගමන් බලපත්‍ර පිටපත WhatsApp කරන්න",
            "කාර්යාලයට පැමිණීම අවශ්‍ය නැත",
            "අපගේ නියෝජිතයා අමතන්න 07X-XXXXXXX",
        ],
        "urgency": [
            "ඉතිරිව ඇත්තේ ස්ථාන 10ක් පමණයි!", "අද දිනයෙන් අවසන්",
            "මුලින්ම එන අයට පමණයි", "ඉක්මන් කරන්න!", "මෙම අවස්ථාව මඟ හරින්න එපා!",
        ],
    },
    "singlish": {
        "hook": [
            "{dest} job chance ekak!!!",
            "{dest} wala rassawal thiyenawa",
            "100% sure {dest} jobs",
            "{dest} direct visa, agent la naha",
            "Jeewithe wenas karaganna {dest} yanna",
            "{dest} free visa saha ticket",
            "{agency} (SLBFE licence {lic}) {dest} urgent rassawal",
        ],
        "job": [
            "factory wada", "house maid wada", "driver wada",
            "hotel cleaning wada", "construction wada", "packing wada",
        ],
        "pay": [
            "padi Rs. {big_salary} masekata",
            "masekata {big_salary} k witharama",
            "padiya {big_salary} + OT",
            "kema nawathan free, padi Rs. {big_salary}",
        ],
        "perk": [
            "experience oni naha", "interview naha", "wayasa simawak naha",
            "OL AL oni naha", "dawas 7n visa sure", "language test naha",
            "government approved agency ekak", "online interview video call eken",
        ],
        "fee": [
            "seat eka confirm karanna Rs. {fee} gewanna",
            "advance Rs. {fee} witharai, ithuru visa awata passe",
            "pahala account ekata Rs. {fee} deposit karanna",
            "visa fee Rs. {fee} ada ma gewanna oni",
            "medical ekata saha file ekata Rs. {fee} ewanna",
            "refundable deposit Rs. {fee} oni",
        ],
        "contact": [
            "WhatsApp witharai 07X-XXXXXXX",
            "wisthara walata WhatsApp karanna 07X-XXXXXXX",
            "passport copy eka WhatsApp karanna",
            "office ekata enna oni naha",
            "agent ta call karanna 07X-XXXXXXX",
        ],
        "urgency": [
            "seats 10i ithuru!", "ada withrai", "kalin ena ayata",
            "ikman karanna!!", "me chance eka miss karaganna epa",
        ],
    },
}

LEGIT = {
    "en": {
        "hook": [
            "{agency} (SLBFE Licence No. {lic}) is recruiting for {dest}",
            "Job vacancies in {dest} through {agency}, a licensed foreign employment agency",
            "{agency} invites applications for positions in {dest}",
            "Overseas employment opportunity in {dest}: {agency}, SLBFE licence {lic}",
            "Vacancies in {dest} - {agency} (licensed agency, Licence No. {lic})",
        ],
        "job": [
            "Registered nurses", "Heavy vehicle drivers with a valid licence",
            "Electricians (NVQ Level 4)", "Welders with trade test", "Hotel cooks with 3 years experience",
            "Plumbers (NVQ Level 3)", "Caregivers with certificate", "Accountants (part qualified)",
        ],
        "pay": [
            "Salary as per employer contract, approximately {usd} USD",
            "Basic salary {usd} USD per month plus overtime as per labour law",
            "Salary range will be explained at the interview",
            "Salary {usd} USD, accommodation provided by employer",
        ],
        "req": [
            "Minimum 2 years experience required", "NVQ certificate required",
            "Age between 23 and 40 years", "Must pass trade test and medical",
            "Valid passport required", "Applicants must register with SLBFE before departure",
            "English speaking ability is essential",
        ],
        "process": [
            "Interviews will be held at our office in {city} on {day}",
            "Bring original certificates to the interview",
            "Selected candidates will be informed in writing",
            "Please verify our licence on the SLBFE website before applying",
            "Do not pay money to individuals; all payments are made at our office with official receipts",
            "Fees are charged only as approved by SLBFE",
            "The employment contract will be explained and signed at SLBFE",
            "Agency service fee as approved by SLBFE is payable only after the visa is issued, with an official receipt",
            "Closing date: {day}",
            "No experience needed for cleaner posts, training provided by employer",
        ],
        "contact": [
            "Apply by email to careers@{slug}.example",
            "Visit our office in {city} between 9 am and 4 pm",
            "For details call our office line 011-XXXXXXX",
            "Send your CV to hr@{slug}.example",
            "WhatsApp our office on 07X-XXXXXXX to book an interview time",
        ],
    },
    "si": {
        "hook": [
            "{agency} (විදේශ සේවා නියුක්ති කාර්යාංශ බලපත්‍ර අංක {lic}) {dest} රැකියා සඳහා බඳවා ගැනීම්",
            "බලපත්‍රලාභී විදේශ රැකියා නියෝජිතායතනයක් වන {agency} හරහා {dest} රැකියා",
            "{dest} රැකියා සඳහා {agency} අයදුම්පත් කැඳවයි",
            "{dest} පුරප්පාඩු - {agency} (බලපත්‍ර අංක {lic})",
        ],
        "job": [
            "හෙද නිලධාරීන්", "බර වාහන රියදුරන් (වලංගු බලපත්‍රයක් සහිත)",
            "විදුලි කාර්මිකයින් (NVQ 4)", "වෙල්ඩින් කාර්මිකයින්", "හෝටල් අරක්කැමියන්",
            "ජලනල කාර්මිකයින්",
        ],
        "pay": [
            "වැටුප සේවා යෝජක ගිවිසුමට අනුව",
            "වැටුප් විස්තර සම්මුඛ පරීක්ෂණයේදී පැහැදිලි කෙරේ",
            "මාසික මූලික වැටුප ඩොලර් {usd} + අතිකාල",
        ],
        "req": [
            "අවම වසර 2ක පළපුරුද්ද අවශ්‍යයි", "NVQ සහතිකය අවශ්‍යයි", "වයස අවු. 23-40 අතර",
            "වෘත්තීය පරීක්ෂණය හා වෛද්‍ය පරීක්ෂණය සමත් විය යුතුය",
            "පිටත්ව යාමට පෙර කාර්යාංශයේ ලියාපදිංචි විය යුතුය", "වලංගු ගමන් බලපත්‍රයක් අවශ්‍යයි",
        ],
        "process": [
            "සම්මුඛ පරීක්ෂණ {city} පිහිටි අපගේ කාර්යාලයේදී පැවැත්වේ",
            "මුල් සහතික රැගෙන එන්න",
            "කිසිදු පුද්ගලයෙකුට මුදල් නොගෙවන්න; සියලු ගෙවීම් කාර්යාලයේදී නිල රිසිට්පත් සමඟ",
            "අයදුම් කිරීමට පෙර කාර්යාංශ වෙබ් අඩවියෙන් අපගේ බලපත්‍රය තහවුරු කරගන්න",
            "තෝරාගත් අයට ලිඛිතව දැනුම් දෙනු ලැබේ",
            "කාර්යාංශය අනුමත සේවා ගාස්තුව වීසා ලැබුණු පසු පමණක්, නිල රිසිට්පතක් සමඟ ගෙවිය යුතුය",
            "පිරිසිදු කිරීමේ තනතුරු සඳහා පළපුරුද්ද අවශ්‍ය නැත, පුහුණුව ලබා දේ",
        ],
        "contact": [
            "careers@{slug}.example වෙත අයදුම් කරන්න",
            "පෙ.ව. 9 සිට ප.ව. 4 දක්වා {city} කාර්යාලයට පැමිණෙන්න",
            "කාර්යාල දුරකථන 011-XXXXXXX",
            "සම්මුඛ පරීක්ෂණ වේලාවක් සඳහා කාර්යාලයට WhatsApp කරන්න 07X-XXXXXXX",
        ],
    },
    "singlish": {
        "hook": [
            "{agency} (SLBFE licence {lic}) {dest} jobs walata aluthin ganna",
            "licensed agency ekak wena {agency} haraha {dest} rassawal",
            "{dest} vacancies - {agency}, licence no {lic}",
            "{agency} eken {dest} jobs walata applications kanda wanawa",
        ],
        "job": [
            "nurses", "heavy vehicle drivers (valid licence ekak ekka)", "electricians (NVQ 4)",
            "welders", "hotel cooks", "plumbers",
        ],
        "pay": [
            "padiya employer contract eka anuwa",
            "padi wisthara interview eke kiyanawa",
            "basic padi USD {usd} + OT",
        ],
        "req": [
            "avurudu 2k experience oni", "NVQ certificate oni", "wayasa 23-40 athara",
            "trade test saha medical pass wenna oni", "yanna kalin SLBFE register wenna oni",
            "valid passport ekak oni",
        ],
        "process": [
            "interview eka {city} office eke",
            "original certificates genna",
            "kisi kenekuta salli denna epa, gewim office eke receipt ekka witharai",
            "apply karanna kalin SLBFE site eken licence eka check karanna",
            "select une ayata liyumak ewanawa",
            "SLBFE approved service fee eka visa awata passe witharai, official receipt ekak ekka",
            "cleaner posts walata experience oni naha, training denawa",
        ],
        "contact": [
            "careers@{slug}.example ekata apply karanna",
            "9-4 athara {city} office ekata enna",
            "office number 011-XXXXXXX",
            "interview time ekak ganna office ekata WhatsApp karanna 07X-XXXXXXX",
        ],
    },
}

# --------------------------------------------------------------------------
# Shifted-era pools: these replace or extend the current pools
# --------------------------------------------------------------------------
SCAM_SHIFT = {
    "en": {
        "hook": [
            "Government approved {dest} quota jobs - private registration open",
            "{dest} caregiver visas, special 2026 quota",
            "Online selection for {dest} - no office visit",
            "{dest} work permit in 21 days through our online portal",
        ],
        "fee": [
            "Scan the QR code and pay the Rs. {fee} processing charge online",
            "Pay {usdt} USDT to reserve your visa slot",
            "Book your language exam slot in our app, fee Rs. {fee} by mobile wallet",
            "Pay Rs. {fee} through mobile wallet for your e-visa approval",
            "Small online medical booking fee Rs. {fee}, pay via the link",
            "Top up Rs. {fee} to activate your job account",
        ],
        "contact": [
            "Join our Telegram channel t.me/xxxx for the form",
            "DM us on TikTok to apply",
            "Apply only through apply-now.example/form",
            "Message the HR team on Telegram",
        ],
    },
    "si": {
        "hook": [
            "{dest} රැකියා සඳහා විශේෂ 2026 කෝටාව",
            "{dest} රැකබලා ගැනීමේ රැකියා - ඔන්ලයින් තේරීම",
            "රජයේ අනුමත {dest} කෝටා රැකියා - පෞද්ගලික ලියාපදිංචිය",
        ],
        "fee": [
            "QR කේතය ස්කෑන් කර රු. {fee} සැකසුම් ගාස්තුව ඔන්ලයින් ගෙවන්න",
            "ඔබේ වීසා ස්ලොට් එක වෙන් කරගැනීමට USDT {usdt} ගෙවන්න",
            "රු. {fee} ජංගම මුදල් පසුම්බිය හරහා ගෙවා e-වීසා අනුමැතිය ලබාගන්න",
            "ඔබේ රැකියා ගිණුම සක්‍රිය කිරීමට රු. {fee} රීලෝඩ් කරන්න",
        ],
        "contact": [
            "අයදුම්පත සඳහා අපගේ Telegram නාලිකාවට එක්වන්න",
            "TikTok හරහා අපට පණිවිඩයක් එවන්න",
            "apply-now.example/form හරහා පමණක් අයදුම් කරන්න",
        ],
    },
    "singlish": {
        "hook": [
            "{dest} 2026 special quota eka",
            "{dest} caregiver visa, online selection",
            "government approved {dest} quota jobs, private registration",
        ],
        "fee": [
            "QR eka scan karala Rs. {fee} processing charge eka online gewanna",
            "visa slot eka book karanna USDT {usdt} danna",
            "app eken exam slot eka book karanna, Rs. {fee} wallet eken",
            "job account eka activate karanna Rs. {fee} top up karanna",
        ],
        "contact": [
            "form eka ganna Telegram channel ekata join wenna",
            "TikTok eken msg ekak danna",
            "apply-now.example/form eken witharai apply karanna",
        ],
    },
}

LEGIT_SHIFT = {
    "en": [
        "The Sri Lanka Bureau of Foreign Employment announces registration for the {dest} employment programme",
        "Registration is free of charge at SLBFE district offices",
        "Selection is by an official language and skills exam conducted by SLBFE",
        "Do not pay any private party for this programme",
        "Check results only on the official SLBFE website",
        "Applicants aged 21 to 39 with O/L qualifications may apply",
    ],
    "si": [
        "ශ්‍රී ලංකා විදේශ සේවා නියුක්ති කාර්යාංශය {dest} රැකියා වැඩසටහන සඳහා ලියාපදිංචිය නිවේදනය කරයි",
        "කාර්යාංශයේ දිස්ත්‍රික් කාර්යාලවල ලියාපදිංචිය නොමිලේ",
        "තේරීම කාර්යාංශය පවත්වන නිල භාෂා හා කුසලතා විභාගයක් මඟිනි",
        "මෙම වැඩසටහන සඳහා කිසිදු පෞද්ගලික පාර්ශවයකට මුදල් නොගෙවන්න",
        "ප්‍රතිඵල නිල වෙබ් අඩවියෙන් පමණක් පරීක්ෂා කරන්න",
    ],
    "singlish": [
        "SLBFE eken {dest} employment programme ekata registration patan aran",
        "registration eka district office wala free",
        "selection eka SLBFE official language exam eken",
        "me programme ekata private kenekuta salli denna epa",
        "results check karanna official SLBFE site eken witharai",
    ],
}

EMOJI = ["🔥", "✈️", "💰", "✅", "‼️", "🇱🇰"]
OBFUSCATE = {
    "WhatsApp": "W.h.a.t.s.A.p.p", "deposit": "d3posit", "visa": "v1sa", "Visa": "V1sa",
    "Telegram": "T e l e g r a m", "fee": "f33",
}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Saturday"]

LANG_MIX = {"current": {"en": 0.5, "si": 0.3, "singlish": 0.2},
            "shifted": {"en": 0.2, "si": 0.35, "singlish": 0.45}}


def _split_pool(items, part):
    """Phrasing-disjoint split: every 4th item is reserved for the test part.

    Shifted-era pools are small (3-6 items), so for them the last quarter
    (at least one item) is held out instead: "shift_train" feeds the drift
    stream and retraining, "shift_test" builds the shifted holdout.
    """
    if part == "all":
        return items
    if part in ("shift_train", "shift_test"):
        k = max(1, len(items) // 4)
        if len(items) <= k:
            return items
        return items[-k:] if part == "shift_test" else items[:-k]
    test = items[3::4]
    train = [x for i, x in enumerate(items) if i % 4 != 3]
    return test if part == "test" else train


def _pick(rng, pool, part, k=1):
    items = _split_pool(pool, part)
    return rng.sample(items, min(k, len(items)))


def _post_context(rng, lang, era):
    """Values that must stay consistent across all lines of one post."""
    dests = (DEST_SHIFTED if era == "shifted" else DEST_CURRENT)
    dest_lang = "si" if lang == "si" else "en"
    agency = rng.choice(AGENCIES)
    return dict(dest=rng.choice(dests[dest_lang]), city=rng.choice(CITIES[dest_lang]),
                agency=agency, slug=agency.lower().replace(" ", "-"),
                lic=rng.randint(1000, 3999), day=rng.choice(DAYS))


def _fill(rng, text, ctx):
    return text.format(
        **ctx,
        big_salary=f"{rng.randrange(350, 950, 25) * 1000:,}",
        big_usd=rng.randrange(1500, 4000, 100),
        usd=rng.randrange(400, 1500, 50),
        fee=f"{rng.randrange(25, 500, 5) * 1000:,}",
        usdt=rng.randrange(100, 1500, 50),
    )


def _impersonation_post(rng, lang, part):
    """Shifted-era tactic: copy the wording of an official SLBFE programme notice,
    then add a payment trick and an unofficial channel."""
    official = LEGIT_SHIFT[lang]
    neutral = _split_pool([official[i] for i in (2, 4, 5) if i < len(official)], part)
    lines = [official[0]] + rng.sample(neutral, rng.randint(1, len(neutral)))
    lines += _pick(rng, SCAM_SHIFT[lang]["fee"], part)
    lines += _pick(rng, SCAM_SHIFT[lang]["contact"], part)
    return lines


def _scam_post(rng, lang, era, part):
    if era == "shifted" and rng.random() < 0.5:
        return _impersonation_post(rng, lang, part)
    p = SCAM[lang]
    s = SCAM_SHIFT[lang] if era == "shifted" else None
    hook_pool = s["hook"] + p["hook"] if s else p["hook"]
    fee_pool = s["fee"] if s and rng.random() < 0.8 else p["fee"]
    contact_pool = s["contact"] if s and rng.random() < 0.7 else p["contact"]
    lines = _pick(rng, hook_pool, part)
    lines.append(", ".join(_pick(rng, p["job"], part, rng.randint(1, 3))))
    lines += _pick(rng, p["pay"], part)
    lines += _pick(rng, p["perk"], part, rng.randint(1, 3))
    lines += _pick(rng, fee_pool, part)
    lines += _pick(rng, contact_pool, part)
    if rng.random() < 0.7:
        lines += _pick(rng, p["urgency"], part)
    return lines


def _legit_post(rng, lang, era, part):
    if era == "shifted" and rng.random() < 0.5:
        pool = LEGIT_SHIFT[lang]
        rest = _split_pool(pool[1:], part)
        return [pool[0]] + rng.sample(rest, rng.randint(1, len(rest)))
    p = LEGIT[lang]
    lines = _pick(rng, p["hook"], part)
    lines.append(", ".join(_pick(rng, p["job"], part, rng.randint(1, 2))))
    lines += _pick(rng, p["pay"], part)
    lines += _pick(rng, p["req"], part, rng.randint(1, 3))
    lines += _pick(rng, p["process"], part, rng.randint(1, 2))
    lines += _pick(rng, p["contact"], part)
    return lines


def _obfuscate(rng, text):
    for a, b in OBFUSCATE.items():
        if rng.random() < 0.6:
            text = text.replace(a, b)
    return " ".join(w + (rng.choice(EMOJI) if rng.random() < 0.08 else "") for w in text.split(" "))


def generate(n, era, part, scam_rate, seed):
    """Generate n posts. era: current|shifted, part: train|test|all."""
    rng = random.Random(seed)
    mix = LANG_MIX[era]
    rows, seen = [], set()
    attempts = 0
    while len(rows) < n and attempts < n * 20:
        attempts += 1
        lang = rng.choices(list(mix), weights=list(mix.values()))[0]
        label = int(rng.random() < scam_rate)
        lines = (_scam_post if label else _legit_post)(rng, lang, era, part)
        ctx = _post_context(rng, lang, era)
        text = "\n".join(_fill(rng, line, ctx) for line in lines)
        if era == "shifted" and label and rng.random() < 0.35:
            text = _obfuscate(rng, text)
        if text in seen:
            continue
        seen.add(text)
        rows.append({"text": text, "label": label, "lang": lang,
                     "source": f"synthetic_sl_{era}"})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate(6, "current", "train", 0.5, 1)
    for _, r in df.iterrows():
        print(f"--- label={r.label} lang={r.lang}\n{r.text}\n")
    df = generate(4, "shifted", "all", 0.6, 2)
    for _, r in df.iterrows():
        print(f"--- SHIFTED label={r.label} lang={r.lang}\n{r.text}\n")
