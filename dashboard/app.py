"""JobShield LK dashboard.  Run: streamlit run dashboard/app.py"""
import json
import os

import pandas as pd
import requests
import streamlit as st

API = os.environ.get("JOBSHIELD_API", "http://localhost:8000")

st.set_page_config(page_title="JobShield LK", page_icon="🛡️", layout="wide")

LEVEL_BADGE = {"OK": "🟢 OK", "WARN": "🟠 WARN", "ALERT": "🔴 ALERT", "WARMING_UP": "⚪ Warming up"}
DECISION_BADGE = {"scam": "🔴 Likely scam", "review": "🟠 Needs review", "legit": "🟢 No strong scam signals"}
SIGNAL_NAMES = {"centroid_dist": "Input distribution shift", "confidence_mean": "Mean confidence",
                "unknown_rate": "Unknown-input share"}
FLAG_NAMES = {
    "upfront_fee": "Asks for an upfront fee or deposit", "guaranteed_visa": "Promises a guaranteed visa",
    "no_checks": "No experience / interview / qualifications needed", "chat_app_only": "Contact only via chat app",
    "urgency": "Pressure to act fast", "crypto_or_wallet": "Crypto, QR or mobile-wallet payment",
    "personal_account": "Payment to a personal account", "licensed_agency": "Mentions an SLBFE licence",
}
EXAMPLES = {
    "Scam (English)": "URGENT VACANCIES in Dubai!!!\nFactory workers, Housemaids\nSalary Rs. 650,000 per month\n"
                      "No experience needed\nPay Rs. 150,000 registration fee to confirm your seat\n"
                      "WhatsApp only: 07X-XXXXXXX\nOnly 10 seats left!",
    "Scam (Sinhala)": "කටාර් රැකියා අවස්ථා!!!\nගෘහ සේවිකාවන්\nමාසික වැටුප රු. 500,000\n"
                      "සම්මුඛ පරීක්ෂණයක් නැත\nපහත ගිණුමට රු. 120,000 තැන්පත් කරන්න\nWhatsApp පමණයි: 07X-XXXXXXX",
    "Legitimate agency": "Ceylon Horizon Manpower (SLBFE Licence No. 2101) is recruiting for Qatar\n"
                         "Electricians (NVQ Level 4)\nBasic salary 900 USD per month plus overtime as per labour law\n"
                         "Minimum 2 years experience required\nInterviews will be held at our office in Kandy on Monday\n"
                         "Do not pay money to individuals; all payments are made at our office with official receipts",
    "New tactic (SLBFE impersonation)": "SLBFE eken South Korea employment programme ekata registration patan aran\n"
                                        "selection eka SLBFE official language exam eken\n"
                                        "QR eka scan karala Rs. 45,000 processing charge eka online gewanna\n"
                                        "form eka ganna Telegram channel ekata join wenna",
}


def api(method, path, **kw):
    try:
        r = requests.request(method, f"{API}{path}", timeout=600, **kw)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"API error on {path}: {e}")
        return None


status = api("GET", "/monitor/status") or {}
model = api("GET", "/model") or {}

with st.sidebar:
    st.title("🛡️ JobShield LK")
    st.caption("Fake overseas-job post detection for Sri Lankan job seekers")
    st.metric("Serving model", model.get("version", "-"))
    st.markdown(f"**Drift status:** {LEVEL_BADGE.get(status.get('level'), status.get('level', '-'))}")
    st.markdown(f"**Safe mode:** {'🟠 ON' if status.get('safe_mode') else 'off'}")
    if model.get("retraining"):
        st.info("⏳ Retraining challenger model…")
    st.divider()
    st.caption("All demo posts are synthetic. No real phone numbers, agencies or people.")

tab_check, tab_monitor, tab_review, tab_model = st.tabs(
    ["Check a post", "Monitoring & drift", "Review queue", "Model"])

# --------------------------------------------------------------------------
with tab_check:
    st.subheader("Is this overseas job offer safe?")
    ex = st.selectbox("Load an example", ["(type your own)"] + list(EXAMPLES))
    text = st.text_area("Paste the job post or message (English, Sinhala or Singlish)",
                        value=EXAMPLES.get(ex, ""), height=180)
    if st.button("Check post", type="primary") and len(text.strip()) >= 10:
        res = api("POST", "/predict", json={"text": text, "channel": "dashboard"})
        if res:
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"### {DECISION_BADGE[res['decision']]}")
            c2.metric("Scam score", f"{res['prob']:.2f}", help=f"Decision threshold {res['threshold']:.2f}")
            c3.metric("Confidence", f"{res['confidence']:.2f}")
            st.info(res["advice"])
            if res["review_reasons"]:
                st.warning("Sent to human review: " + ", ".join(res["review_reasons"]))
            if res["flags"]:
                st.markdown("**Warning signs found:**")
                for f in res["flags"]:
                    st.markdown(f"- {FLAG_NAMES.get(f, f)}")
            with st.expander("Details"):
                st.json({k: res[k] for k in ("scores", "nearest_sim", "is_unknown", "lang", "model_version",
                                             "drift_level", "safe_mode")})

# --------------------------------------------------------------------------
with tab_monitor:
    st.subheader("Live monitoring")
    st.caption("Signals are computed over the last 50 predictions and compared with limits learnt "
               "from normal traffic.")
    d1, d2, d3, d4, d5 = st.columns(5)
    if d1.button("▶ Stream 60 normal posts"):
        with st.spinner("streaming…"):
            api("POST", "/demo/stream", json={"dataset": "live_normal", "n": 60,
                                              "offset": st.session_state.get("off_n", 0)})
        st.session_state["off_n"] = st.session_state.get("off_n", 0) + 60
        st.rerun()
    if d2.button("⚡ Stream 100 shifted posts"):
        with st.spinner("streaming new scam tactics…"):
            api("POST", "/demo/stream", json={"dataset": "shifted", "n": 100,
                                              "offset": st.session_state.get("off_s", 0)})
        st.session_state["off_s"] = st.session_state.get("off_s", 0) + 100
        st.rerun()
    if d3.button("👥 Simulate reviewers"):
        r = api("POST", "/demo/auto_review")
        if r:
            st.toast(f"Labelled {r['labelled']} posts")
        st.rerun()
    if d4.button("🔁 Retrain now"):
        api("POST", "/retrain")
        st.rerun()
    if d5.button("↺ Reset demo"):
        api("POST", "/demo/reset")
        st.session_state.clear()
        st.rerun()

    st.markdown(f"### {LEVEL_BADGE.get(status.get('level'), '-')}")
    if status.get("signals"):
        cols = st.columns(3)
        for col, (key, s) in zip(cols, status["signals"].items()):
            arrow = "below" if key == "confidence_mean" else "above"
            col.metric(SIGNAL_NAMES[key], f"{s['value']:.3f}",
                       delta=f"{s['value'] - s['baseline']:+.3f} vs normal",
                       delta_color="inverse" if key != "confidence_mean" else "normal")
            col.caption(("🔴 FIRED" if s["fired"] else "🟢 within limit") + f" (alert if {arrow} {s['limit']:.3f})")
        m1, m2, m3 = st.columns(3)
        m1.metric("Scam rate in window", f"{status['scam_rate']:.0%}")
        m2.metric("Sent to review", f"{status['review_rate']:.0%}")
        m3.markdown("**Language mix:** " + ", ".join(f"{k} {v:.0%}" for k, v in status["lang_mix"].items()))
    elif status:
        st.info(f"Collecting traffic: {status.get('window', 0)}/{status.get('needed', 25)} predictions")

    recent = api("GET", "/monitor/recent", params={"n": 300}) or []
    if recent:
        df = pd.DataFrame(recent).sort_values("id")
        df["rolling confidence"] = df.confidence.rolling(20, min_periods=1).mean()
        df["rolling similarity to training data"] = df.nearest_sim.rolling(20, min_periods=1).mean()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Rolling model confidence** (20-post average)")
            st.line_chart(df.set_index("id")["rolling confidence"], height=220)
        with c2:
            st.markdown("**Rolling similarity to training data** (20-post average)")
            st.line_chart(df.set_index("id")["rolling similarity to training data"], height=220)

    al = api("GET", "/monitor/alerts") or {}
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Alerts**")
        if al.get("alerts"):
            st.dataframe(pd.DataFrame(al["alerts"])[["ts", "level", "message", "model_version"]],
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No alerts yet")
    with c2:
        st.markdown("**Response events** (safe mode, retraining, promotion)")
        if al.get("events"):
            ev = pd.DataFrame(al["events"])
            st.dataframe(ev[["ts", "kind", "detail"]], hide_index=True, use_container_width=True)
        else:
            st.caption("No events yet")

# --------------------------------------------------------------------------
with tab_review:
    q = api("GET", "/review/queue") or {}
    counts = q.get("counts", {})
    st.subheader("Human review queue")
    st.caption("Uncertain and unfamiliar posts land here. Reviewed labels feed the retraining trigger "
               "(retrain starts automatically at 30 labels during a drift alert).")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending", counts.get("pending", 0))
    c2.metric("Labelled", counts.get("labelled", 0))
    c3.metric("Used in retraining", counts.get("used", 0))
    for item in q.get("items", [])[:15]:
        with st.container(border=True):
            st.markdown(f"**#{item['id']}** · score {item['prob']:.2f} · {item['lang']} · _{item['reason']}_")
            st.text(item["text_redacted"])
            b1, b2, _ = st.columns([1, 1, 6])
            if b1.button("Scam", key=f"s{item['id']}"):
                api("POST", f"/review/{item['id']}", json={"label": 1})
                st.rerun()
            if b2.button("Legit", key=f"l{item['id']}"):
                api("POST", f"/review/{item['id']}", json={"label": 0})
                st.rerun()

# --------------------------------------------------------------------------
with tab_model:
    st.subheader("Held-out evaluation (serving model)")
    if model.get("test"):
        rows = []
        for split in ("test", "shifted_holdout"):
            for mname, per_src in model[split].items():
                for src, m in per_src.items():
                    rows.append({"split": split, "model": mname, "data": src,
                                 **{k: m.get(k) for k in ("n", "scams", "precision", "recall", "f1", "pr_auc")}})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown("**Model registry**")
    if model.get("registry"):
        st.dataframe(pd.DataFrame(model["registry"]["history"]), hide_index=True, use_container_width=True)
