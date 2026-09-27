# Ad Brief to Audience Schema Translator

**Live demo:** https://audience-brief-parser-4dwtsrouwolbwzqdqsa6sb.streamlit.app/

A tool that converts loosely written ad campaign briefs into a structured, validated target audience description, so it can be handed off to a data or ML team to query against real first-party and third-party data sources.

## The problem this solves

An ad brief typically describes a target audience in plain human language, for example "environmentally conscious millennials with disposable income." That description isn't queryable against a real data system. A data team needs actual field values that match a defined schema. This tool does that translation and, critically, validates the AI's output against a fixed set of allowed values, so it never silently hands downstream systems a value that doesn't exist in the real data dictionary.

## What it does

1. Takes a free-text ad brief as input.
2. Sends it to Claude with a strict instruction to extract only fields and values from a predefined data dictionary, never to invent new categories.
3. Validates every returned value against the allowed list for that field, flagging anything that doesn't match.
4. Splits the results into two groups: first-party attributes (would be queried from the company's own CRM or customer data) and third-party attributes (would be queried from an external data provider).
5. Surfaces any assumptions the model made when inferring a value from indirect language.

## Batch mode

Upload a CSV with a brief_text column (up to 50 rows) to process multiple briefs at once. Before running, the tool estimates the batch's likely cost against your remaining session budget and refuses to start if it would exceed it, rather than running out of budget partway through. Results show a compact summary table plus an expandable detail view per row, with a downloadable CSV of the full output.

## Audience persona generator (Premium feature)

After extracting a schema, an optional second step turns it into a short narrative persona, a name, a one-line tagline, a first-person quote, and a day-in-the-life paragraph, grounded strictly in the extracted schema values rather than inventing new detail. This maps to a deliverable boutique agencies already produce for their own clients, so it's built as the flagship Premium-tier feature rather than a generic add-on. See PRICING.md for the reasoning behind that choice.

A sidebar plan selector ("Basic" or "Premium") demonstrates this gating: Basic shows the persona section locked with an explanation, Premium unlocks the button. This selector is a UI simulation for demo purposes only, there's no real user account or billing system behind it, so it isn't real access control. See HANDOFF.md for what real entitlement enforcement would require.

## Built for real-world use, not just a demo

Beyond the core extraction logic, this includes several things a tool needs before a stranger can use it safely:

- **Input validation.** Empty, too-short, or excessively long briefs are rejected with a clear message before any API call is made, so no cost is wasted on invalid input.
- **Graceful failure handling.** If the AI service is down, rate-limited, or returns an error, the user sees a clear, readable message, never a raw Python traceback.
- **A session cost cap.** Usage is capped per session ($2.00 by default) to bound worst-case cost exposure from a single visitor, with the cap enforced before both single extractions and batch runs.
- **A first-time user explainer.** The page leads with a one-line plain-language description of what the tool does; a collapsed section covers the deeper mechanics (the industry-standard schema, the two data categories, what the tool doesn't do) for anyone who wants it.
- **Operator-side usage logging.** Every extraction attempt (single or batch, successful or failed) is logged to a Google Sheet outside the user's browser session, so usage can be reviewed later even after the visitor's session ends. Logging is best-effort: if it fails for any reason, it fails silently and never blocks or breaks the user's actual request.

## Grounding in a real industry standard

The demographic and interest fields in this prototype are pulled directly from the [IAB Tech Lab Audience Taxonomy 1.1](https://github.com/InteractiveAdvertisingBureau/Taxonomies), the ad industry's actual public standard for describing audience segments, rather than invented categories.

First-party fields (purchase history segment, loyalty tier, email engagement) are illustrative placeholders, since no public standard exists for internal CRM segmentation, that data model is proprietary to each company.

## A note on data

This is a public prototype with no privacy policy or data handling agreement, see HANDOFF.md's Stage 5 section for what's missing. The live app displays a warning asking visitors not to paste real client or campaign information, use a fictional or sample brief instead.

## Known limitations

1. **Truncated responses at low token limits.** Longer briefs occasionally produced incomplete JSON in earlier testing. The token limit was raised and the app now detects truncation explicitly via the API's stop_reason, flagging it rather than silently returning an incomplete result.
2. **No persistence of results.** Usage is logged (see above), but individual extraction results themselves are not saved anywhere; closing the browser tab loses them unless downloaded first.
3. **No real data source connections.** This produces a validated query intent only, it does not call any actual CRM, data warehouse, or third-party data provider.
4. **Session-based cost cap, not account-based.** The $2.00 cap resets if a visitor opens a new browser session, so it bounds cost per session, not per person.
5. **Plan gating is simulated, not enforced.** The Basic/Premium selector is a sidebar dropdown anyone can switch freely, it demonstrates the tiering UX, not real subscription access control. There's no user account system to tie a real plan to.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for extraction
- Pandas (display formatting)
- gspread + Google Sheets API (operator-side usage logging)

See HANDOFF.md for engineering handoff notes, open questions, and what this prototype deliberately doesn't solve. See PRICING.md for the pricing strategy and business model reasoning behind the Basic/Premium split. See GTM.md for the go-to-market channel reasoning.
