"""Audience & Channel Strategy report: prompt, normalization and HTML rendering.

The schema extractor in app.py answers "what fields would a data team query?".
This module answers the question a small-business client actually asks:
"who is my best customer, and where and how do I reach them?". Its output
mirrors the six-section "Audience & Channel Strategy" one-pager Databite
delivered to its first pilot client by hand:

    01 Target audience     six profile cards plus audience tags
    02 Strategic insights  exactly four, each ending in one concrete action
    03 Channel plan        channel, priority, what to do, budget, outcome
    04 Hashtags            grouped tags plus suggested combos per post type
    05 Next 30 days        week-by-week actions
    06 Open questions      validation questions, each with why it matters

Kept free of Streamlit so it can be unit tested and reused by batch jobs.
"""

import html
import json
import re

# Long enough for a ~45 minute discovery call transcript (the pilot
# transcripts are ~18K characters), short enough to keep one report under
# roughly $0.15 of API spend.
MIN_SOURCE_LENGTH = 200
MAX_SOURCE_LENGTH = 40000
REPORT_MAX_TOKENS = 6000
ESTIMATED_COST_PER_REPORT = 0.15

AUDIENCE_CARDS = [
    ("core_profile", "Core profile"),
    ("sharpest_segment", "Sharpest segment"),
    ("why_they_hire", "Why they hire you"),
    ("what_makes_them_switch", "What makes them switch"),
    ("how_they_find_you", "How they find a new provider"),
    ("where_they_live_online", "Where they live online"),
]
CHANNEL_PRIORITIES = ["primary", "secondary", "later"]
INSIGHT_COUNT = 4
MAX_TAGS_PER_POST = 5

SECTION_KEYS = ["audience", "audience_tags", "insights", "channel_plan", "hashtags", "actions_30_day", "validation_questions"]


def validate_source_input(text):
    stripped = text.strip()
    if len(stripped) < MIN_SOURCE_LENGTH:
        return False, f"Please paste the call transcript, notes or a detailed brief (at least {MIN_SOURCE_LENGTH} characters)."
    if len(stripped) > MAX_SOURCE_LENGTH:
        return False, f"That text is too long ({len(stripped)} characters, maximum {MAX_SOURCE_LENGTH}). Trim small talk or split the call into parts."
    return True, None


def build_report_prompt(source_text, business_name=""):
    business_line = f"The business is called {business_name}." if business_name.strip() else "Infer the business's name from the text if it is stated; otherwise use an empty string."
    return f"""You are a senior marketing strategist at Databite. Below is source material about one small business: usually a discovery call transcript between a Databite analyst and the business owner, sometimes notes or a brief. {business_line}

Write an "Audience & Channel Strategy" for the owner. Address them directly as "you". Be specific to this business: name their real products, existing assets (newsletters, groups, birthday messages, apps, referral habits), customer segments, geography and deadlines exactly as they describe them. Never write advice that would fit any business in the category. Base facts on what the business owner says; ignore filler, small talk and garbled or non-English transcription fragments. Do not invent statistics about the business; anything you estimate must read as an estimate.

Sections to produce:

1. audience: six short cards describing the highest-value client. Each card has a "title" (2-6 words, a crisp label such as "Established Canadian Professional") and a "body" (1-3 sentences).
   - core_profile: who the core customer is (age band, life stage, income, location, situation).
   - sharpest_segment: the narrowest, most profitable sub-segment this business is uniquely good at serving, and why.
   - why_they_hire: the job the customer hires this business to do, in the customer's terms.
   - what_makes_them_switch: what makes customers leave a competitor, and which of this business's existing habits or assets is the antidote.
   - how_they_find_you: how customers find a new provider (referral, search, social, events), in order of importance.
   - where_they_live_online: which platforms and private channels (including WhatsApp, community groups, email) matter and what each is for.
2. audience_tags: 6-10 short labels (1-4 words) summarising the audience, e.g. "Homeowners", "Dual-income households".
3. insights: exactly {INSIGHT_COUNT} strategic insights, most important first. Each has a "title" (one punchy sentence, may use an em dash), a "body" (2-4 sentences explaining the reasoning, including what competitors get wrong where relevant) and an "action" (one sentence: the specific thing to do, e.g. an exact line of copy to add or a posting cadence). At least one insight should turn an asset the business already has into a lead or referral source.
4. channel_plan: 4-6 rows ordered by priority. Each row: "channel" (a platform or a non-platform channel such as "Referral engine" or "Email newsletter"), "priority" (one of {CHANNEL_PRIORITIES}; "later" is for paid ads or anything that should wait until organic content converts), "what_to_do" (cadence and content, 1-2 sentences), "budget" (short, e.g. "Organic, no ad budget needed", "Zero cost", "$300-500/mo to test") and "expected_outcome" (one short sentence, framed as an estimate).
5. hashtags: for the single most important content platform. "platform" (its name), "guidance" (1-2 sentences on how many tags per post and how to mix them, at most {MAX_TAGS_PER_POST} per post), "groups" (3-4 groups, each with "label" such as "High-volume", "purpose" such as "Broad reach", and "tags": 4-6 hashtags) and "combos" (3-4 suggested combinations, each with "post_type" naming a concrete post idea and "tags": 3-{MAX_TAGS_PER_POST} hashtags drawn from the groups). Include location-specific tags if the business is local or national. Every hashtag starts with "#" and has no spaces.
6. actions_30_day: 3-5 steps for the next 30 days, in order. Each has "timeframe" (e.g. "Week 1", "Week 1-2", "Week 3-4"), "title" (a few words) and "detail" (1-2 sentences, concrete enough to do without another meeting, e.g. the exact first post title).
7. validation_questions: exactly 3 questions whose answers would most change this strategy. Each has "question" and "why_it_matters" (one sentence on what each possible answer would mean for the plan).

Respond with ONLY valid JSON, no other text, no markdown code fences, in exactly this shape:
{{
  "business_name": "...",
  "audience": {{
    "core_profile": {{"title": "...", "body": "..."}},
    "sharpest_segment": {{"title": "...", "body": "..."}},
    "why_they_hire": {{"title": "...", "body": "..."}},
    "what_makes_them_switch": {{"title": "...", "body": "..."}},
    "how_they_find_you": {{"title": "...", "body": "..."}},
    "where_they_live_online": {{"title": "...", "body": "..."}}
  }},
  "audience_tags": ["...", "..."],
  "insights": [{{"title": "...", "body": "...", "action": "..."}}],
  "channel_plan": [{{"channel": "...", "priority": "primary", "what_to_do": "...", "budget": "...", "expected_outcome": "..."}}],
  "hashtags": {{
    "platform": "...",
    "guidance": "...",
    "groups": [{{"label": "...", "purpose": "...", "tags": ["#...", "#..."]}}],
    "combos": [{{"post_type": "...", "tags": ["#...", "#..."]}}]
  }},
  "actions_30_day": [{{"timeframe": "...", "title": "...", "detail": "..."}}],
  "validation_questions": [{{"question": "...", "why_it_matters": "..."}}]
}}

Source material:
\"\"\"
{source_text}
\"\"\"
"""


def _clean_tag(tag):
    tag = re.sub(r"\s+", "", str(tag)).lstrip("#")
    return f"#{tag}" if tag else ""


def normalize_report(report):
    """Fill in missing sections with empty values and tidy fields the model
    sometimes formats loosely (hashtags without '#', priority casing), so
    rendering never has to guard against a missing key."""
    report = dict(report)
    report.setdefault("business_name", "")
    audience = report.get("audience") or {}
    report["audience"] = {key: {"title": (audience.get(key) or {}).get("title", ""), "body": (audience.get(key) or {}).get("body", "")} for key, _ in AUDIENCE_CARDS}
    for key in ("audience_tags", "insights", "channel_plan", "actions_30_day", "validation_questions"):
        report[key] = report.get(key) or []
    for row in report["channel_plan"]:
        row["priority"] = str(row.get("priority", "")).strip().lower()
    hashtags = report.get("hashtags") or {}
    hashtags.setdefault("platform", "")
    hashtags.setdefault("guidance", "")
    hashtags["groups"] = hashtags.get("groups") or []
    hashtags["combos"] = hashtags.get("combos") or []
    for group in hashtags["groups"] + hashtags["combos"]:
        group["tags"] = [t for t in (_clean_tag(t) for t in group.get("tags") or []) if t]
    report["hashtags"] = hashtags
    return report


def validate_report(report):
    """Return human-readable problems with a normalized report. An empty list
    means every section is present and within the shape the prompt asks for."""
    issues = []
    for key, label in AUDIENCE_CARDS:
        card = report["audience"][key]
        if not card["title"] or not card["body"]:
            issues.append(f"Audience card '{label}' is empty.")
    if len(report["insights"]) != INSIGHT_COUNT:
        issues.append(f"Expected {INSIGHT_COUNT} strategic insights, got {len(report['insights'])}.")
    if not report["channel_plan"]:
        issues.append("Channel plan is empty.")
    for row in report["channel_plan"]:
        if row["priority"] not in CHANNEL_PRIORITIES:
            issues.append(f"Channel '{row.get('channel', '?')}' has priority '{row['priority']}', expected one of {CHANNEL_PRIORITIES}.")
    if not report["hashtags"]["groups"]:
        issues.append("No hashtag groups.")
    for combo in report["hashtags"]["combos"]:
        if len(combo["tags"]) > MAX_TAGS_PER_POST:
            issues.append(f"Hashtag combo '{combo.get('post_type', '?')}' has {len(combo['tags'])} tags, more than {MAX_TAGS_PER_POST}.")
    if not report["actions_30_day"]:
        issues.append("No 30-day actions.")
    if not report["validation_questions"]:
        issues.append("No validation questions.")
    return issues


def parse_report(result_text):
    """Parse the model's JSON response into a normalized report dict.
    Raises json.JSONDecodeError or ValueError on unusable output."""
    text = result_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    report = json.loads(text)
    if not isinstance(report, dict):
        raise ValueError("Report is not a JSON object.")
    return normalize_report(report)


def report_to_markdown(report):
    """Plain-text version of the report, for pasting into email or a doc."""
    lines = [f"# Audience & Channel Strategy{': ' + report['business_name'] if report['business_name'] else ''}", ""]
    lines += ["## 01 Target audience", ""]
    for key, label in AUDIENCE_CARDS:
        card = report["audience"][key]
        lines.append(f"**{label}: {card['title']}.** {card['body']}")
        lines.append("")
    if report["audience_tags"]:
        lines += ["Tags: " + ", ".join(report["audience_tags"]), ""]
    lines += ["## 02 Strategic insights", ""]
    for i, insight in enumerate(report["insights"], 1):
        lines.append(f"{i}. **{insight.get('title', '')}** {insight.get('body', '')} **{insight.get('action', '')}**")
    lines += ["", "## 03 Channel plan", "", "| Channel | Priority | What to do | Budget | Expected outcome |", "|---|---|---|---|---|"]
    for row in report["channel_plan"]:
        cells = [row.get("channel", ""), row["priority"], row.get("what_to_do", ""), row.get("budget", ""), row.get("expected_outcome", "")]
        lines.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    hashtags = report["hashtags"]
    lines += ["", f"## 04 {hashtags['platform']} hashtags".replace("  ", " "), "", hashtags["guidance"], ""]
    for group in hashtags["groups"]:
        lines.append(f"- {group.get('label', '')} ({group.get('purpose', '')}): {' '.join(group['tags'])}")
    if hashtags["combos"]:
        lines += ["", "Suggested combo per post type:"]
        for combo in hashtags["combos"]:
            lines.append(f"- {combo.get('post_type', '')}: {' '.join(combo['tags'])}")
    lines += ["", "## 05 Next 30 days", ""]
    for step in report["actions_30_day"]:
        lines.append(f"- **{step.get('timeframe', '')}: {step.get('title', '')}.** {step.get('detail', '')}")
    lines += ["", "## 06 To sharpen this further", ""]
    for i, q in enumerate(report["validation_questions"], 1):
        lines.append(f"{i}. **{q.get('question', '')}** {q.get('why_it_matters', '')}")
    return "\n".join(lines) + "\n"


REPORT_CSS = """
:root { --ink:#1f2a24; --muted:#5b6560; --line:#d9ddd8; --accent:#1f3d2f; --chip:#e8f1ea; --warn:#b5541c; --amber:#f6e7b8; }
* { box-sizing: border-box; }
body { margin:0; background:#fff; color:var(--ink); font:14px/1.55 'Inter', -apple-system, 'Segoe UI', sans-serif; }
.page { max-width: 820px; margin: 0 auto; padding: 40px 32px 56px; }
h1, h2, h3, .card-title, .insight-title { font-family: 'Fraunces', Georgia, serif; }
.eyebrow { font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
h1 { font-size:34px; margin:6px 0 2px; letter-spacing:-.01em; }
.subtitle { font-family: Georgia, serif; font-style:italic; color:var(--muted); margin:0 0 14px; }
.meta { font-size:12px; color:var(--muted); display:flex; gap:18px; padding-bottom:18px; border-bottom:2px solid var(--accent); }
.meta span::before { content:"\\25CF"; color:var(--accent); font-size:8px; margin-right:6px; vertical-align:middle; }
.section-label { display:flex; align-items:center; gap:10px; margin:34px 0 4px; font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }
.section-label::after { content:""; flex:1; border-top:1px solid var(--line); }
h2 { font-size:22px; margin:6px 0 16px; }
.cards { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; }
.card { border:1px solid var(--line); border-top:2px solid var(--accent); padding:12px 14px; }
.card-label { font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
.card-title { font-size:16px; font-weight:600; margin:6px 0 4px; line-height:1.25; }
.card p { margin:0; font-size:12.5px; color:var(--muted); }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 4px; }
.chip { background:var(--chip); padding:4px 10px; font-size:12px; border-radius:2px; }
.insight { display:grid; grid-template-columns:36px 1fr; margin-bottom:16px; }
.insight-num { font-family: Georgia, serif; font-size:26px; color:#9aa79f; }
.insight-title { font-size:16px; font-weight:600; margin:0 0 4px; }
.insight p { margin:0; color:var(--muted); }
.insight strong { color:var(--ink); }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); font-weight:500; padding:8px 8px 8px 0; border-bottom:1px solid var(--ink); }
td { vertical-align:top; padding:12px 8px 12px 0; border-bottom:1px solid var(--line); }
.budget { display:block; color:var(--muted); font-size:12px; margin-top:2px; }
.badge { display:inline-block; font-size:9.5px; letter-spacing:.08em; text-transform:uppercase; padding:2px 6px; margin-left:6px; background:var(--chip); color:var(--accent); }
.badge.secondary { background:var(--amber); color:#7a5a00; }
.badge.later { background:#f3e3d6; color:var(--warn); }
.group-label { font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin:14px 0 2px; }
.combos { border:1px solid var(--line); border-left:4px solid var(--accent); padding:12px 16px; margin-top:16px; }
.combos p { margin:6px 0; }
.action { display:grid; grid-template-columns:22px 1fr; margin-bottom:12px; }
.action::before { content:"\\2192"; color:var(--warn); font-weight:700; }
.action p { margin:2px 0 0; color:var(--muted); }
.questions { border:1px solid var(--line); border-left:4px solid var(--warn); padding:14px 18px; }
.questions .eyebrow { color:var(--warn); margin-bottom:8px; }
.questions ol { margin:0; padding-left:20px; }
.questions li { margin-bottom:12px; font-weight:500; }
.questions li p { font-weight:400; color:var(--muted); margin:2px 0 0; font-size:13px; }
.footer { display:flex; justify-content:space-between; font-size:12px; border-top:1px solid var(--line); margin-top:36px; padding-top:12px; }
@media (max-width: 700px) { .cards { grid-template-columns:1fr; } .page { padding:24px 16px; } }
@media print { .page { padding:0; } .card, .insight, tr, .action, .questions li { break-inside: avoid; } }
"""


def report_to_html(report, month_label="", prepared_by="Databite"):
    """Standalone, print-ready HTML page laid out like the pilot PDF.
    Open it in a browser and use Print > Save as PDF to get the client file."""
    e = lambda s: html.escape(str(s or ""))
    name = report["business_name"]
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>Audience &amp; Channel Strategy{' - ' + e(name) if name else ''}</title>",
        "<link href='https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Inter:wght@400;500;600&display=swap' rel='stylesheet'>",
        f"<style>{REPORT_CSS}</style></head><body><div class='page'>",
        f"<div class='eyebrow'>{e(prepared_by)} &middot; Pilot analysis</div>",
        "<h1>Audience &amp; Channel Strategy</h1>",
    ]
    if name:
        parts.append(f"<p class='subtitle'>{e(name)}</p>")
    meta = [m for m in (month_label, f"Prepared by {prepared_by}", "Confidential") if m]
    parts.append("<div class='meta'>" + "".join(f"<span>{e(m)}</span>" for m in meta) + "</div>")

    parts += ["<div class='section-label'>01 &mdash; Target audience</div>", "<h2>Your highest-value client, defined</h2>", "<div class='cards'>"]
    for key, label in AUDIENCE_CARDS:
        card = report["audience"][key]
        parts.append(f"<div class='card'><div class='card-label'>{e(label)}</div><div class='card-title'>{e(card['title'])}</div><p>{e(card['body'])}</p></div>")
    parts.append("</div>")
    if report["audience_tags"]:
        parts.append("<div class='chips'>" + "".join(f"<span class='chip'>{e(t)}</span>" for t in report["audience_tags"]) + "</div>")

    parts += ["<div class='section-label'>02 &mdash; Strategic insights</div>", f"<h2>{_count_word(len(report['insights']))} things that change your approach</h2>"]
    for i, insight in enumerate(report["insights"], 1):
        action = f" <strong>{e(insight.get('action'))}</strong>" if insight.get("action") else ""
        parts.append(f"<div class='insight'><div class='insight-num'>{i}</div><div><div class='insight-title'>{e(insight.get('title'))}</div><p>{e(insight.get('body'))}{action}</p></div></div>")

    parts += ["<div class='section-label'>03 &mdash; Channel plan</div>", "<h2>Where to show up and what to do there</h2>",
              "<table><thead><tr><th>Channel</th><th>What to do</th><th>Expected outcome</th></tr></thead><tbody>"]
    for row in report["channel_plan"]:
        priority = row["priority"]
        badge = f"<span class='badge {e(priority)}'>{e(priority)}</span>" if priority else ""
        budget = f"<span class='budget'>{e(row.get('budget'))}</span>" if row.get("budget") else ""
        parts.append(f"<tr><td style='width:24%'>{e(row.get('channel'))}{badge}</td><td>{e(row.get('what_to_do'))}{budget}</td><td style='width:28%'>{e(row.get('expected_outcome'))}</td></tr>")
    parts.append("</tbody></table>")

    hashtags = report["hashtags"]
    if hashtags["groups"]:
        platform = hashtags["platform"]
        parts += [f"<div class='section-label'>04 &mdash; {e(platform)} hashtags</div>", "<h2>Tags that reach the right feed</h2>"]
        if hashtags["guidance"]:
            parts.append(f"<p>{e(hashtags['guidance'])}</p>")
        for group in hashtags["groups"]:
            label = " &mdash; ".join(e(x) for x in (group.get("label"), group.get("purpose")) if x)
            parts.append(f"<div class='group-label'>{label}</div><div class='chips'>" + "".join(f"<span class='chip'>{e(t)}</span>" for t in group["tags"]) + "</div>")
        if hashtags["combos"]:
            parts.append("<div class='combos'><div class='eyebrow'>Suggested combo per post type</div>")
            for combo in hashtags["combos"]:
                parts.append(f"<p>{e(combo.get('post_type'))} &mdash; {e(' '.join(combo['tags']))}</p>")
            parts.append("</div>")

    parts += ["<div class='section-label'>05 &mdash; Immediate actions</div>", "<h2>What to do in the next 30 days</h2>"]
    for step in report["actions_30_day"]:
        parts.append(f"<div class='action'><div><strong>{e(step.get('timeframe'))}: {e(step.get('title'))}</strong><p>{e(step.get('detail'))}</p></div></div>")

    if report["validation_questions"]:
        parts += ["<div class='section-label'>06 &mdash; To sharpen this further</div>", "<div class='questions'><div class='eyebrow'>A few things that would make the next round even more targeted</div><ol>"]
        for q in report["validation_questions"]:
            parts.append(f"<li>{e(q.get('question'))}<p>{e(q.get('why_it_matters'))}</p></li>")
        parts.append("</ol></div>")

    footer_right = f"Built from your discovery call{' &middot; ' + e(name) if name else ''}"
    footer_left = " &middot; ".join(e(x) for x in (prepared_by, "Pilot engagement", month_label) if x)
    parts.append(f"<div class='footer'><strong>{footer_left}</strong><span>{footer_right}</span></div>")
    parts.append("</div></body></html>")
    return "\n".join(parts)


def _count_word(n):
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
    return words.get(n, str(n))
