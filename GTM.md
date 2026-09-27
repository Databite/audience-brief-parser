# Go-to-Market Strategy: Ad Brief to Audience Schema Translator

Like PRICING.md, this is a reasoning exercise, not an executed plan. No outreach has actually happened, no community post has gone out. This documents the thinking, including a course correction partway through, rather than a clean final answer.

## The buyer, restated

An account lead at a boutique advertising agency, the same persona defined in PRICING.md. The channel choices below all have to reach that specific person, not a generic marketing audience.

## Channels considered

Three were evaluated: content/SEO, a free trial, and outreach through an existing network.

**Content/SEO.** The real search intent isn't "AI audience segmentation tool," it's language closer to the actual pain: "how to write a brief that doesn't get bounced back," "IAB taxonomy explained," or platform-specific targeting field questions. Content built around the real search terms, with the tool as the natural next step rather than the headline, would work, but SEO takes months to rank. It's a durable long-term channel, not a way to get first users this quarter.

**Free trial.** Given the unit economics (roughly $0.015-$0.03 per brief), a generous free trial, 20 or so extractions, costs well under a dollar to give away. The real barrier to conversion isn't price (Basic is already priced to be expensable without procurement), it's trust in an unproven tool from an unknown vendor. A free trial addresses that directly by letting someone test it against a real brief before committing to pay.

**Existing network.** This was the strongest channel in theory, a warm intro beats any cold channel. In practice, there is no existing network of boutique agency contacts to draw on, this is honestly cold outreach, not a warm channel, and that changes the plan.

## Correction: cold DMs versus community-first

The first version of this plan defaulted to cold LinkedIn outreach, direct messages to 15-25 people with titles like Account Director or Media Director at small agencies. On reflection, that's likely not the best first move for this specific product. A single-feature tool from an unknown solo builder is a hard cold sell, it asks a stranger to trust an unproven vendor with something that touches their own client relationships, and cold outreach at this scale typically nets a single-digit-percent reply rate.

A better first channel for this situation: communities where the buyer persona already self-selects, agency-focused subreddits (r/advertising, r/agency), agency owner Slack or Discord groups, or marketing-ops corners of X/LinkedIn where "here's a tool I built, tell me if it's useful" posts are normal. This flips the dynamic from interrupting a stranger to reaching people who already have the pain and choose to engage, and it's lower effort per potential lead than one-to-one cold messages.

**Revised plan, in priority order:**
1. Community posts (agency-focused subreddits, relevant Slack/Discord groups) as the primary first-touch channel
2. A free trial as the low-commitment conversion mechanism from that traffic
3. Content/SEO as a long-term supporting channel, not a near-term acquisition lever
4. Cold outreach deprioritized below the above, since it's the highest-effort, lowest-response channel of the options considered, worth revisiting only if the community channel produces no signal at all

## The compliance tension this surfaced

Building out this plan surfaced a real tension with Stage 5 (legal and compliance groundwork, deliberately left unaddressed for this exercise): any version of this plan that gets someone to actually trial the tool risks them pasting real client or campaign information into a live app with no privacy policy or data processing agreement.

**Resolution for this exercise:** rather than build out real legal groundwork (out of scope, named explicitly in HANDOFF.md), a visible warning was added directly to the live app asking visitors not to paste real client or confidential information, and to use a fictional or sample brief instead. This is a UI-level mitigation, not a real safeguard, it reduces risk but doesn't close the gap. If this were pursued for real, closing Stage 5 first would be a precondition for actually executing any of the channels above, not an afterthought to handle once users show up.

## What's still unvalidated

Everything above is reasoning, not evidence. No one outside this exercise has confirmed the pain is real for a specific boutique agency, that the pricing lands, or that any of these channels actually converts. That's Stage 1 (idea and problem validation) work, explicitly skipped at the start of this exercise, and it remains the biggest open gap in the whole plan, this document describes a hypothesis about go-to-market, not a tested one.
