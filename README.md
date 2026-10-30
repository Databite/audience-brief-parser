# Databite Audience Toolkit

Client-ready Audience & Channel Strategy reports and channel launch kits for small businesses, plus audience schema extraction for ad agencies.

**Live demo:** https://audience-brief-parser-4dwtsrouwolbwzqdqsa6sb.streamlit.app/

A Streamlit app with three tabs:

- **Strategy report:** turns free text or a call transcript about a business into a client-ready, six-section Audience & Channel Strategy, with real dates and a success measure for every step, that you can download as HTML or Markdown.
- **Launch kit:** turns one channel from that strategy into everything needed to launch it: ready-to-paste posts, ad and lead form copy with qualifying questions, targeting, budget, reply scripts and a dated checklist.
- **For agencies:** two tools for ad agencies. **Single brief** converts a loosely written ad campaign brief into a structured, validated target audience description (so it can be handed to a data or ML team to query against first-party and third-party data), plus strategic insights and validation questions. **Batch mode** runs the same extraction over a CSV of up to 50 briefs.

## Run it locally (Mac)

You need Python 3 and an Anthropic API key.

```bash
git clone https://github.com/Databite/audience-brief-parser.git
cd audience-brief-parser

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

Streamlit opens the app at http://localhost:8501. Stop it with Ctrl+C.

Next time, from the repo folder, you only need:

```bash
source venv/bin/activate
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

Notes:

- On a Mac, use `python3`. Outside the venv, bare `pip` and `streamlit` usually aren't on your PATH, so always `source venv/bin/activate` first (your prompt shows `(venv)` when it's active).
- Instead of exporting the key each time, you can put it in `.streamlit/secrets.toml` as `ANTHROPIC_API_KEY = "sk-ant-..."`. The app checks Streamlit secrets first, then the environment variable. Both `.streamlit/secrets.toml` and `venv/` are gitignored.
- Usage logging to Google Sheets needs a service account (`gcp_service_account` in Streamlit secrets, or the JSON key file named in `SERVICE_ACCOUNT_FILE` in `app.py`, placed in the repo folder; it's gitignored). Without it, logging fails silently and the app works normally.
- After pulling new changes, re-run `pip install -r requirements.txt` inside the venv in case dependencies changed.

### Run the tests

```bash
source venv/bin/activate
pip install pytest
python -m pytest tests/
```

The tests cover the strategy report's prompt, validation and rendering (`strategy_report.py`), using a saved sample report in `tests/fixtures/`. They make no API calls.

## The problems this solves

The app answers two related questions, one for each kind of user.

**"What would a data team actually query?"** (Single brief and Batch mode, under For agencies.) An ad brief typically describes a target audience in plain human language, for example "environmentally conscious millennials with disposable income." That description isn't queryable against a real data system. A data team needs actual field values that match a defined schema. This tool does that translation and, critically, validates the AI's output against a fixed set of allowed values, so it never silently hands downstream systems a value that doesn't exist in the real data dictionary.

**"Who is my best customer, and where and how do I reach them?"** (Strategy report tab.) A small business owner usually can't answer that from a schema. They need a plain-language plan they can act on this month. The Strategy report turns what they say about their business, in notes or on a discovery call, into a client-ready Audience & Channel Strategy: who to target, which channels to use first, and what to do in the next 30 days. The Launch kit then turns one channel into copy and steps the owner can follow without another meeting. See [Strategy report](#strategy-report) and [Launch kit](#launch-kit) below.

## What it does

### Single brief and batch mode: audience schema extraction

1. Takes a free-text ad brief as input.
2. Sends it to Claude with a strict instruction to extract only fields and values from a predefined data dictionary, never to invent new categories.
3. Validates every returned value against the allowed list for that field, flagging anything that doesn't match.
4. Splits the results into two groups: first-party attributes (would be queried from the company's own CRM or customer data) and third-party attributes (would be queried from an external data provider). First-party values (purchase history, loyalty, email engagement) are inferred from what the brief says about existing customers, for example referrals and repeat clients suggest `repeat_customer`.
5. Surfaces any assumptions the model made when inferring a value from indirect language, and flags anything the brief mentions that has no matching value in the schema.
6. Adds 3 to 5 strategic insights that go beyond the schema (which channel to prioritize, which segment is underserved, what messaging angle fits) and 2 to 3 validation questions the business should answer next.

Briefs must be 15 to 3,000 characters.

#### Fields and allowed values

| Field | Source | Multi-value | Allowed values |
|---|---|---|---|
| `age_range` | 3rd party | yes | 13-17, 18-20, 21-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65-69, 70-74, 75+ |
| `gender` | 3rd party | no | Female, Male, Other Gender, Unknown Gender |
| `household_income` | 3rd party | no | Less than $10,000 up to $250,000+ (12 IAB bands) |
| `urbanization` | 3rd party | no | Rural up to Over 2M+ People (9 IAB bands) |
| `interests` | 3rd party | yes | 25 IAB top-level interest categories |
| `social_platforms` | 3rd party | yes | Instagram, TikTok, Facebook, LinkedIn, YouTube, Twitter/X, WhatsApp, Snapchat |
| `country` | 3rd party | no | Canada, United States, United Kingdom, Australia, India, Other |
| `employment_type` | 3rd party | yes | Employed professional, Small business owner (incorporated), Small business owner (unincorporated), Self-employed, Student, Retired |
| `purchase_history_segment` | 1st party | no | first_time_buyer, repeat_customer, high_value, lapsed |
| `loyalty_tier` | 1st party | no | none, bronze, silver, gold, platinum |
| `email_engagement` | 1st party | no | high, medium, low, unengaged |

Multi-value fields come back as comma-separated values and each one is validated separately. Single-value fields are validated whole, since some allowed values (like the income bands) contain commas. The full lists live in `DATA_DICTIONARY` in `app.py`.

## Batch mode

Upload a CSV with a `brief_text` column (up to 50 rows) to process multiple briefs at once; `test_batch.csv` is a sample. Before running, the tool estimates the batch's likely cost against your remaining session budget and refuses to start if it would exceed it, rather than running out of budget partway through. On the Premium plan you can also tick a box to generate a persona for each row, which adds a second API call per row and is included in the cost estimate. If the session cap is reached partway through anyway, the batch stops and shows the rows it finished. Results show a compact summary table plus an expandable detail view per row, with a downloadable CSV of the full output.

## Strategy report

The "Strategy report" tab turns free text about a business into a client-ready Audience & Channel Strategy, the same format as the one-pager Databite delivered by hand to its first pilot client.

**Input.** Pick the input type ("Free text (description, notes or brief)" or "Call transcript"), optionally enter the business name, then paste the text or upload a .txt file. Input must be 50 to 40,000 characters, enough for a roughly 45 minute call transcript. Set the plan start date (defaults to today) and, optionally, key dates or deadlines such as a festival or a busy season; the plan uses real calendar dates and times steps around them.

**Output.** Six sections:

1. **Target audience:** six profile cards (core profile, sharpest segment, why they hire you, what makes them switch, how they find a new provider, where they live online) plus audience tags.
2. **Strategic insights:** exactly four, each ending in one concrete action.
3. **Channel plan:** channel, priority (primary, secondary, later), what to do, budget, expected outcome and a success measure (a number, a check-in date and what to do if it's missed).
4. **Hashtags:** grouped tags for the most important content platform plus suggested combos per post type, at most five tags per post.
5. **Next 30 days:** dated actions, each with how to know it's done or working.
6. **Open questions:** validation questions, each with why it matters.

**Download.** As a print-ready HTML page (open it and print to PDF for the client) or as Markdown.

**Cost and limits.** One report is estimated at about $0.25 against the session cap. The response is allowed up to 16,000 output tokens so long reports aren't cut off; if one is still cut off, the app shows the sections that arrived, flags what's missing and warns you, instead of failing silently.

The prompt doesn't assume customers will refer or reply just because they're asked. Referral advice is based on how the owner says new clients arrive today, and any new ask is framed as a test with a success measure.

Prompt, validation and rendering live in `strategy_report.py`, which has no Streamlit dependency so it can be unit tested.

## Launch kit

The "Launch kit" tab builds from the strategy report made in the same session (pick one of its channels) or from a pasted strategy, notes or transcript (name the channel). Set the launch start date, an optional ad budget, key dates and any notes, such as who counts as a qualified lead.

**Output:**

- **Goal and qualified lead:** what the launch should achieve, and the criteria a person must meet to be worth an appointment.
- **Checklist:** 8 to 15 dated steps, each with how to know it's done, plus success measures with targets and check-in dates.
- **Posts:** 8 to 12 ready-to-paste posts, each ending in a call to action.
- **Ads and lead form** (only when the channel has a budget): 2 to 3 ad variations, and a lead form whose qualifying questions say which answers make a qualified lead, to screen out fake or unqualified leads.
- **Targeting and budget:** platform settings to enter, total and daily budget, schedule and a stop rule.
- **Reply scripts:** what to send when someone responds, aimed at booking a call within 24 hours.

Download it as print-ready HTML or Markdown. One kit is estimated at about $0.20 against the session cap and is logged as a `launch_kit` event. The code is in `launch_kit.py`, tested in `tests/test_launch_kit.py`.

## Audience persona generator (Premium feature)

After extracting a schema, an optional second step turns it into a short narrative persona, a name, a one-line tagline, a first-person quote, and a day-in-the-life paragraph, grounded strictly in the extracted schema values rather than inventing new detail. This maps to a deliverable boutique agencies already produce for their own clients, so it's built as the flagship Premium-tier feature rather than a generic add-on. See PRICING.md for the reasoning behind that choice.

A sidebar plan selector ("Basic" or "Premium") demonstrates this gating: Basic shows the persona section locked with an explanation, Premium unlocks the button. This selector is a UI simulation for demo purposes only, there's no real user account or billing system behind it, so it isn't real access control. See HANDOFF.md for what real entitlement enforcement would require.

## Built for real-world use, not just a demo

Beyond the core extraction logic, this includes several things a tool needs before a stranger can use it safely:

- **Input validation.** Empty, too-short, or excessively long briefs are rejected with a clear message before any API call is made, so no cost is wasted on invalid input.
- **Graceful failure handling.** If the AI service is down, rate-limited, or returns an error, the user sees a clear, readable message, never a raw Python traceback.
- **A session cost cap.** Usage is capped per session ($2.00 on Basic, $5.00 on Premium) to bound worst-case cost exposure from a single visitor, with the cap enforced before single extractions, batch runs and strategy reports.
- **A first-time user explainer.** The page leads with a one-line plain-language description of what the tool does; a collapsed section covers the deeper mechanics (the industry-standard schema, the two data categories, what the tool doesn't do) for anyone who wants it.
- **Operator-side usage logging.** Every API call attempt (single extraction, batch row, persona and strategy report, successful or failed) is logged to a Google Sheet as a timestamp, event type, cost and success flag, outside the user's browser session, so usage can be reviewed later even after the visitor's session ends. Logging is best-effort: if it fails for any reason, it fails silently and never blocks or breaks the user's actual request.

## Grounding in a real industry standard

The demographic and interest fields in this prototype are pulled directly from the [IAB Tech Lab Audience Taxonomy 1.1](https://github.com/InteractiveAdvertisingBureau/Taxonomies), the ad industry's actual public standard for describing audience segments, rather than invented categories.

First-party fields (purchase history segment, loyalty tier, email engagement) are illustrative placeholders, since no public standard exists for internal CRM segmentation, that data model is proprietary to each company.

## A note on data

This is a public prototype with no privacy policy or data handling agreement, see HANDOFF.md's Stage 5 section for what's missing. The live app displays a warning asking visitors not to paste real client or campaign information, use a fictional or sample brief instead.

## Known limitations

1. **Truncated responses at low token limits.** Longer briefs occasionally produced incomplete JSON in earlier testing. The token limits were raised (1,800 output tokens for extraction, 16,000 for strategy reports) and the app now detects truncation explicitly via the API's stop_reason, flagging it rather than silently returning an incomplete result.
2. **No persistence of results.** Usage is logged (see above), but extraction results, personas and strategy reports themselves are not saved anywhere; closing the browser tab loses them unless downloaded first.
3. **No real data source connections.** This produces a validated query intent only, it does not call any actual CRM, data warehouse, or third-party data provider.
4. **Session-based cost cap, not account-based.** The cap resets if a visitor opens a new browser session, so it bounds cost per session, not per person.
5. **Plan gating is simulated, not enforced.** The Basic/Premium selector is a sidebar dropdown anyone can switch freely, it demonstrates the tiering UX, not real subscription access control. There's no user account system to tie a real plan to.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API: Claude Sonnet 5 (`MODEL` in `app.py`) for extraction, personas and strategy reports. Costs shown in the app are estimated from per-token prices set in `app.py`.
- Pandas (display formatting)
- pytest (tests for `strategy_report.py`)
- gspread + Google Sheets API (operator-side usage logging)

See HANDOFF.md for engineering handoff notes, open questions, and what this prototype deliberately doesn't solve. See PRICING.md for the pricing strategy and business model reasoning behind the Basic/Premium split. See GTM.md for the go-to-market channel reasoning.
