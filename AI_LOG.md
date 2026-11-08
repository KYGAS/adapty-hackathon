# AI log

## Tools and what we used them for

| Tool | Used for |
|---|---|
| Claude Code in VS Code (Claude Mythos 5.1, then Opus 5.5) | Nearly all code, tests and docs, the demo data generator, the pitch deck and the demo video, in one long agent session |
| Claude Code CLI (`claude -p`, our subscription) | Inside the product: it writes the executive memo, headless, with tools off and a JSON schema for the output |
| Adapty CLI 0.18 | We read its source to map the developer API, and made read-only calls to capture real answers from the Lumen app |
| Claude skills | dataviz for chart specs and palette checks, loop for ten timed data iterations, claude-api for the Anthropic provider, Slides for the pitch deck, ndemo for the demo video |
| Headless Chrome and Playwright | Screenshots and recordings, so the agent could check the UI it built instead of trusting a green build |

## Setup

- **Rules files:** a global `CLAUDE.md` with writing rules (plain ASCII punctuation, short factual sentences, no filler). The Adapty style kit's `STYLE_GUIDE.md` was the only allowed source for frontend design decisions.
- **Memory:** Claude Code keeps short note files between sessions: event rules, API routes, build state, and a lesson about ports. They carried the project state through a context compaction in the middle of the build.
- **Invariants as code:** the three rules from our build prompt became checks, not intentions. They are the number guard, a 100% coverage gate in the pytest config, and an approval-only write route.
- **MCP:** the Adapty MCP server was available but not connected. The developer API covered everything we needed.
- **Subagents:** none. One session did the work. Independent tool calls ran in parallel, and a 10-minute cron loop drove the data expansion.

## Prompts that worked well

1. The build prompt's invariants: *"Zero LLM Math ... Deterministic & Unit-Tested Statistics (100% coverage) ... No Autonomous Writes."* Stating them as non-negotiable turned each one into an architecture decision on day one.
2. *"/loop 10minutes ... analyze the data and create a larger seed sample ... execute 10 loop iterations, each with it's own data expansion target, finally collect the work done and give me a report."* One target per iteration kept every step small, tested and committed. The final report forced a reconciliation of all ten.
3. *"We now have a frontend guide collection: <style kit folder>. Please use it to guide all future frontend style decisions."* A concrete kit with tokens, components and 37 reference screenshots beats "make it look like Adapty".

## One thing AI got wrong

Claude's first trial-to-paid estimate for the weekly plan was 82%. Its own generator, using a stricter definition, gave 49.1%. That definition counts only finished trials, and only a payment for the same product after the trial started. We caught it because two independent computations of the same rate disagreed. The cause was renewal rows counted as new conversions. The same trap had inflated paid conversion on long tests, because purchases over viewers counts every renewal. The fix: conversion is now paying users over viewers, covered by unit tests, and each arm's trial rate is weighted by the plans that arm actually started.

## What we'd never delegate to AI

- **Stopping a live test or shipping a winner.** That is why the product turns every write into a dry run that needs a named human approval.
- **Choosing the risk thresholds:** alpha, power, the minimum effect and the 50-payer floor. AI can explain the trade-offs, but the team owns the cost of a wrong call.
- **Credentials and anything that leaves the machine.** Keys stay in `.env`, and pushing to the shared repository stays a human step.
