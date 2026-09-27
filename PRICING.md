# Pricing Strategy: Ad Brief to Audience Schema Translator

This document is part of a deliberate learning exercise: walking one prototype through the stages of an idea-to-product lifecycle a real company would go through, including business model thinking, independent of actual market validation. The reasoning below is informed guessing calibrated against unit economics and comparable products, not research from real prospects. That distinction matters and is called out explicitly rather than presented as validated pricing.

## Buyer persona

**Who pays**: not the individual marketer writing the brief, but an account lead at a small boutique advertising agency, the person who owns the handoff between a client's brief and the team that executes targeting.

**The pain this solves**: rework. Briefs get bounced back and forth because the targeting section is vague, incomplete, or uses language a data team can't act on directly. Boutique agencies are the right size for this problem: big enough to have real brief-handoff friction, too small to have built internal tooling for it themselves.

## Value metric

Flat monthly tier per team, not per-brief usage. The actual marginal API cost per brief is roughly $0.015, small enough that metering by usage would make the tool look strangely cheap for the actual value delivered (fewer round trips, less rework, faster handoff). A flat tier better matches how a workflow tool's value is actually perceived, and how boutique agencies budget for software (an expensable monthly line item, not a variable cost tied to volume).

## Tier structure

| Tier | Seats | Price | What's included |
|---|---|---|---|
| Basic | Up to 5 | $79/month | Core extraction, validation against the data dictionary, batch mode |
| Premium | Up to 10 | $229/month | Everything in Basic, plus the audience persona generator and a stronger extraction model |
| Custom | 10+ | Contact for pricing | Sales-assisted, for agencies beyond the self-serve range |

**Why $79, not lower.** An early draft considered a $49 entry price. Competitive research (below) suggests boutique agencies are used to paying more for comparable AI marketing tools, and a price that's too low can read as "not serious" to a buyer evaluating a new vendor. $79 keeps the tool self-serve and expensable without a procurement process, while signaling more credibility than a bargain-bin price would.

**Why $229 for Premium, not just "more seats."** Premium isn't priced as a seat-count multiplier alone, since that would just be per-seat pricing wearing a tier costume. It's priced as a meaningful step up (2.9x Basic) tied to two real feature differences: the persona generator and a stronger model on extraction. $229 for 10 seats also lands well under what a per-seat competitor like Jasper would charge for the same team size (10 x $69/seat = $690/month at their list price), positioning this as a smart alternative to buying enterprise seats rather than a stripped-down cheap tool.

## Competitive pricing research

Two comparable AI marketing tools were checked for real pricing anchors, since cost-plus pricing tells you almost nothing here (API cost per brief is negligible) and no real prospect price-sensitivity research (e.g. a Van Westendorp study) has been done for this tool:

- **AdCreative.ai**: Starter $20-39/month (1 user), Professional $125-249/month (10 users), Ultimate $500-999/month (20 users), custom Enterprise beyond that. ([Atria: AdCreative.ai Pricing 2026](https://www.tryatria.com/blog/adcreative-ai-pricing))
- **Jasper**: Pro tier at $69/seat/month (so a 5-seat team runs $345/month, a 10-seat team $690/month at list price), custom Business tier for larger teams with priority support and API access. ([eesel AI: A Comprehensive Guide to Jasper AI Pricing in 2026](https://www.eesel.ai/blog/jasper-ai-pricing))

Both comps suggest room to price at or above the current $79/$229 structure, not below it, per-seat models in this space run meaningfully higher than what's being proposed here for a comparable team size.

## Premium feature: why the persona generator, not other options considered

Three feature ideas for differentiating Premium were considered:

1. **Persona generator (built).** Turns the extracted schema into a narrative persona (name, tagline, quote, day-in-the-life). Chosen first because it maps directly to a deliverable boutique agencies already produce and bill for as part of client work, this isn't introducing a new concept to the buyer, it's automating something they already understand the value of.
2. **Model tiering (not yet built, planned).** Running Premium extractions on a stronger model than Basic. Chosen second because it ties the price difference to a real, defensible cost and quality difference, rather than an arbitrary feature gate.
3. **AI-generated image from the insights (considered and dropped).** Rejected for v1: image generation costs meaningfully more per call than text, and it pulls the tool's scope away from its actual job (producing a queryable schema for a data team) toward visual creative, which risks diluting the core value proposition rather than strengthening it. Kept as a documented "considered and scoped out" idea rather than built, a deliberate prioritization decision worth being able to explain, not an oversight.

## Honest limitations of this pricing exercise

- No real customer or prospect has seen these numbers. There is no price-sensitivity data (Van Westendorp or otherwise) behind the $79/$229 figures, they're anchored to competitor pricing and unit economics, not demand research.
- The plan gating in the live app is a UI simulation (see HANDOFF.md), not connected to real billing, so this pricing has not been tested against real payment behavior.
- Tier feature differentiation currently rests on one built feature (persona generator) and one planned-but-unbuilt one (model tiering). A real launch would need the second one built before Premium's price is fully justified by its feature set.
