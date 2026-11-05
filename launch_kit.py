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
import re

import strategy_report

# The kit's JSON runs ~5-8K tokens and the model's thinking tokens count
# against the same budget; 12K cut real kits off before the checklist.
KIT_MAX_TOKENS = 32000
# Worst case: 32K output tokens at $0.015/1K plus a few thousand input tokens.
ESTIMATED_COST_PER_KIT = 0.50


def build_kit_prompt(context_text, channel, business_name="", start_date=None, key_dates="", budget="", notes="", source_text=""):
    """source_text is the original notes or transcript a strategy report was
    built from. The report is a summary, so passing the source keeps facts the
    report left out (e.g. that the owner built a product they mention)."""
    business_line = f"The business is called {business_name}." if business_name.strip() else "Infer the business's name from the text if it is stated; otherwise use an empty string."
    budget_line = f"Ad budget for this channel: {budget.strip()}." if budget.strip() else "No ad budget was given, so treat this as an organic launch unless the strategy below gives this channel a budget."
    notes_line = f"Extra notes from the owner: {notes.strip()}" if notes.strip() else ""
    return f"""You are a senior marketing strategist at Databite. Below is a strategy (or notes) for one small business. {business_line} The owner asked for tangible, step-by-step actions and ready-to-use copy, not more strategy, and only counts a lead if it is a real person who meets their criteria.

Build a launch kit for this one channel: {channel}. {strategy_report.plan_dates_line(start_date, key_dates)} {budget_line} {notes_line}

Write everything so the owner can copy, paste and do it without another meeting. Address them as "you" in instructions, and write post and ad copy in the owner's own voice. Name their real products, segments, assets and geography. Do not invent statistics or client results; leave a [bracketed placeholder] where a real number or story from the owner is needed.

Sections to produce:

1. goal: one sentence on what this launch should achieve.
2. qualified_lead: one sentence defining a qualified lead for this business (the criteria a person must meet to be worth an appointment).
3. posts: 8-12 organic posts for this channel, in publishing order. Each has "date", "title" (a few words), "copy" (the complete post exactly as the owner pastes it, in the channel's normal length and format, including its call to action and any hashtags) and "call_to_action" (the call-to-action line quoted from the copy, e.g. a keyword to message back). Mix formats the channel supports.
4. ads: if this channel has an ad budget, 2-3 ad variations to test, each with "name", "audience" (which segment it targets), "headline", "primary_text" and "cta_button" (a button label the platform offers that fits what the person gets, e.g. "Sign up" or "Learn more" for booking a call, never "Request demo" for a service business). Otherwise an empty list.
5. lead_form: if there are ads, the lead form they point to: "headline", "intro" (1-2 sentences), "questions" (3-5 short multiple-choice qualifying questions, each with "question", "answers" (a list of choices) and "qualifies_if" (which answers make a qualified lead)), "privacy_note" (one line) and "thank_you" (what the person sees after submitting, including what happens next) and "how_it_works" (4-5 plain-language steps, in order, for an owner who has never used this platform's lead forms: where to create the form and attach it to the ad (name the platform's own tool, e.g. LinkedIn Lead Gen Forms in Campaign Manager or Meta Instant Forms in Ads Manager), what the prospect sees when they click the ad button (the form opens on the platform, pre-filled from their profile, no website needed), where submitted leads arrive and how the owner is notified, and how to check answers against qualifies_if and reply within 24 hours using the reply scripts). The questions must screen out people who do not meet the qualified_lead criteria. Without ads, return an object with empty strings and an empty questions list.
6. targeting: settings to enter on the platform, 4-8 rows of "setting" and "value" (e.g. location, job titles, company size, age, interests, exclusions). For an organic channel, describe who to connect with or which groups to join instead.
7. budget: "total" (for the launch period), "daily", "schedule" (when ads run, around the owner's dates) and "stop_rule" (the result that means pause or change the ads). For an organic channel, use "No ad spend" and a stop rule for the posting effort.
8. reply_scripts: 2-4 messages to send when someone responds (a DM, a comment, a form lead), each with "situation" and "message". Each moves a qualified person toward booking an appointment within 24 hours.
9. checklist: 8-15 steps in order, covering setup, launch and review. Each has "date", "step" (one concrete action) and "done_when" (how the owner knows it is finished).
10. success_measures: 2-4 rows, each with "metric", "target" (a number; propose one from the budget and channel rather than leaving a placeholder) and "check_on" (a date), including qualified leads and booked appointments.

Keep copy tight and every instruction to 1-2 sentences. When one part of the kit mentions another, use its plain heading ("the lead form", "Qualifies if", "the stop rule", "the success measures", "the reply scripts"), never a JSON key name like qualifies_if or stop_rule, and never "above" or "below". Write the JSON keys in the order shown below, so the checklist, measures and lead form come before the long post copy.

Respond with ONLY valid JSON, no other text, no markdown code fences, in exactly this shape:
{{
  "business_name": "...",
  "channel": "...",
  "goal": "...",
  "qualified_lead": "...",
  "checklist": [{{"date": "...", "step": "...", "done_when": "..."}}],
  "success_measures": [{{"metric": "...", "target": "...", "check_on": "..."}}],
  "ads": [{{"name": "...", "audience": "...", "headline": "...", "primary_text": "...", "cta_button": "..."}}],
  "lead_form": {{"headline": "...", "intro": "...", "questions": [{{"question": "...", "answers": ["...", "..."], "qualifies_if": "..."}}], "privacy_note": "...", "thank_you": "...", "how_it_works": ["...", "..."]}},
  "targeting": [{{"setting": "...", "value": "..."}}],
  "budget": {{"total": "...", "daily": "...", "schedule": "...", "stop_rule": "..."}},
  "reply_scripts": [{{"situation": "...", "message": "..."}}],
  "posts": [{{"date": "...", "title": "...", "copy": "...", "call_to_action": "..."}}]
}}

Strategy or notes:
\"\"\"
{context_text}
\"\"\"
{_source_block(source_text)}"""


def _source_block(source_text):
    if not source_text.strip():
        return ""
    return f"""
Original notes or transcript the strategy was built from. Use it for facts the strategy leaves out, such as what the owner built, offers or has already tried, and describe those things in the owner's own terms. Where the two disagree on the plan, follow the strategy.
\"\"\"
{source_text.strip()}
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
    _tidy(kit)
    return kit


QUALIFIED_LEAD_PREFIX = re.compile(r"^\s*(a\s+)?qualified\s+lead\s+(is|=)\s*:?\s*", re.IGNORECASE)
# "the questions below." -> "the questions." Only before punctuation or the
# end, so "above $100K" or "below 30" stay as they are.
POSITION_WORD = re.compile(r"\s+(listed\s+|shown\s+)?(above|below)(?=[.,;:)]|$)", re.IGNORECASE)


def _squash(text):
    return re.sub(r"\W+", " ", str(text)).strip().lower()


def _tidy(kit):
    """Fix the wording slips the model makes even when told not to, so they
    never reach a client: a doubled "A qualified lead is" label, "above" or
    "below" (meaningless once sections move), and a call to action printed
    twice because it is also inside the post copy."""
    kit["qualified_lead"] = QUALIFIED_LEAD_PREFIX.sub("", kit["qualified_lead"])
    if kit["qualified_lead"]:
        kit["qualified_lead"] = kit["qualified_lead"][0].upper() + kit["qualified_lead"][1:]
    unplace = lambda text: POSITION_WORD.sub("", str(text or ""))
    for item in kit["checklist"]:
        for field in ("step", "done_when"):
            if item.get(field):
                item[field] = unplace(item[field])
    form = kit["lead_form"]
    form["how_it_works"] = [unplace(step) for step in form["how_it_works"]]
    for field in ("intro", "thank_you"):
        form[field] = unplace(form[field])
    for post in kit["posts"]:
        cta = _squash(post.get("call_to_action", ""))
        if cta and cta in _squash(post.get("copy", "")):
            post["call_to_action"] = ""


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
        lines += [f"**A qualified lead:** {kit['qualified_lead']}", ""]
    lines += ["## Checklist", ""]
    for item in kit["checklist"]:
        lines.append(f"- [ ] **{item.get('date', '')}:** {item.get('step', '')} *Done when: {item.get('done_when', '')}*")
    lines += ["", "## Success measures", "", "| Metric | Target | Check on |", "|---|---|---|"]
    for m in kit["success_measures"]:
        lines.append("| " + " | ".join(str(m.get(k, "")).replace("|", "/") for k in ("metric", "target", "check_on")) + " |")
    lines += ["", "## Posts", ""]
    for i, post in enumerate(kit["posts"], 1):
        lines += [f"### {i}. {post.get('date', '')}: {post.get('title', '')}", "", post.get("copy", ""), ""] + ([f"**Call to action:** {post['call_to_action']}", ""] if post.get("call_to_action") else [])
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
.chip.version { background:var(--chip); color:var(--accent); font-weight:600; }
.stats { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin:16px 0; }
.stat { border:1px solid var(--line); border-top:3px solid var(--accent); padding:14px 16px; }
.stat:nth-child(2) { border-top-color:var(--warn); }
.stat-num { font-family:'Fraunces', Georgia, serif; font-size:30px; line-height:1.1; color:var(--accent); }
.stat:nth-child(2) .stat-num { color:var(--warn); }
.stat-num.small { font-size:20px; }
.stat-label { font-size:12px; color:var(--muted); margin-top:6px; }
.glance { background:#eef3ef; padding:16px 20px; margin-top:6px; }
.glance .eyebrow { color:var(--accent); font-weight:600; margin-bottom:6px; }
.glance p { margin:6px 0; }
.check { display:grid; grid-template-columns:18px 118px 1fr; gap:10px; padding:10px 0; border-bottom:1px solid var(--line); break-inside:avoid; }
.check .box { width:13px; height:13px; border:1.5px solid var(--accent); margin-top:4px; }
.check .date { font-size:12px; font-weight:600; color:var(--accent); }
.check p { margin:2px 0 0; color:var(--muted); font-size:12.5px; }
.measures td.target { font-family:'Fraunces', Georgia, serif; font-size:18px; color:var(--warn); white-space:nowrap; }
.steps { background:#eef3ef; padding:14px 18px 6px; margin-bottom:18px; break-inside:avoid; }
.steps ol { margin:6px 0 8px; padding-left:20px; }
.steps li { margin-bottom:6px; }
.form { border:1px solid var(--line); border-radius:6px; padding:18px 20px; max-width:560px; break-inside:avoid; }
.form-title { font-family:'Fraunces', Georgia, serif; font-size:18px; font-weight:600; }
.form .intro { color:var(--muted); margin:4px 0 12px; }
.q { padding:10px 0; border-top:1px solid var(--line); }
.q-text { font-weight:500; }
.answers { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; }
.answer { border:1px solid var(--line); border-radius:999px; padding:2px 10px; font-size:12px; }
.answer.yes { border-color:var(--accent); background:var(--chip); color:var(--accent); font-weight:500; }
.qualifies { font-size:12px; color:var(--accent); }
.form-foot { font-size:12px; color:var(--muted); margin-top:10px; }
.ads { display:grid; grid-template-columns:1fr; gap:12px; }
.ad { border:1px solid var(--line); padding:14px 16px; break-inside:avoid; }
.ad .card-label { margin-bottom:4px; }
.ad-headline { font-weight:600; margin:4px 0; }
.ad p { margin:4px 0; color:var(--ink); }
.button { display:inline-block; background:var(--accent); color:#fff; border-radius:999px; padding:3px 12px; font-size:12px; margin-top:6px; }
.kv td:first-child { width:28%; font-weight:600; }
.script { border:1px solid var(--line); border-left:4px solid var(--accent); padding:10px 14px; margin-bottom:10px; break-inside:avoid; }
.script .situation { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
.script p { margin:4px 0 0; }
.post { border:1px solid var(--line); border-top:2px solid var(--accent); padding:12px 16px; margin-bottom:12px; break-inside:avoid; }
.post p { margin:6px 0 0; white-space:pre-wrap; }
.post .cta { color:var(--accent); font-weight:600; }
.placeholder { background:var(--amber); padding:0 3px; }
h2 { break-after:avoid; }
.section-label { break-after:avoid; }
@media (max-width: 700px) { .stats { grid-template-columns:1fr; } .check { grid-template-columns:18px 1fr; } .check .date { grid-column:2; } }
.keep { break-inside:avoid; }
@media print { @page { margin:0.6in; } }
"""


def _highlight_placeholders(escaped):
    """Shade [bracketed placeholders] so the owner sees what to fill in."""
    return re.sub(r"\[([^\[\]]{1,200})\]", r"<span class='placeholder'>[\1]</span>", escaped)


def _qualifies(answer, qualifies_if):
    """True when the answer appears as a whole phrase in the Qualifies-if text,
    so 'No' isn't marked just because 'None' or 'Not' appears there."""
    return bool(answer) and re.search(r"(?<!\w)" + re.escape(answer) + r"(?!\w)", qualifies_if, re.IGNORECASE) is not None


def _stat(number, label):
    size = "" if len(number) <= 8 else " small"
    return f"<div class='stat'><div class='stat-num{size}'>{number}</div><div class='stat-label'>{label}</div></div>"


def kit_to_html(kit, month_label="", prepared_by="Databite"):
    """Standalone, print-ready HTML in the look of Databite's hand-made
    client PDFs: an at-a-glance page first, then the steps, then the copy."""
    e = lambda s: html.escape(str(s or ""))
    copy = lambda s: _highlight_placeholders(e(s))
    form, budget = kit["lead_form"], kit["budget"]
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
    first_date = kit["checklist"][0].get("date") if kit["checklist"] else ""
    meta = [m for m in (month_label, f"Prepared by {prepared_by}", "Confidential") if m]
    start_chip = f"<span class='chip version'>Starts {e(first_date)}</span>" if first_date else ""
    parts.append("<div class='meta' style='align-items:center'>" + start_chip + "".join(f"<span>{e(m)}</span>" for m in meta) + "</div>")

    # At a glance: the three numbers that define the launch, then the goal.
    parts += ["<div class='section-label'>At a glance</div>", "<h2>Your launch on one page</h2>", "<div class='stats'>"]
    parts.append(_stat(e(budget["total"] or "No ad spend"), "Budget" + (f" &middot; {e(budget['daily'])}" if budget["daily"] else "")))
    if kit["success_measures"]:
        m = kit["success_measures"][0]
        parts.append(_stat(copy(m.get("target")), f"{e(m.get('metric'))}" + (f" by {e(m.get('check_on'))}" if m.get("check_on") else "")))
    parts.append(_stat(str(len(kit["checklist"])), f"dated steps &middot; {len(kit['posts'])} ready-to-post posts"))
    parts.append("</div>")
    if kit["goal"] or kit["qualified_lead"] or budget["stop_rule"]:
        parts.append("<div class='glance'><div class='eyebrow'>The plan at a glance</div>")
        if kit["goal"]:
            parts.append(f"<p><strong>Goal.</strong> {e(kit['goal'])}</p>")
        if kit["qualified_lead"]:
            parts.append(f"<p><strong>A qualified lead.</strong> {e(kit['qualified_lead'])}</p>")
        if budget["stop_rule"]:
            parts.append(f"<p><strong>Stop rule.</strong> {e(budget['stop_rule'])}</p>")
        parts.append("</div>")

    n = 0
    def section(label, heading):
        nonlocal n
        n += 1
        return [f"<div class='section-label'>{n:02d} &mdash; {label}</div>", f"<h2>{heading}</h2>"]

    if kit["checklist"]:
        parts += section("Checklist", "Step by step")
        for item in kit["checklist"]:
            parts.append(f"<div class='check'><div class='box'></div><div class='date'>{e(item.get('date'))}</div>"
                         f"<div>{copy(item.get('step'))}<p>Done when: {e(item.get('done_when'))}</p></div></div>")
    if kit["success_measures"]:
        parts.append("<div class='keep'><h2 style='margin-top:24px'>How you'll know it's working</h2><table class='measures'><thead><tr><th>Measure</th><th>Target</th><th>Check on</th></tr></thead><tbody>")
        for m in kit["success_measures"]:
            parts.append(f"<tr><td>{e(m.get('metric'))}</td><td class='target'>{copy(m.get('target'))}</td><td>{e(m.get('check_on'))}</td></tr>")
        parts.append("</tbody></table></div>")

    if form["questions"]:
        parts += section("Lead form", "Screen leads before you call")
        if form["how_it_works"]:
            parts.append("<div class='steps'><div class='eyebrow'>How the lead form works</div><ol>" + "".join(f"<li>{e(step)}</li>" for step in form["how_it_works"]) + "</ol></div>")
        parts.append(f"<div class='form'><div class='form-title'>{e(form['headline'])}</div><p class='intro'>{e(form['intro'])}</p>")
        for q in form["questions"]:
            qualifies = str(q.get("qualifies_if") or "")
            answers = "".join(f"<span class='answer{' yes' if _qualifies(a, qualifies) else ''}'>{e(a)}</span>" for a in q["answers"])
            parts.append(f"<div class='q'><div class='q-text'>{e(q.get('question'))}</div><div class='answers'>{answers}</div>"
                         f"<div class='qualifies'>Qualifies if: {e(qualifies)}</div></div>")
        parts.append(f"<div class='form-foot'><strong>Privacy:</strong> {e(form['privacy_note'])}<br><strong>Thank-you screen:</strong> {e(form['thank_you'])}</div></div>")

    if kit["ads"]:
        parts += section("Ads", "Ad variations to test") + ["<div class='ads'>"]
        for ad in kit["ads"]:
            parts.append(f"<div class='ad'><div class='card-label'>{e(ad.get('name'))} &middot; {e(ad.get('audience'))}</div>"
                         f"<p>{copy(ad.get('primary_text'))}</p><div class='ad-headline'>{copy(ad.get('headline'))}</div>"
                         f"<span class='button'>{e(ad.get('cta_button'))}</span></div>")
        parts.append("</div>")

    if kit["targeting"] or any(budget.values()):
        parts += section("Targeting and budget", "Settings to enter") + ["<table class='kv'><tbody>"]
        for t in kit["targeting"]:
            parts.append(f"<tr><td>{e(t.get('setting'))}</td><td>{e(t.get('value'))}</td></tr>")
        for field, label in (("total", "Total budget"), ("daily", "Daily budget"), ("schedule", "Schedule"), ("stop_rule", "Stop rule")):
            if budget[field]:
                parts.append(f"<tr><td>{label}</td><td>{e(budget[field])}</td></tr>")
        parts.append("</tbody></table>")

    if kit["reply_scripts"]:
        parts += section("Reply scripts", "When someone responds")
        for r in kit["reply_scripts"]:
            parts.append(f"<div class='script'><div class='situation'>{e(r.get('situation'))}</div><p>{copy(r.get('message'))}</p></div>")

    if kit["posts"]:
        parts += section("Posts", "Ready to paste")
        parts.append("<p class='intro' style='color:var(--muted)'>Shaded <span class='placeholder'>[brackets]</span> mark details only you can fill in.</p>")
        for post in kit["posts"]:
            parts.append(f"<div class='post'><div class='card-label'>{e(post.get('date'))}</div><div class='card-title'>{e(post.get('title'))}</div>"
                         f"<p>{copy(post.get('copy'))}</p>" + (f"<p class='cta'>{copy(post.get('call_to_action'))}</p>" if post.get("call_to_action") else "") + "</div>")

    footer_left = " &middot; ".join(e(x) for x in (prepared_by, "Launch kit", month_label) if x)
    parts.append(f"<div class='footer'><strong>{footer_left}</strong><span>{e(kit['business_name'])}</span></div>")
    parts.append("</div></body></html>")
    return "\n".join(parts)
