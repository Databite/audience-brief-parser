# Engineering Handoff: Ad Brief to Audience Schema Translator

## The problem this addresses

Marketing teams write audience targeting in loose, human language. Data and ML teams need structured field values that map to an actual data dictionary before they can query first-party CRM data or license third-party audience segments. Today that translation happens manually, or not at all, meaning briefs often stay too vague to action.

## What this prototype proves

An LLM can extract structured values from unstructured brief text and be constrained to only return values that exist in a real, predefined schema (in this case, grounded in the IAB Tech Lab Audience Taxonomy 1.1, not invented categories). A validation layer checks every returned value against the allowed list, so an invalid value never silently passes through to a downstream query.

## What I deliberately did not solve

- **No connection to real data sources.** This produces a validated query intent only. It does not call any actual CRM, data warehouse, or third-party data provider (LiveRamp, Experian, etc.). Wiring this to real systems is a separate integration project, and a meaningfully larger one, since it involves real contracts, data access agreements, and privacy review that this prototype has no visibility into.
- **Single brief at a time.** There's no batch mode. A real marketing team processes many briefs per campaign cycle, not one at a time through a web form.
- **No persistence or versioning.** Nothing is saved. If a brief is revised, there's no history of what changed or why the extracted schema changed with it.
- **First-party field values are illustrative, not real.** `purchase_history_segment`, `loyalty_tier`, and `email_engagement` are placeholders I constructed, since no public standard exists for internal CRM segmentation. A real implementation needs these mapped to whatever schema the actual CRM uses, which will differ by company.

## Open questions for engineering

1. **Omission versus invention.** Testing surfaced a real gap: when a brief mentions something outside the allowed schema (a social platform not in the data dictionary, for example), the model sometimes drops it silently rather than either forcing an invalid value in or flagging it as an assumption. The validation layer catches invalid values but doesn't catch omissions. Is a stricter prompt enough, or does this need a separate completeness check that diffs entities mentioned in the brief against what made it into the output?
2. **Confidence, not just presence.** Right now a field is either populated or "not specified." For a real system, is a binary enough, or does whoever queries the third-party data provider need a confidence signal, so a low-confidence inferred field is treated differently from a directly stated one?
3. **Cost at scale.** Based on actual per-brief costs observed during testing (roughly $0.007 per brief), here's what real volume looks like:

   | Monthly volume | Estimated monthly cost |
   |---|---|
   | 100 briefs | ~$0.70 |
   | 1,000 briefs | ~$7 |
   | 10,000 briefs | ~$70 |
   | 100,000 briefs | ~$700 |

   This scales differently than the consent form scorer, since campaign teams process briefs in bursts (a launch cycle), not a steady daily stream. At even 10,000 briefs a month, cost stays low, but that assumes brief length stays roughly constant. A brief with much longer copy or many more assumptions to reason through will cost more per call, so if this tool starts ingesting longer campaign documents rather than short briefs, cost per unit should be re-measured, not assumed to hold.
4. **Where does the data dictionary itself live?** It's hardcoded in the script right now. A real version likely needs this to be configurable, since the IAB taxonomy has ~1,500 possible segment values and different teams will want different subsets active.

## Architecture note

The LLM runs first here, since translating loose language into structure is the hard part a rule-based
