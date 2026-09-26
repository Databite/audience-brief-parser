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

## Tech stack

- Python
- Streamlit (interface)
- Anthropic API (Claude) for the extraction layer
- Pandas (display formatting)

## Running it locally


**Live demo:** https://audience-brief-parser-4dwtsrouwolbwzqdqsa6sb.streamlit.app/

