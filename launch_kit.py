"""Channel launch kit: the ready-to-use pieces for one channel from a strategy.

The strategy report says where to show up and why. Beta clients asked for the
next step: "tangible step by step actions", copy they can paste, and leads
that are real people who meet their criteria. A launch kit takes one channel
(e.g. "LinkedIn" with a $300-500/mo test budget) and produces:

    posts             dated, ready-to-paste posts with a call to action
    ads               ad copy, only when the channel has a paid budget
    lead_form         qualifying questions that screen out unqualified leads,
                      plus how the platform's form works, for owners new to it
    targeting         platform settings to enter
    budget            total, daily, schedule and a stop rule
    reply_scripts     what to send when someone responds
    checklist         dated steps, each with how to know it is done
    success_measures  numbers to hit and when to check them

Kept free of Streamlit, like strategy_report, so it can be unit tested.
"""

import html
import json

import strategy_report

KIT_MAX_TOKENS = 12000
# Worst case: 12K output tokens at $0.015/1K plus a few thousand input tokens.
ESTIMATED_COST_PER_KIT = 0.20


def build_kit_prompt(context_text, channel, business_name="", start_date=None, key_dates="", budget="", notes=""):
    business_line = f"The business is called {business_name}." if business_name.strip() else "Infer the business's name from the text if it is stated; otherwise use an empty string."
    budget_line = f"Ad budget for this channel: {budget.strip()}." if budget.strip() else "No ad budget was given, so treat this as an organic launch unless the strategy below gives this channel a budget."
    notes_line = f"Extra notes from the owner: {notes.strip()}" if notes.strip() else ""
    return f"""You are a senior marketing strategist at Databite. Below is a strategy (or notes) for one small business. {business_line} The owner asked for tangible, step-by-step actions and ready-to-use copy, not more strategy, and only counts a lead if it is a real person who meets their criteria.

Build a launch kit for this one channel: {channel}. {strategy_report.plan_dates_line(start_date, key_dates)} {budget_line} {notes_line}

Write everything so the owner can copy, paste and do it without another meeting. Address them as "you" in instructions, and write post and ad copy in the owner's own voice. Name their real products, segments, assets and geography. Do not invent statistics or client results; leave a [bracketed placeholder] where a real number or story from the owner is needed.

Sections to produce:

1. goal: one sentence on what this launch should achieve.
2. qualified_lead: one sentence defining a qualified lead for this business (the criteria a person must meet to be worth an appointment).
3. posts: 8-12 organic posts for this channel, in publishing order. Each has "date", "title" (a few words), "copy" (the full post, ready to paste, in the channel's normal length and format) and "call_to_action" (the exact last line, e.g. a keyword to message back). Mix formats the channel supports.
4. ads: if this channel has an ad budget, 2-3 ad variations to test, each with "name", "audience" (which segment it targets), "headline", "primary_text" and "cta_button" (a button label the platform offers). Otherwise an empty list.
5. lead_form: if there are ads, the lead form they point to: "headline", "intro" (1-2 sentences), "questions" (3-5 short multiple-choice qualifying questions, each with "question", "answers" (a list of choices) and "qualifies_if" (which answers make a qualified lead)), "privacy_note" (one line) and "thank_you" (what the person sees after submitting, including what happens next) and "how_it_works" (4-5 plain-language steps, in order, for an owner who has never used this platform's lead forms: where to create the form and attach it to the ad (name the platform's own tool, e.g. LinkedIn Lead Gen Forms in Campaign Manager or Meta Instant Forms in Ads Manager), what the prospect sees when they click the ad button (the form opens on the platform, pre-filled from their profile, no website needed), where submitted leads arrive and how the owner is notified, and how to check answers against qualifies_if and reply within 24 hours using the reply scripts). The questions must screen out people who do not meet the qualified_lead criteria. Without ads, return an object with empty strings and an empty questions list.
6. targeting: settings to enter on the platform, 4-8 rows of "setting" and "value" (e.g. location, job titles, company size, age, interests, exclusions). For an organic channel, describe who to connect with or which groups to join instead.
7. budget: "total" (for the launch period), "daily", "schedule" (when ads run, around the owner's dates) and "stop_rule" (the result that means pause or change the ads). For an organic channel, use "No ad spend" and a stop rule for the posting effort.
8. reply_scripts: 2-4 messages to send when someone responds (a DM, a comment, a form lead), each with "situation" and "message". Each moves a qualified person toward booking an appointment within 24 hours.
9. checklist: 8-15 steps in order, covering setup, launch and review. Each has "date", "step" (one concrete action) and "done_when" (how the owner knows it is finished).
10. success_measures: 2-4 rows, each with "metric", "target" (a number) and "check_on" (a date), including qualified leads and booked appointments.

Keep copy tight and every instruction to 1-2 sentences.

Respond with ONLY valid JSON, no other text, no markdown code fences, in exactly this shape:
{{
  "business_name": "...",
  "channel": "...",
  "goal": "...",
  "qualified_lead": "...",
  "posts": [{{"date": "...", "title": "...", "copy": "...", "call_to_action": "..."}}],
  "ads": [{{"name": "...", "audience": "...", "headline": "...", "primary_text": "...", "cta_button": "..."}}],
  "lead_form": {{"headline": "...", "intro": "...", "questions": [{{"question": "...", "answers": ["...", "..."], "qualifies_if": "..."}}], "privacy_note": "...", "thank_you": "...", "how_it_works": ["...", "..."]}},
  "targeting": [{{"setting": "...", "value": "..."}}],
  "budget": {{"total": "...", "daily": "...", "schedule": "...", "stop_rule": "..."}},
  "reply_scripts": [{{"situation": "...", "message": "..."}}],
  "checklist": [{{"date": "...", "step": "...", "done_when": "..."}}],
  "success_measures": [{{"metric": "...", "target": "...", "check_on": "..."}}]
}}

Strategy or notes:
\"\"\"
{context_text}
\"\"\"
"""


LIST_KEYS = ["posts", "ads", "targeting", "reply_scripts", "checklist", "success_measures"]
LEAD_FORM_FIELDS = ["headline", "intro", "privacy_note", "thank_you"]
BUDGET_FIELDS = ["total", "daily", "schedule", "stop_rule"]


def normalize_kit(kit):
    """Fill in missing sections so rendering never has to guard a key."""
    kit = dict(kit)
    for key in ("business_name", "channel", "goal", "qualified_lead"):
        kit[key] = kit.get(key) or ""
    for key in LIST_KEYS:
        kit[key] = kit.get(key) or []
    form = kit.get("lead_form") or {}
    kit["lead_form"] = {field: form.get(field) or "" for field in LEAD_FORM_FIELDS}
    kit["lead_form"]["questions"] = form.get("questions") or []
    kit["lead_form"]["how_it_works"] = [str(step) for step in form.get("how_it_works") or []]
    for q in kit["lead_form"]["questions"]:
        q["answers"] = [str(a) for a in q.get("answers") or []]
    budget = kit.get("budget") or {}
    kit["budget"] = {field: budget.get(field) or "" for field in BUDGET_FIELDS}
    return kit


def validate_kit(kit):
    """Human-readable problems with a normalized kit; empty means complete."""
    issues = []
    if not kit["posts"]:
        issues.append("No posts.")
    if kit["ads"] and not kit["lead_form"]["questions"]:
        issues.append("Ads are included but the lead form has no qualifying questions.")
    if kit["lead_form"]["questions"] and not kit["lead_form"]["how_it_works"]:
        issues.append("The lead form doesn't explain how it works on the platform.")
    for q in kit["lead_form"]["questions"]:
        if not q.get("qualifies_if"):
            issues.append(f"Lead form question '{q.get('question', '?')}' doesn't say which answers qualify.")
    if not kit["checklist"]:
        issues.append("No checklist.")
    if not kit["success_measures"]:
        issues.append("No success measures.")
    return issues


def parse_kit(result_text, truncated=False):
    """Parse the model's JSON into a normalized kit, salvaging complete
    sections from a cut-off response. Raises on unusable output."""
    text = result_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        kit = json.loads(text)
    except json.JSONDecodeError:
        kit = strategy_report.repair_truncated_json(text) if truncated else None
        if kit is None:
            raise
    if not isinstance(kit, dict):
        raise ValueError("Launch kit is not a JSON object.")
    return normalize_kit(kit)


def kit_title(kit):
    title = f"{kit['channel']} Launch Kit".strip()
    return title + (f": {kit['business_name']}" if kit["business_name"] else "")


def kit_to_markdown(kit):
    lines = [f"# {kit_title(kit)}", ""]
    if kit["goal"]:
        lines += [f"**Goal:** {kit['goal']}", ""]
    if kit["qualified_lead"]:
        lines += [f"**A qualified lead is:** {kit['qualified_lead']}", ""]
    lines += ["## Checklist", ""]
    for item in kit["checklist"]:
        lines.append(f"- [ ] **{item.get('date', '')}:** {item.get('step', '')} *Done when: {item.get('done_when', '')}*")
    lines += ["", "## Success measures", "", "| Metric | Target | Check on |", "|---|---|---|"]
    for m in kit["success_measures"]:
        lines.append("| " + " | ".join(str(m.get(k, "")).replace("|", "/") for k in ("metric", "target", "check_on")) + " |")
    lines += ["", "## Posts", ""]
    for i, post in enumerate(kit["posts"], 1):
        lines += [f"### {i}. {post.get('date', '')}: {post.get('title', '')}", "", post.get("copy", ""), "", f"**Call to action:** {post.get('call_to_action', '')}", ""]
    if kit["ads"]:
        lines += ["## Ads", ""]
        for ad in kit["ads"]:
            lines += [f"### {ad.get('name', '')}", f"- Audience: {ad.get('audience', '')}", f"- Headline: {ad.get('headline', '')}",
                      f"- Text: {ad.get('primary_text', '')}", f"- Button: {ad.get('cta_button', '')}", ""]
    form = kit["lead_form"]
    if form["questions"]:
        lines += ["## Lead form", ""]
        if form["how_it_works"]:
            lines += ["**How it works**", ""] + [f"{i}. {step}" for i, step in enumerate(form["how_it_works"], 1)] + ["", "**The form**", ""]
        lines += [f"**{form['headline']}** {form['intro']}", ""]
        for i, q in enumerate(form["questions"], 1):
            lines.append(f"{i}. {q.get('question', '')} ({' / '.join(q['answers'])}). *Qualifies if: {q.get('qualifies_if', '')}*")
        lines += ["", f"Privacy: {form['privacy_note']}", "", f"Thank-you screen: {form['thank_you']}", ""]
    if kit["targeting"]:
        lines += ["## Targeting", ""] + [f"- **{t.get('setting', '')}:** {t.get('value', '')}" for t in kit["targeting"]] + [""]
    budget = kit["budget"]
    if any(budget.values()):
        lines += ["## Budget", "", f"- Total: {budget['total']}", f"- Daily: {budget['daily']}", f"- Schedule: {budget['schedule']}", f"- Stop rule: {budget['stop_rule']}", ""]
    if kit["reply_scripts"]:
        lines += ["## Reply scripts", ""]
        for r in kit["reply_scripts"]:
            lines += [f"**{r.get('situation', '')}**", "", f"> {r.get('message', '')}", ""]
    return "\n".join(lines).rstrip() + "\n"


KIT_CSS = strategy_report.REPORT_CSS + """
.post { border:1px solid var(--line); border-top:2px solid var(--accent); padding:12px 16px; margin-bottom:12px; }
.post p { margin:6px 0 0; white-space:pre-wrap; }
.post .cta { color:var(--accent); font-weight:500; }
.check { display:grid; grid-template-columns:22px 110px 1fr; gap:6px; margin-bottom:10px; }
.check::before { content:"\\2610"; color:var(--accent); }
.check p { margin:2px 0 0; color:var(--muted); font-size:12.5px; }
blockquote { margin:6px 0 14px; padding:8px 14px; border-left:3px solid var(--accent); background:var(--chip); }
"""


def kit_to_html(kit, month_label="", prepared_by="Databite"):
    """Standalone, print-ready HTML in the same look as the strategy report."""
    e = lambda s: html.escape(str(s or ""))
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{e(kit_title(kit))}</title>",
        "<link href='https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Inter:wght@400;500;600&display=swap' rel='stylesheet'>",
        f"<style>{KIT_CSS}</style></head><body><div class='page'>",
        f"<div class='eyebrow'>{e(prepared_by)} &middot; Launch kit</div>",
        f"<h1>{e(kit['channel'])} Launch Kit</h1>",
    ]
    if kit["business_name"]:
        parts.append(f"<p class='subtitle'>{e(kit['business_name'])}</p>")
    meta = [m for m in (month_label, f"Prepared by {prepared_by}", "Confidential") if m]
    parts.append("<div class='meta'>" + "".join(f"<span>{e(m)}</span>" for m in meta) + "</div>")
    if kit["goal"] or kit["qualified_lead"]:
        parts.append("<div class='combos'>")
        if kit["goal"]:
            parts.append(f"<p><strong>Goal:</strong> {e(kit['goal'])}</p>")
        if kit["qualified_lead"]:
            parts.append(f"<p><strong>A qualified lead is:</strong> {e(kit['qualified_lead'])}</p>")
        parts.append("</div>")

    parts += ["<div class='section-label'>01 &mdash; Checklist</div>", "<h2>Step by step</h2>"]
    for item in kit["checklist"]:
        parts.append(f"<div class='check'><strong>{e(item.get('date'))}</strong><div>{e(item.get('step'))}<p>Done when: {e(item.get('done_when'))}</p></div></div>")
    if kit["success_measures"]:
        parts.append("<table><thead><tr><th>Success measure</th><th>Target</th><th>Check on</th></tr></thead><tbody>")
        for m in kit["success_measures"]:
            parts.append(f"<tr><td>{e(m.get('metric'))}</td><td>{e(m.get('target'))}</td><td>{e(m.get('check_on'))}</td></tr>")
        parts.append("</tbody></table>")

    parts += ["<div class='section-label'>02 &mdash; Posts</div>", "<h2>Ready to paste</h2>"]
    for post in kit["posts"]:
        parts.append(f"<div class='post'><div class='card-label'>{e(post.get('date'))}</div><div class='card-title'>{e(post.get('title'))}</div>"
                     f"<p>{e(post.get('copy'))}</p><p class='cta'>{e(post.get('call_to_action'))}</p></div>")

    section = 3
    if kit["ads"]:
        parts += [f"<div class='section-label'>0{section} &mdash; Ads</div>", "<h2>Ad variations to test</h2>",
                  "<table><thead><tr><th>Ad</th><th>Copy</th><th>Button</th></tr></thead><tbody>"]
        for ad in kit["ads"]:
            parts.append(f"<tr><td style='width:24%'><strong>{e(ad.get('name'))}</strong><span class='budget'>{e(ad.get('audience'))}</span></td>"
                         f"<td><strong>{e(ad.get('headline'))}</strong><br>{e(ad.get('primary_text'))}</td><td style='width:16%'>{e(ad.get('cta_button'))}</td></tr>")
        parts.append("</tbody></table>")
        section += 1
    form = kit["lead_form"]
    if form["questions"]:
        parts += [f"<div class='section-label'>0{section} &mdash; Lead form</div>"]
        if form["how_it_works"]:
            parts += ["<h2>How the lead form works</h2><ol>"] + [f"<li>{e(step)}</li>" for step in form["how_it_works"]] + ["</ol>"]
        parts += [f"<h2>{e(form['headline']) or 'Lead form'}</h2>", f"<p>{e(form['intro'])}</p>",
                  "<div class='questions'><div class='eyebrow'>Qualifying questions</div><ol>"]
        for q in form["questions"]:
            parts.append(f"<li>{e(q.get('question'))}<p>{e(' / '.join(q['answers']))}</p><p>Qualifies if: {e(q.get('qualifies_if'))}</p></li>")
        parts.append(f"</ol></div><p><strong>Privacy:</strong> {e(form['privacy_note'])}</p><p><strong>Thank-you screen:</strong> {e(form['thank_you'])}</p>")
        section += 1
    if kit["targeting"] or any(kit["budget"].values()):
        parts += [f"<div class='section-label'>0{section} &mdash; Targeting and budget</div>", "<h2>Settings to enter</h2>", "<table><tbody>"]
        for t in kit["targeting"]:
            parts.append(f"<tr><td style='width:28%'><strong>{e(t.get('setting'))}</strong></td><td>{e(t.get('value'))}</td></tr>")
        for field, label in (("total", "Total budget"), ("daily", "Daily budget"), ("schedule", "Schedule"), ("stop_rule", "Stop rule")):
            if kit["budget"][field]:
                parts.append(f"<tr><td><strong>{label}</strong></td><td>{e(kit['budget'][field])}</td></tr>")
        parts.append("</tbody></table>")
        section += 1
    if kit["reply_scripts"]:
        parts += [f"<div class='section-label'>0{section} &mdash; Reply scripts</div>", "<h2>When someone responds</h2>"]
        for r in kit["reply_scripts"]:
            parts.append(f"<p><strong>{e(r.get('situation'))}</strong></p><blockquote>{e(r.get('message'))}</blockquote>")

    footer_left = " &middot; ".join(e(x) for x in (prepared_by, "Launch kit", month_label) if x)
    parts.append(f"<div class='footer'><strong>{footer_left}</strong><span>{e(kit['business_name'])}</span></div>")
    parts.append("</div></body></html>")
    return "\n".join(parts)
