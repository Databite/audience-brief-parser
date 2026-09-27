import streamlit as st
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
import os
import json
import pandas as pd
import io
import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Ad Brief to Audience Schema Translator",
    page_icon="🎯",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

h1 {
    font-weight: 700;
    font-size: 2.1rem !important;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}

h2, h3 {
    font-weight: 600;
    letter-spacing: -0.01em;
}

.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 0.85rem !important;
    color: #6b7280 !important;
}

.stButton > button {
    font-weight: 600;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
}

[data-testid="stExpander"] {
    border-radius: 8px;
    border: 1px solid #e5e7eb;
}

.stTextArea textarea {
    border-radius: 8px;
    font-size: 0.95rem;
}

[data-testid="stMetricValue"] {
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key=api_key)
MODEL = "claude-sonnet-5"

INPUT_COST_PER_1K = 0.003
OUTPUT_COST_PER_1K = 0.015

# Bounds are business decisions, not derived from anything technical.
# Kept low because this app is reachable by anonymous visitors with no
# per-user auth, so a single session's worst-case API spend needs a ceiling.
MIN_BRIEF_LENGTH = 15
MAX_BRIEF_LENGTH = 3000
MAX_BATCH_ROWS = 50
SESSION_COST_CAP = 2.00
ESTIMATED_COST_PER_BRIEF = 0.015

SERVICE_ACCOUNT_FILE = "audience-parser-logging-eb22d4a5e70c.json"
SHEET_ID = "1QcuH2mH2HHtvC5PtCDRwqp7yK-u09WT6qZh91pKk4og"
SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet_client():
    """Authorize a Google Sheets client for operator-side usage logging.

    Tries Streamlit's secrets store first (how this runs when deployed on
    Streamlit Community Cloud), then falls back to a local service account
    JSON file (how this runs on a developer's machine, where st.secrets
    isn't configured).
    """
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SHEET_SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SHEET_SCOPES)
    return gspread.authorize(creds)

def log_event(event_type, cost, success):
    """Best-effort logging. Never let a logging failure break the user's actual request."""
    try:
        gc = get_sheet_client()
        sheet = gc.open_by_key(SHEET_ID).sheet1
        sheet.append_row([
            datetime.datetime.utcnow().isoformat(),
            event_type,
            round(cost, 5),
            success
        ])
    except Exception:
        pass

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

def validate_brief_input(text):
    stripped = text.strip()
    if len(stripped) == 0:
        return False, "Please paste an ad brief before submitting."
    if len(stripped) < MIN_BRIEF_LENGTH:
        return False, f"That looks too short to be a real ad brief (minimum {MIN_BRIEF_LENGTH} characters). Please add more detail."
    if len(stripped) > MAX_BRIEF_LENGTH:
        return False, f"That brief is too long ({len(stripped)} characters, maximum {MAX_BRIEF_LENGTH}). Please shorten it or split it into separate briefs."
    return True, None

def build_prompt(brief_text):
    field_list = "\n".join([f'- {name}: allowed values are {info["allowed"]}' for name, info in DATA_DICTIONARY.items()])
    prompt = f"""You are a marketing data analyst. Read the ad brief below and extract a structured target audience description.

Only use these fields, and only these allowed values for each field:
{field_list}

Rules:
1. If the brief does not give enough information to confidently pick a value for a field, use the exact string "not specified" for that field. Do not guess.
2. If you infer a value from indirect language, for example inferring household_income from a phrase like "disposable income", still provide the value, but also list that inference in the assumptions list below. Keep each assumption to one short sentence.
3. If the brief mentions something relevant that has no matching allowed value in the schema, note it explicitly in the assumptions list rather than dropping it silently.
4. Respond with ONLY valid JSON, no other text, no markdown code fences, in exactly this shape:
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
    """Strip a markdown code fence from Claude's response, if present.

    The prompt explicitly asks for raw JSON with no code fences, but models
    sometimes wrap output in ```json ... ``` anyway. This normalizes both
    cases so json.loads() doesn't fail on well-formed JSON that's just
    wrapped in markdown.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

def call_claude(prompt, max_tokens):
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
    except RateLimitError:
        return None, 0.0, False, "The AI service is temporarily rate limited. Please wait a moment and try again."
    except APIConnectionError:
        return None, 0.0, False, "Could not connect to the AI service. Please check your connection and try again."
    except APIError as e:
        return None, 0.0, False, f"The AI service returned an error and could not complete this request. ({e.__class__.__name__})"
    except Exception as e:
        return None, 0.0, False, f"An unexpected error occurred: {e.__class__.__name__}. Please try again."

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1000 * INPUT_COST_PER_1K) + (output_tokens / 1000 * OUTPUT_COST_PER_1K)
    text_blocks = [block.text for block in response.content if block.type == "text"]
    result_text = "\n".join(text_blocks)
    truncated = response.stop_reason == "max_tokens"
    return result_text, cost, truncated, None

def llm_extract(brief_text):
    prompt = build_prompt(brief_text)
    return call_claude(prompt, 1500)

def build_persona_prompt(parsed_schema):
    """Build a prompt that turns an already-extracted audience schema into a
    short narrative persona, the kind of one-pager a boutique agency would
    put in front of a client alongside a creative brief.

    Takes the structured schema rather than the original brief text, since
    the persona should reflect what the tool actually extracted and
    validated, not re-derive its own interpretation of the raw brief.
    """
    schema_lines = "\n".join([f"- {field}: {value}" for field, value in parsed_schema.items() if field != "assumptions"])
    return f"""You are a marketing strategist writing a short audience persona for an internal creative deck, based on a validated target audience schema.

Audience schema:
{schema_lines}

Write a persona with exactly this structure:
NAME: [a plausible first name and last initial for this persona]
TAGLINE: [one short sentence capturing who they are]
QUOTE: [one first-person sentence in this persona's voice, something they might plausibly say]
DAY_IN_THE_LIFE: [one short paragraph, 3-4 sentences, describing a typical day or moment relevant to this audience]

Ground every detail in the schema values above. Do not invent demographic or interest details that contradict or go beyond what's given. This is a fictional, illustrative persona for internal creative use, not a real individual or a claim about any real person.
"""

def parse_persona_result(text):
    """Parse the persona generator's structured text response into a dict.

    Same string-matching approach as the rest of this app's LLM output
    parsing: expects one field per line in the exact NAME/TAGLINE/QUOTE/
    DAY_IN_THE_LIFE format the prompt requests.
    """
    fields = {"NAME": "", "TAGLINE": "", "QUOTE": "", "DAY_IN_THE_LIFE": ""}
    current_field = None
    for line in text.splitlines():
        matched = False
        for field in fields:
            if line.startswith(field + ":"):
                fields[field] = line.split(":", 1)[1].strip()
                current_field = field
                matched = True
                break
        if not matched and current_field and line.strip():
            fields[current_field] += " " + line.strip()
    return fields

def generate_persona(parsed_schema):
    """Generate a narrative persona from an already-extracted schema.

    This is the Premium-tier feature: it's a second, separate API call on
    top of the base extraction, so it's kept as an explicit opt-in button
    rather than running automatically, so a Basic-equivalent user in this
    prototype isn't charged for a call they didn't ask for.
    """
    prompt = build_persona_prompt(parsed_schema)
    result_text, cost, truncated, api_error = call_claude(prompt, 400)
    if api_error:
        return None, cost, api_error
    return parse_persona_result(result_text), cost, None

def validate_against_dictionary(parsed_json):
    flags = []
    for field, info in DATA_DICTIONARY.items():
        value = parsed_json.get(field, "not specified")
        if value != "not specified" and value not in info["allowed"]:
            flags.append(f"'{field}' returned value '{value}', which is not in the allowed list {info['allowed']}")
    return flags

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
if "scan_count" not in st.session_state:
    st.session_state.scan_count = 0

def remaining_budget():
    return max(0.0, SESSION_COST_CAP - st.session_state.total_cost)

st.title("Ad Brief to Audience Schema Translator")
st.write("Turn a plain-language ad brief into a structured audience profile, ready to hand off to your data team.")

with st.expander("How does this actually work? (for the curious)"):
    st.markdown("""
**The problem this solves:** Marketers write audience descriptions in plain language, like "environmentally conscious millennials with disposable income." That's not something a data system can search for directly, it needs specific, predefined field values instead.

**What this tool does:** Paste in a plain-language ad brief, and it converts that description into a structured set of fields with real values, things like an age range, an income bracket, and a list of interests, all pulled from a real industry-standard vocabulary rather than made up on the spot.

**Why two categories, "1st-party" and "3rd-party":** Some information (like whether someone already bought from your company before) would come from your own customer records. Other information (like their age range or interests) would typically be purchased from an outside data provider. This tool sorts the results into those two groups, since in a real setting each group is looked up in a completely different place.

**What it doesn't do:** It doesn't actually connect to any real customer database or purchase real audience data, it only produces the structured request you'd hand off to whoever manages those systems.
""")

st.caption(f"Briefs must be between {MIN_BRIEF_LENGTH} and {MAX_BRIEF_LENGTH} characters. This is a prototype, not a validated production tool, always sanity-check the output before using it for real targeting decisions.")
st.caption(f"Session usage cap: \\${SESSION_COST_CAP:.2f}. Used so far: \\${st.session_state.total_cost:.5f}. Remaining: \\${remaining_budget():.5f}.")

# Simulates the pricing tier gate for demo purposes. There's no real user
# account or billing system here, so this isn't real access control, it's a
# stand-in that lets you toggle between what a Basic vs Premium visitor
# would see. The `key` argument makes Streamlit persist this choice in
# st.session_state automatically for the rest of the browser session, the
# same lifetime as the cost cap and scan count above.
st.sidebar.selectbox("Plan (simulated, for demo purposes)", ["Basic", "Premium"], key="user_plan")
st.sidebar.caption("This selector simulates what a Basic vs Premium subscriber would see. It is not connected to real billing or user accounts.")

tab1, tab2 = st.tabs(["Single brief", "Batch mode"])

with tab1:
    brief_input = st.text_area("Ad brief", height=150)

    if st.button("Extract audience schema"):
        if remaining_budget() <= 0:
            st.error(f"This session has reached its \\${SESSION_COST_CAP:.2f} usage cap. Please start a new session to continue.")
        else:
            is_valid, error_message = validate_brief_input(brief_input)
            if not is_valid:
                st.warning(error_message)
            else:
                with st.spinner("Extracting with Claude..."):
                    result_text, cost, truncated, api_error = llm_extract(brief_input)

                if api_error:
                    st.error(api_error)
                    log_event("single_extraction", 0.0, False)
                else:
                    st.session_state.total_cost += cost
                    st.session_state.scan_count += 1

                    if truncated:
                        st.warning("Response was cut off before completion. Results below may be incomplete.")

                    try:
                        parsed = json.loads(clean_json_text(result_text))
                        log_event("single_extraction", cost, True)
                        # Persist the parsed result and its cost in session_state rather
                        # than only a local variable. Streamlit reruns this entire script
                        # top to bottom on every widget interaction, and st.button() only
                        # returns True on the exact run where it was clicked. Without this,
                        # clicking "Generate persona" below triggers a rerun in which
                        # "Extract audience schema" is no longer True, so this whole block
                        # (and the schema results) would silently stop rendering, which is
                        # exactly the "clicked it, nothing happened" bug this fixes.
                        st.session_state.last_parsed = parsed
                        st.session_state.last_extraction_cost = cost
                        # Clear any persona generated for a previous brief, otherwise a
                        # new extraction would still show the old persona underneath it
                        # since that's also read from session_state now.
                        st.session_state.last_persona = None
                    except json.JSONDecodeError:
                        st.error("Claude did not return valid JSON. Raw response below.")
                        st.text(result_text)
                        st.session_state.last_parsed = None
                        log_event("single_extraction", cost, False)

    # Rendering reads from session_state, not a local variable, so results
    # (and the persona button below) survive the rerun triggered by any
    # other button on this page, including "Generate persona" itself.
    parsed = st.session_state.get("last_parsed")
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

        st.divider()
        st.subheader("Audience persona (Premium feature)")

        if st.session_state.user_plan != "Premium":
            # Locked state for Basic: show what the feature is and why it's
            # gated, rather than just hiding the section entirely. A visible
            # locked feature does more to sell an upgrade than a feature
            # that doesn't appear to exist at all.
            st.info("Persona generation is a Premium feature. Switch to Premium in the sidebar to try it. (This is a simulated plan selector for demo purposes, not real billing.)")
        else:
            st.caption("Turns this schema into a short narrative persona for internal creative decks. A separate API call, generated on demand.")
            if st.button("Generate persona"):
                if remaining_budget() <= 0:
                    st.error(f"This session has reached its \\${SESSION_COST_CAP:.2f} usage cap. Please start a new session to continue.")
                else:
                    with st.spinner("Generating persona..."):
                        persona, persona_cost, persona_error = generate_persona(parsed)
                    st.session_state.total_cost += persona_cost
                    if persona_error:
                        st.error(persona_error)
                        log_event("persona_generation", persona_cost, False)
                    else:
                        log_event("persona_generation", persona_cost, True)
                        # Also persisted, so the persona itself survives any later rerun
                        # (for example, if you click "Generate persona" again).
                        st.session_state.last_persona = persona
                        st.session_state.last_persona_cost = persona_cost

            if st.session_state.get("last_persona"):
                persona = st.session_state.last_persona
                st.markdown(f"**{persona['NAME']}**")
                st.write(persona['TAGLINE'])
                st.markdown(f"> {persona['QUOTE']}")
                st.write(persona['DAY_IN_THE_LIFE'])
                st.caption(f"Persona generation cost: \\${st.session_state.last_persona_cost:.5f}")

        st.subheader("Cost tracking")
        st.write(f"This extraction cost approximately \\${st.session_state.last_extraction_cost:.5f}")
        st.write(f"Total scans this session: {st.session_state.scan_count}")
        st.write(f"Total estimated cost this session: \\${st.session_state.total_cost:.5f}")

with tab2:
    st.write(f"Upload a CSV file with one column named `brief_text`, one ad brief per row. Maximum {MAX_BATCH_ROWS} rows per batch.")
    uploaded_file = st.file_uploader("Upload CSV", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if "brief_text" not in df.columns:
            st.error("Your CSV must have a column named 'brief_text'.")
        elif len(df) > MAX_BATCH_ROWS:
            st.error(f"This file has {len(df)} rows, which exceeds the {MAX_BATCH_ROWS} row limit for this prototype. Please split it into smaller batches.")
        else:
            estimated_batch_cost = len(df) * ESTIMATED_COST_PER_BRIEF
            st.write(f"Found {len(df)} briefs in this file. Estimated cost: \\${estimated_batch_cost:.4f}. Remaining session budget: \\${remaining_budget():.4f}.")

            if estimated_batch_cost > remaining_budget():
                st.error(f"This batch's estimated cost (\\${estimated_batch_cost:.4f}) exceeds your remaining session budget (\\${remaining_budget():.4f}). Reduce the number of rows or start a new session.")
            elif st.button("Run batch extraction"):
                results = []
                total_batch_cost = 0.0
                progress = st.progress(0)
                cap_hit_mid_batch = False

                for i, row in df.iterrows():
                    if remaining_budget() <= 0:
                        cap_hit_mid_batch = True
                        break

                    text = str(row["brief_text"])
                    is_valid, error_message = validate_brief_input(text)

                    if not is_valid:
                        row_result = {
                            "row": i + 1,
                            "parsed_ok": False,
                            "truncated": False,
                            "validation_flags": f"input rejected: {error_message}",
                            "assumptions": "",
                            "raw_response": "",
                            "cost": 0.0
                        }
                        for field in DATA_DICTIONARY.keys():
                            row_result[field] = "input_error"
                        results.append(row_result)
                        progress.progress((i + 1) / len(df))
                        continue

                    result_text, cost, truncated, api_error = llm_extract(text)

                    if api_error:
                        row_result = {
                            "row": i + 1,
                            "parsed_ok": False,
                            "truncated": False,
                            "validation_flags": f"API error: {api_error}",
                            "assumptions": "",
                            "raw_response": "",
                            "cost": 0.0
                        }
                        for field in DATA_DICTIONARY.keys():
                            row_result[field] = "api_error"
                        results.append(row_result)
                        log_event("batch_row", 0.0, False)
                        progress.progress((i + 1) / len(df))
                        continue

                    st.session_state.total_cost += cost
                    total_batch_cost += cost

                    try:
                        parsed = json.loads(clean_json_text(result_text))
                        flags = validate_against_dictionary(parsed)
                        row_result = {
                            "row": i + 1,
                            "parsed_ok": True,
                            "truncated": truncated,
                            "validation_flags": "; ".join(flags) if flags else "none",
                            "assumptions": "; ".join(parsed.get("assumptions", [])),
                            "raw_response": "",
                            "cost": round(cost, 5)
                        }
                        for field in DATA_DICTIONARY.keys():
                            row_result[field] = parsed.get(field, "not specified")
                        log_event("batch_row", cost, True)
                    except json.JSONDecodeError:
                        row_result = {
                            "row": i + 1,
                            "parsed_ok": False,
                            "truncated": truncated,
                            "validation_flags": "could not parse response" + (" (truncated)" if truncated else ""),
                            "assumptions": "",
                            "raw_response": result_text,
                            "cost": round(cost, 5)
                        }
                        for field in DATA_DICTIONARY.keys():
                            row_result[field] = "parse_error"
                        log_event("batch_row", cost, False)

                    results.append(row_result)
                    progress.progress((i + 1) / len(df))

                if cap_hit_mid_batch:
                    st.warning(f"Session usage cap reached partway through this batch. {len(results)} of {len(df)} rows were processed before stopping.")

                results_df = pd.DataFrame(results)
                st.subheader("Batch results")

                summary_df = results_df[["row", "parsed_ok", "truncated", "validation_flags", "cost"]]
                st.dataframe(summary_df, use_container_width=True)

                st.write(f"Total batch cost: \\${total_batch_cost:.5f}")

                st.subheader("Full details per row")
                for _, r in results_df.iterrows():
                    label = f"Row {r['row']} — {'OK' if r['parsed_ok'] else 'ERROR'}, \\${r['cost']}"
                    with st.expander(label):
                        st.markdown("**Extracted schema:**")
                        for field in DATA_DICTIONARY.keys():
                            st.write(f"- **{field}**: {r[field]}")
                        st.markdown("**Validation flags:**")
                        st.write(r["validation_flags"])
                        st.markdown("**Assumptions:**")
                        st.write(r["assumptions"] if r["assumptions"] else "None")
                        if not r["parsed_ok"] and r["raw_response"]:
                            st.markdown("**Raw response (for debugging):**")
                            st.text(r["raw_response"])

                csv_buffer = io.StringIO()
                results_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    "Download results as CSV",
                    csv_buffer.getvalue(),
                    "batch_results.csv",
                    "text/csv"
                )
