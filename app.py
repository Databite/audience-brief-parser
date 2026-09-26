import streamlit as st
from anthropic import Anthropic
import os
import json
import pandas as pd

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-5"

INPUT_COST_PER_1K = 0.003
OUTPUT_COST_PER_1K = 0.015

# Demographic and interest values below are pulled directly from the
# IAB Tech Lab Audience Taxonomy 1.1, the ad industry's actual public
# standard for describing audience segments. Source:
# https://github.com/InteractiveAdvertisingBureau/Taxonomies
# Purchase history, loyalty tier, and email engagement have no public
# standard, since that's internal CRM data unique to each company, so
# those are illustrative placeholders, not taxonomy-grounded values.

DATA_DICTIONARY = {
    "age_range": {
        "allowed": ["18-20", "21-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75+"],
        "source": "3rd_party"
    },
    "gender": {
        "allowed": ["Female", "Male", "Other Gender", "Unknown Gender"],
        "source": "3rd_party"
    },
    "household_income": {
        "allowed": ["Less than $10,000", "$10,000-$14,999", "$15,000-$19,999", "$20000 - $39999", "$40000 - $49999", "$50000 - $74999", "$75000 - $99999", "$100000 - $149999", "$150,000-$174,999", "$175,000-$199,999", "$200,000-$249,999", "$250,000+"],
        "source": "3rd_party"
    },
    "urbanization": {
        "allowed": ["Rural", "2K-4.9K People", "5K-9.9K People", "10K-19.9K People", "20K-49.9K People", "50K-99.9K People", "100K-199.9K People", "200K-2M People", "Over 2M+ People"],
        "source": "3rd_party"
    },
    "interests": {
        "allowed": ["Automotive", "Books and Literature", "Business and Finance", "Careers", "Education", "Family and Relationships", "Fine Art", "Food & Drink", "Health and Medical Services", "Healthy Living", "Hobbies & Interests", "Home & Garden", "Movies", "Music and Audio", "News and Politics", "Personal Finance", "Pets", "Real Estate", "Shopping", "Sports", "Style & Fashion", "Technology & Computing", "Television", "Travel", "Video Gaming"],
        "source": "3rd_party"
    },
    "social_platforms": {
        "allowed": ["Instagram", "TikTok", "Facebook", "LinkedIn", "YouTube", "Twitter/X"],
        "source": "3rd_party"
    },
    "purchase_history_segment": {
        "allowed": ["first_time_buyer", "repeat_customer", "high_value", "lapsed"],
        "source": "1st_party"
    },
    "loyalty_tier": {
        "allowed": ["none", "bronze", "silver", "gold", "platinum"],
        "source": "1st_party"
    },
    "email_engagement": {
        "allowed": ["high", "medium", "low", "unengaged"],
        "source": "1st_party"
    },
}

def build_prompt(brief_text):
    field_list = "\n".join([f'- {name}: allowed values are {info["allowed"]}' for name, info in DATA_DICTIONARY.items()])
    prompt = f"""You are a marketing data analyst. Read the ad brief below and extract a structured target audience description.

Only use these fields, and only these allowed values for each field:
{field_list}

Rules:
1. If the brief does not give enough information to confidently pick a value for a field, use the exact string "not specified" for that field. Do not guess.
2. If you infer a value from indirect language, for example inferring household_income from a phrase like "disposable income", still provide the value, but also list that inference in the assumptions list below.
3. Respond with ONLY valid JSON, no other text, no markdown code fences, in exactly this shape:
{{
  "age_range": "...",
  "gender": "...",
  "household_income": "...",
  "urbanization": "...",
  "interests": "...",
  "social_platforms": "...",
  "purchase_history_segment": "...",
  "loyalty_tier": "...",
  "email_engagement": "...",
  "assumptions": ["...", "..."]
}}

Ad brief:
\"\"\"
{brief_text}
\"\"\"
"""
    return prompt

def clean_json_text(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

def llm_extract(brief_text):
    prompt = build_prompt(brief_text)
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1000 * INPUT_COST_PER_1K) + (output_tokens / 1000 * OUTPUT_COST_PER_1K)

    text_blocks = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_blocks)
    return result_text, cost

def validate_against_dictionary(parsed_json):
    flags = []
    for field, info in DATA_DICTIONARY.items():
        value = parsed_json.get(field, "not specified")
        if value != "not specified" and value not in info["allowed"]:
            flags.append(f"'{field}' returned value '{value}', which is not in the allowed list {info['allowed']}")
    return flags

st.title("Ad Brief to Audience Schema Translator")
st.write("Paste an ad brief below. This extracts a structured target audience description mapped to the IAB Tech Lab Audience Taxonomy 1.1, and shows which attributes come from 1st-party data versus 3rd-party data.")

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0

brief_input = st.text_area("Ad brief", height=150)

if st.button("Extract audience schema"):
    if brief_input.strip() == "":
        st.warning("Paste an ad brief first.")
    else:
        with st.spinner("Extracting with Claude..."):
            result_text, cost = llm_extract(brief_input)

        st.session_state.total_cost += cost
        st.session_state.scan_count += 1

        try:
            parsed = json.loads(clean_json_text(result_text))
        except json.JSONDecodeError:
            st.error("Claude did not return valid JSON. Raw response below.")
            st.text(result_text)
            parsed = None

        if parsed:
            st.subheader("Validation against data dictionary")
            flags = validate_against_dictionary(parsed)
            if flags:
                for flag in flags:
                    st.error(flag)
            else:
                st.success("All returned values match the allowed data dictionary values.")

            st.subheader("1st-party attributes (query your own CRM or customer data)")
            first_party_rows = [(field, parsed.get(field, "not specified")) for field, info in DATA_DICTIONARY.items() if info["source"] == "1st_party"]
            st.table(pd.DataFrame(first_party_rows, columns=["Attribute", "Value"]))

            st.subheader("3rd-party attributes (query external data providers)")
            third_party_rows = [(field, parsed.get(field, "not specified")) for field, info in DATA_DICTIONARY.items() if info["source"] == "3rd_party"]
            st.table(pd.DataFrame(third_party_rows, columns=["Attribute", "Value"]))

            assumptions = parsed.get("assumptions", [])
            st.subheader("Assumptions made by the model")
            if assumptions:
                for a in assumptions:
                    st.warning(a)
            else:
                st.write("No assumptions flagged.")

        st.subheader("Cost tracking")
        st.write(f"This extraction cost approximately ${cost:.5f}")
        st.write(f"Total scans this session: {st.session_state.scan_count}")
        st.write(f"Total estimated cost this session: ${st.session_state.total_cost:.5f}")
