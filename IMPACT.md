# Impact statement: JobShield LK

## Who is protected
Sri Lankans looking for work abroad, and the families who pay for it. Most are from rural areas and lower-income households. Many are first-time migrants, women going into domestic work, and young workers chasing new destinations like Europe, Japan and Korea. They find jobs through Facebook, TikTok and WhatsApp posts written in Sinhala, English or Singlish. These are channels where nobody checks whether an "agency" is licensed.

## How many people we could reach
- A record **~313,000 Sri Lankans left for foreign employment in 2024** (SLBFE figures reported by Ada Derana and The Daily Morning). Job seekers who *answer* posts are a multiple of those who actually leave.
- Each departing worker typically supports a household, so the families exposed number in the high hundreds of thousands each year.
- **Year-one target:** 50,000 posts checked, through the web checker and SLBFE district offices.

## Harm we prevent
- Victims pay "registration fees", "deposits" and "visa fees" upfront, often with borrowed money or pawned jewellery. In one 2025 case, 10 victims lost **Rs. 14.9 million** (about Rs. 1.5 million each) to a fake Canada-jobs scheme. Another scheme using a licensed agency's name took about **Rs. 200 million** for fake European hospitality jobs.
- The SLBFE recovered and refunded **over Rs. 194.5 million** to victims between October 2025 and February 2026. That covers only the cases that were reported and recovered.
- The SLBFE reports that complaints about social-media job fraud are **rising daily**, and most of the ads it investigated were fake.

**Measurable outcomes for a pilot:**
1. Posts checked and the share flagged as high risk
2. Rupees at risk avoided (flagged posts × fee demanded in the post)
3. Reports forwarded to the SLBFE Special Investigation Unit
4. Time from a new scam tactic appearing to the model being retrained, measured by our drift monitor

## Why staying power matters here
Scammers switch destinations, payment tricks and channels quickly, and now copy official SLBFE programme wording. A static filter silently stops catching them. JobShield detects that drift, sends uncertain posts to human review, and retrains with reviewed labels, only promoting a new model if it is measurably better.

## Realistic path to adoption
1. **Month 0–1, public checker:** a free web tool (this repo) in Sinhala and English. Every warning points to SLBFE licence checks and the SLBFE 1989 hotline.
2. **Month 1–3, SLBFE pilot:** the Special Investigation Unit uses the review queue to triage reported ads. Their labels become our retraining data. We add a lookup against the SLBFE licensed-agency register.
3. **Month 3–6, reach rural users:** SLBFE district officers and Development Officers use the checker during pre-departure counselling. Add a WhatsApp forwarding bot.
4. **Partners:** CBSL's "Be Scam Proof" campaign for awareness; Sri Lanka CERT|CC for tactic sharing; social platforms for bulk takedown reports.

**Cost:** runs on a single CPU server, with no GPU and no paid API.

*Sources: Ada Derana, "Over 300,000 Sri Lankans left for foreign employment in 2024"; The Daily Morning (RTI data, 2025); Daily FT, "SLBFE busts major foreign job scandals"; Ada Derana, "Two arrested for defrauding Rs. 200 million by promising employment in Europe" (Oct 2025); Ada Derana, "Over Rs. 194.5 million recovered and refunded to foreign employment scam victims: SLBFE" (Mar 2026); Hiru News on rising social-media job-fraud complaints.*
