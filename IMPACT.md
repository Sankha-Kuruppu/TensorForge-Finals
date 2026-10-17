# Impact Statement: JobShield LK

> **Protecting Sri Lankan migrant workers and their families from foreign-employment recruitment fraud, with scam detection that notices when tactics change.**

---

## 1. Who is protected

JobShield LK protects Sri Lankans looking for work abroad, and the families who pay for it:

- **Rural and first-time job seekers** who find jobs through Facebook groups, TikTok and WhatsApp forwards, channels where nobody checks whether an "agency" is licensed, and who have no easy way to check the SLBFE licence register themselves.
- **Young workers chasing new destinations** (South Korea, Japan, Israel, Europe, Canada) who are targeted with fake work-visa offers that demand large upfront "deposits".
- **Women going into domestic work** abroad, approached by intermediaries charging "processing fees".
- **Their families**, who often borrow money or pawn jewellery to pay these fees.

Posts reach them in Sinhala, English or Singlish. Most scam filters only read English.

---

## 2. How many people could be reached

- **~313,000 Sri Lankans left for foreign employment in 2024**, a record (SLBFE figures). The number who see and answer overseas job posts is a multiple of that.
- Each departing worker typically supports a household, so hundreds of thousands of families are exposed every year.
- **Year-one target:** **50,000 job posts checked** through a free web checker and SLBFE district offices.

---

## 3. Measurable harm prevented

JobShield works **before money changes hands**: it flags the post when the job seeker first sees it.

- **The losses are large:** in one 2025 case, 10 victims lost **LKR 14.9 million** (about LKR 1.5 million each) to a fake Canada-jobs scheme. Another scheme, run through a Negombo agency that held a valid SLBFE licence, took about **LKR 200 million** for fake European hospitality jobs (arrests in October 2025). Between October 2025 and February 2026, SLBFE recovered and refunded **LKR 194.5 million**, and only for reported cases.
- **Complaints are rising:** SLBFE says complaints about job fraud promoted on social media are rising daily, and most ads it investigated were fake.
- **Evidence from our build:** when we simulated scammers changing tactics, the model alone would have called **39%** of the new scams safe; JobShield called **none** safe, because it noticed the change and sent them to human review. After reviewing and retraining, the new model catches them itself (F1 0.83 → 0.99).

**What a pilot measures:**
1. **Money at risk avoided:** confirmed scam posts × the fee each post demanded.
2. **Interception rate:** share of confirmed fake ads flagged before anyone paid.
3. **Triage time:** time SLBFE investigators spend per reported ad, with and without pre-computed risk scores.
4. **Time to adapt:** hours from a drift alert to a retrained, promoted model.

---

## 4. Realistic path to adoption

| Horizon | Milestone |
| :--- | :--- |
| **Month 0–1:** public web checker | Free checker in Sinhala and English. Every warning points the user to the SLBFE licence check and the **1989** SLBFE hotline. |
| **Month 1–3:** SLBFE Special Investigation Unit pilot | Investigators triage reported ads in our review queue; their verdicts become retraining data. Add a lookup against the SLBFE licensed-agency register. |
| **Month 3–6:** grassroots reach | SLBFE Development Officers in district offices use the checker during pre-departure registration. Add a WhatsApp forwarding bot and Tamil support. |
| **Ongoing:** partnerships | CBSL's "Be Scam Proof" campaign for awareness; Sri Lanka CERT\|CC for sharing new tactics; reports to social media platforms for takedowns. |

**Sustainability:** the whole detection and drift-monitoring pipeline runs on a single CPU server, with no GPU and no paid LLM API, so it is cheap for a government or non-profit to run long term.

---
*Sources: SLBFE departure figures via Ada Derana ("Over 300,000 Sri Lankans left for foreign employment in 2024") and The Daily Morning (RTI data); Daily FT, "SLBFE busts major foreign job scandals"; Ada Derana, "Two arrested for defrauding Rs. 200 million by promising employment in Europe" (Oct 2025); Ada Derana, "Over Rs. 194.5 million recovered and refunded to foreign employment scam victims: SLBFE" (Mar 2026); Hiru News on rising social-media job-fraud complaints. Model results: this repository's README and `reports/`.*
