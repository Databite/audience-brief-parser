# Ad Brief to Audience Schema Translator

A prototype tool that converts loosely written ad campaign briefs into a structured, validated target audience description, so it can be handed off to a data or ML team to query against real first-party and third-party data sources

## The problem this solves

An ad brief typically describes a target audience in plain human language, for example "environmentally conscious millennials with disposable income." That description isn't queryable against a real data system. A data team needs actual field values that match a defined schema. This tool does that translation and, critically, validates the AI's output against a fixed set of allowed values, so it never silently hands downstream systems a value that doesn't exist in the real data dictionary.

## What it does

1. Takes a free-text ad brief as input.
2. Sends it to Claude with a strict instruction to extract only fields and values from a predefined data dictionary, never to invent new categories.
3. Validates every returned value against the allowed list for that field, flagging anything the model returned that doesn't match.
4. Splits the results into two groups: first-party attributes (would be queried from the company's own CRM or customer data) and third-party attributes (would be queried from an external data provider).
5. Surfaces any assumptions the model made when inferring a value from indirect language (for example, inferring an income bracket from the phrase "disposable income").

## Grounding in a real industry standard

The demographic and interest fields in this prototype are pulled directly from the [IAB Tech Lab Audience Taxonomy 1.1](https://github.com/InteractiveAdvertisingBureau/Taxonomies), the ad industry's actual public standard for describing audience segments. This was a deliberate choice: rather than inventing plausible-sounding categories, the schema reflects real, citable industry vocabulary.

First-party fields (purchase history segment, loyalty tier, email engagement) are illustrative placeholders, since no public standard exists for internal CRM segmentation, that data model is proprietary to each company.

## What this is not

This prototype does not connect to any real data provider or CRM. It stops at producing a clean, validated, structured query intent. Connecting that output to actual data sources (a real customer database, a licensed third-party data provider) is a separate integration project.

## Known limitations

Testing surfaced two real gaps worth flagging for anyone extending this:

1. **Truncated responses at low token limits.** With the original `max_tokens` setting, longer briefs occasionally produced incomplete JSON that failed to parse. Raising the limit resolved it for the briefs tested here, but a production version should handle a truncated or malformed response gracefully (retry, or surface a partial result) rather than just failing.

2. **Signals can be silently dropped instead of flagged.** When a brief mentions something outside the allowed schema (for example, a social platform not in the data dictionary), the model sometimes omits it entirely rather than either forcing an invalid value or listing it in the assumptions section. The validation layer catches invalid values, but it does not currently catch omissions. A stricter prompt instruction, or a completeness check that compares mentioned entities in the brief against what made it into the output, would close this gap.

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the extraction layer
- Pandas (display formatting)

## Running it locally


**Live demo:** https://audience-brief-parser-4dwtsrouwolbwzqdqsa6sb.streamlit.app/

