
## Live demo
 
https://audience-brief-parser-4dwtsrouwolbwzqdqsa6sb.streamlit.app/

# Ad Brief to Audience Schema Translator

A prototype tool that converts loosely written ad campaign briefs into a structured, validated target audience description, so it can be handed off to a data or ML team to query against real first-party and third-party data sources.

## The problem this solves

An ad brief typically describes a target audience in plain human language, for example "environmentally conscious millennials with disposable income." That description isn't queryable against a real data system. A data team needs actual field values that match a defined schema. This tool does that translation and, critically, validates the AI's output against a fixed set of allowed values, so it never silently hands downstream systems a value that doesn't exist in the real data dictionary.

## What it does

1. Takes a free-text ad brief as input.
2. **Extraction pass:** sends it to Claude with a strict instruction to extract only fields and values from a predefined data dictionary, never to invent new categories.
3. **Self-check pass:** a second Claude call reviews the extracted output against the original brief, specifically checking for anything mentioned in the brief that got dropped entirely, neither captured in a field value nor flagged as an assumption. Anything it catches gets added to the assumptions list, tagged `[caught by self-check]`.
4. Validates every returned value against the allowed list for that field, flagging anything that doesn't match.
5. Splits the results into two groups: first-party attributes (would be queried from the company's own CRM or customer data) and third-party attributes (would be queried from an external data provider).
6. Surfaces all assumptions, both the ones the model flagged during extraction and any additional ones the self-check pass caught.

This two-call pattern, one call does the work, a second call checks the first call's work against the source, is a small example of agentic-style verification: rather than trusting a single model call's output at face value, the system checks its own work before returning a result.

## Batch mode

Upload a CSV with a `brief_text` column to process multiple briefs at once. Results show a compact summary table plus an expandable detail view per row, with a downloadable CSV of the full output.

## Grounding in a real industry standard

The demographic and interest fields in this prototype are pulled directly from the [IAB Tech Lab Audience Taxonomy 1.1](https://github.com/InteractiveAdvertisingBureau/Taxonomies), the ad industry's actual public standard for describing audience segments. This was a deliberate choice: rather than inventing plausible-sounding categories, the schema reflects real, citable industry vocabulary.

First-party fields (purchase history segment, loyalty tier, email engagement) are illustrative placeholders, since no public standard exists for internal CRM segmentation, that data model is proprietary to each company.

## Known limitations

Testing surfaced two real gaps worth flagging for anyone extending this:

1. **Truncated responses at low token limits.** Longer briefs, or briefs generating longer self-check output, occasionally produced incomplete JSON that failed to parse. The app now detects this explicitly (checking the API's `stop_reason`) and flags truncated results rather than silently showing an incomplete answer, but the underlying risk, a response exceeding the token budget, isn't fully eliminated by raising the limit alone.

2. **Signals can still be missed, though less often now.** Earlier testing found the model sometimes dropped a mentioned signal (a platform not in the schema, for example) without flagging it. This is now addressed two ways: a stricter extraction prompt, and a second self-check call that reviews the extraction against the brief. In testing, the prompt fix alone resolved the known case; the self-check call exists as a safety net for cases the prompt fix doesn't catch on its own.

## What this is not

This prototype does not connect to any real data provider or CRM. It stops at producing a clean, validated, structured query intent. Connecting that output to actual data sources (a real customer database, a licensed third-party data provider) is a separate integration project.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the extraction and self-check layers
- Pandas (display formatting)

