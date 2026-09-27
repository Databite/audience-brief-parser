# Engineering Handoff: Ad Brief to Audience Schema Translator

## The problem this addresses

Marketing teams write audience targeting in loose, human language. Data and ML teams need structured field values that map to an actual data dictionary before they can query first-party CRM data or license third-party audience segments. Today that translation happens manually, or not at all, meaning briefs often stay too vague to action.

## What this prototype proves

An LLM can extract structured values from unstructured brief text and be constrained to only return values that exist in a real, predefined schema (in this case, grounded in the IAB Tech Lab Audience Taxonomy 1.1, not invented categories). A validation layer checks every returned value against the allowed list, so an invalid value never silently passes through to a downstream query. A second, independent model call then reviews the first call's output against the original brief, catching signals the extraction pass may have missed, a lightweight example of self-verification rather than trusting a single pass at face value.

## What I deliberately did not solve

- **No connection to real data sources.** This produces a validated query intent only. It does not call any actual CRM, data warehouse, or third-party data provider (LiveRamp, Experian, etc.). Wiring this to real systems is a separate integration project, and a meaningfully larger one, since it involves real contracts, data access agreements, and privacy review that this prototype has no visibility into.
- **No persistence or versioning.** Nothing is saved. If a brief is revised, there's no history of what changed or why the extracted schema changed with it.
- **First-party field values are illustrative, not real.** `purchase_history_segment`, `loyalty_tier`, and `email_engagement` are placeholders I constructed, since no public standard exists for internal CRM segmentation. A real implementation needs these mapped to whatever schema the actual CRM uses, which will differ by company.

## Open questions for engineering

1. **Omission versus invention (partially resolved).** Testing surfaced a real gap: when a brief mentions something outside the allowed schema (a social platform not in the data dictionary, for example), the model sometimes dropped it silently rather than either forcing an invalid value in or flagging it as an assumption. This is now addressed two ways: a stricter extraction prompt that explicitly instructs the model to flag unmapped mentions, and a second self-check call that reviews the extraction against the original brief and catches anything still missed. In testing, the prompt fix alone caught the known case (a platform not in the schema); the self-check call exists as a safety net for cases the prompt fix doesn't catch. Open question for engineering: at what point does a second model call per brief stop being worth the added cost and latency, versus relying on the prompt fix alone? This likely depends on how costly a missed signal is in the actual business context, worth a conversation with whoever owns the downstream use of this data, not just an engineering call.
2. **Confidence, not just presence.** Right now a field is either populated or "not specified." For a real system, is a binary enough, or does whoever queries the third-party data provider need a confidence signal, so a low-confidence inferred field is treated differently from a directly stated one?
3. **Cost at scale.** Based on actual per-brief costs observed during testing (roughly $0.007 per brief for extraction alone, closer to $0.02 to $0.03 with the self-check pass included), here's what real volume looks like:

   | Monthly volume | Extraction only | With self-check |
   |---|---|---|
   | 100 briefs | ~$0.70 | ~$2.50 |
   | 1,000 briefs | ~$7 | ~$25 |
   | 10,000 briefs | ~$70 | ~$250 |
   | 100,000 briefs | ~$700 | ~$2,500 |

   The self-check call roughly triples the per-brief cost. At low volume this is trivial either way. At high volume, this is exactly the tradeoff named in question 1: is catching an occasional missed signal worth 2 to 3x the cost at scale? That's a product decision, not just an engineering one, and it may have a different answer depending on how the downstream data gets used (a missed signal in a small test campaign matters less than one in a major paid media buy).
4. **Where does the data dictionary itself live?** It's hardcoded in the script right now. A real version likely needs this to be configurable, since the IAB taxonomy has ~1,500 possible segment values and different teams will want different subsets active.

## Architecture note

Three layers run in sequence here. First, an LLM call extracts structure from unstructured text, since that's the hard part a rule-based system can't do. Second, a separate LLM call reviews that extraction against the original brief, checking specifically for dropped signals, this is a different kind of check than the first call, verification rather than extraction, which is why it's a separate call with its own narrow prompt rather than asking the first call to also grade itself. Third, a rule-based validation layer checks the final output against the fixed schema, catching any value that doesn't match, regardless of which of the first two calls produced it.

This is the inverse order from the compliance scorer, where rules ran first, because the two problems are shaped differently: there, rules catch known bad patterns before spending money on judgment; here, judgment produces the raw structure that rules then have to verify, and a second round of judgment double-checks the first round's completeness before the rules ever see it.

## Audience persona generator and the plan-gating bug

The persona generator is a fourth, optional LLM call: it takes the already-validated schema (not the raw brief) and turns it into a short narrative persona. It's kept as an explicit opt-in button rather than running automatically after every extraction, so cost isn't incurred on a call the user didn't ask for.

**A real bug worth documenting.** The first working version of this button had a genuine Streamlit gotcha: Streamlit reruns the entire script top to bottom on every widget interaction, and `st.button()` only returns `True` on the exact run it was clicked on. The extraction results and the persona button both lived inside `if st.button("Extract audience schema")`. Clicking "Generate persona" triggers a rerun, and on that rerun the extract button's condition is `False` again, which silently dropped the whole results block, schema tables, assumptions, and the persona button itself, out of the render. The fix: extraction results and the generated persona are now persisted in `st.session_state` and rendered from there, independent of which button was clicked on a given rerun, the same pattern Streamlit's own docs recommend for any UI where one button's result needs to survive a second button's click. Worth checking for this same pattern anywhere else multi-button interaction gets added later.

**Plan gating is a UI simulation, not access control.** The sidebar Basic/Premium selector is a `st.selectbox` with a `key`, which Streamlit persists in session state for the browser session. It has no connection to a real account, subscription, or payment system, so anyone can flip it freely. Real entitlement enforcement would need: user accounts (this prototype has none), a subscription/billing system (e.g. Stripe) that's the actual source of truth for a user's plan, and a server-side check on that plan before the persona endpoint runs, never a client-toggleable value. This is explicitly out of scope for this prototype and belongs in a later productization pass if this were built out for real, it's a meaningfully larger lift than anything else in this repo, involving auth, a real database, and a billing integration.

## Stage 5: legal and compliance groundwork (not addressed)

This is a known, named gap, not an unconsidered one. A real version of this tool, taking payment from real agencies, would need at minimum:

1. **Terms of Service.** What the buyer is paying for, liability limits, and who's responsible if the extraction is wrong and someone acts on it in a real targeting decision. This matters more than boilerplate ToS usually does, since the tool's output directly feeds real ad spend decisions.
2. **Privacy Policy.** What data is collected (ad brief text, which can contain a client's confidential campaign strategy), how long it's retained, and whether it's used for anything beyond the immediate request.
3. **Data handling commitments.** A real buyer would reasonably ask whether their brief text is visible to anyone else, or used to train anything. Right now briefs go to Anthropic's API under their standard terms and get logged to an operator Google Sheet, adequate for a prototype, not sufficient for a paying customer, who would need an actual data processing agreement.

None of this is built here. It's named explicitly so a reader of this repo sees a considered scope decision, not a gap nobody noticed.

**One real mitigation added, not a substitute for the above.** Since this app is deployed live and publicly reachable, the risk isn't only hypothetical, so a visible warning was added to the app itself (not just this doc) telling visitors not to paste real client or campaign information. This reduces the chance of real confidential data actually reaching the app, but it's a UI-level nudge someone can ignore, not a data processing agreement, a privacy policy, or a technical control. It does not close Stage 5.
