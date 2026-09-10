# SureForge

An instruction-only Agent Skill for complex work. It tells an AI agent to research before it asks, ask before it plans, plan before it builds, verify before it delivers, and to get an independent review before it calls anything done.

Version 1.0.0. MIT license. Maintained by Da7-Tech.

## Why this exists

Agents fail in predictable ways on big tasks. They start building before the request is understood. They treat a skipped question as a yes. They check a sample and call it complete. They re-read their own work and call it a review. They run out of review rounds and ship anyway.

SureForge is the working procedure that grew out of dealing with exactly those failures, written down so an agent can follow it. The pattern behind it is simple: the time spent understanding, planning, and checking up front is far less than the time spent redoing work, patching it, and re-checking it by hand afterwards. Fewer do-overs means fewer tokens over the life of a task, less of your attention spent on review, and work that is right the first time far more often.

It is plain text: a short entry point plus reference files the agent loads when it needs them. There is no runtime, no hook, and no dependency. The agent follows it the way it follows any other skill.

## Install

The skill is the `skills/sureforge/` folder: one `SKILL.md` plus the reference files and templates it links to. Installing means putting a copy of that folder where your agent looks for skills. Nothing runs at install time and nothing runs afterwards; the agent reads the text when the skill is selected.

With the Skills CLI (Node.js 22.20 or newer), from your project:

```bash
npx skills add Da7-Tech/SureForge
```

The CLI asks which agents to install for and copies the folder into each one's skill directory. To skip the prompt, name the agents with the CLI's identifiers, for example:

```bash
npx skills add Da7-Tech/SureForge --agent claude-code --agent codex --agent cursor --agent devin --agent hermes-agent -y
```

Add `-g` to install at user level instead of in the current project. The CLI may write a `skills-lock.json` in your project; that file can contain local paths, so look at it before committing it. `npx skills update` refreshes installed skills and `npx skills remove` uninstalls them.

Manual install: copy the whole `skills/sureforge/` folder, including `LICENSE`, `references/`, and `assets/`, into the directory your host reads. Copying only `SKILL.md` is not enough, because it links to the other files.

| Host | Project directory | User directory |
| --- | --- | --- |
| Claude Code | `.claude/skills/sureforge/` | `~/.claude/skills/sureforge/` |
| Codex | `.agents/skills/sureforge/` | `~/.agents/skills/sureforge/` |
| Cursor | `.agents/skills/sureforge/` or `.cursor/skills/sureforge/` | `~/.cursor/skills/sureforge/` or `~/.agents/skills/sureforge/` |
| Devin CLI | `.devin/skills/sureforge/` | `~/.config/devin/skills/sureforge/` |
| Hermes Agent | `.hermes/skills/sureforge/` | `~/.hermes/skills/sureforge/` |

These are the directories the pinned Skills CLI and the hosts' own documentation used when this was checked (dates and details in [platforms.md](skills/sureforge/references/platforms.md)). Hosts change their paths; if a skill is not discovered, check the host's current documentation first.

To read the skill without installing anything, open [SKILL.md](skills/sureforge/SKILL.md). It is the same text the agent gets.

## Use

Ask for it by name:

> Use SureForge for this task. Research the important unknowns before you ask me anything, then give me a plan I can check before you build.

For high-stakes work, ask for full mode:

> Use SureForge in full mode. Do not pass a gate without three verification methods of your own and three from an independent reviewer. If a reviewer or tool is missing, tell me instead of pretending.

Small tasks are meant to stay small. If you ask SureForge to fix a typo, the instructions call for fixing the typo and checking the diff, not for starting a research project.

## How it works

Four phases, each ending in a gate that is READY, REPAIR, or BLOCKED:

1. Research and clarify. Read what is already there, research the unknowns that change the decision, look at the problem from three angles, then ask the questions that matter and offer alternatives. A skipped question is not an answer.
2. Plan. Map every acceptance criterion to a step, an inspection unit, and a way to verify it. Write down permissions, budgets, and stop conditions before touching anything.
3. Execute. One owner, dependency order, failing test before the fix where tests exist. If execution shows the plan was wrong, go back to the plan gate instead of patching.
4. Deliver. Freeze the candidate, inspect every agreed unit on that exact version, try the recipient's path (open it, install it, run it), and report what was verified, what was reused, and what was not checked.

Three tiers set how much of this runs:

| Tier | When | What the agent owes |
| --- | --- | --- |
| Light | Small, reversible, clearly specified | Understand, do the minimal change, check it. |
| Standard | Substantial multi-step work with bounded consequences | Four gates, two complementary checks per gate, independent review at plan and delivery when one is available. |
| Full | You asked for it, or the consequences are high-risk or hard to reverse | Three verification methods from the agent and three chosen freely by a fresh-context reviewer at every gate; a critic for material disputes. |

Independent review means a reviewer that has not seen the author's reasoning, self-rating, or preferred verdict. It gets the artifact, the request, the contract, and the material it needs, and it picks its own methods. Every finding is investigated before anything is changed: confirmed, refuted with evidence, unresolved, duplicate, or out of scope. There are at most three review rounds per gate, and running out of rounds is a BLOCKED result, not a delivery.

When something is missing (no internet, no question tool, no reviewer, no renderer), the skill says so and uses a named fallback rather than pretending the check happened.

## What is in this repository

- `skills/sureforge/` is the skill: `SKILL.md`, seven reference files (the four phases, the review protocol, a verification catalog, dated platform notes), and templates for the reviewer brief, critic brief, task ledger, and coverage ledger. This folder is all a user needs.
- `evals/` is the evaluation kit: thirteen failure scenarios with pass/fail oracles, twenty activation prompts with expected tiers, five synthetic benchmark tasks with hidden grading criteria, a three-arm study protocol, an abstract gate model, and a strict aggregator for run records.
- `review/` holds the review contract the skill was built against and a neutral intake for fresh-context reviewers.
- `scripts/` and `tests/` check the package itself: inventory, metadata, links, licenses, privacy patterns, archive integrity, and installation. See [Verification](#verification) for the commands.
- [CONTRIBUTING](CONTRIBUTING.md), [SECURITY](SECURITY.md), and the [code of conduct](CODE_OF_CONDUCT.md) cover how to propose changes, how to report text that could steer an agent badly, and how people are expected to treat each other here.

## How it has been tested

Three kinds of evidence, kept apart because they prove different things.

Mechanical checks you can rerun from this repository: the unit tests (see [Verification](#verification)) pass on Python 3.11 and 3.14, and every fault listed in `scripts/mutation_audit.py` is caught by them when seeded into a temporary copy. The skill passes the reference `skills-ref` validator at the commit pinned in `review/toolchain.json`.

Installation checks, run locally with Skills CLI 1.5.23 in an isolated project: copies installed for the five CLI targets Claude Code, Cursor, Codex, Devin, and Hermes (four directories, since Cursor and Codex share one) were byte-identical to `skills/sureforge/`, and Devin CLI 3000.6.14 listed the installed skill. Installation from the public repository is checked when a release is tagged and recorded in that release's notes, not here.

Behavior, from two pilots that checked whether models actually follow the text and stay inside its limits. The run logs are kept by the maintainer, outside this repository.

- GLM-5.2 through Devin, skill installed, 38 sessions (13 scenarios, 20 activation prompts, 5 tasks). The model followed the workflow in 12 of 13 scenarios and partially in one. It stayed quiet on all 10 prompts labeled as not needing the skill and picked the skill up on 5 of the 10 labeled for it (that set includes two explicit invocations and one light-tier typo fix). All five tasks came out correct, and the one check the model could not perform, a visual render, it reported as blocked instead of claiming it had done it.
- Grok 4.6 at maximum effort, with and without the skill, 24 runs: 4 tasks at two repetitions per arm (16) and 4 scenarios at one repetition per arm (8). Both arms met every frozen criterion. With the skill, every run declared its tier, said plainly when no independent reviewer was available instead of pretending one was, and left a coverage ledger and evidence record behind, so the person receiving the work could see what had been checked and what had not.

The pilots used small synthetic tasks that a strong model gets right with or without help; they were built to test adherence and safety, not to show the gains that come on real, underspecified work where the failures listed above actually happen. A three-arm comparison on the maintainer's own task set and on visual-document work is the next step.

Four rounds of independent review preceded this release; the findings and what changed are in the [changelog](CHANGELOG.md).

## Verification

From the repository root, with Python 3.11 or newer:

```bash
python3 -B -m scripts.check_package
python3 -B -m unittest discover -s tests -v
```

The first command checks the file inventory, skill metadata, links, licenses, requirement references, evaluation data, syntax, version consistency across the public documents, and privacy patterns. The second runs the package, gate-model, and metrics tests. To seed each listed implementation fault into a temporary copy and confirm the tests catch it (a few minutes):

```bash
python3 -B -m scripts.mutation_audit
```

To compare an installed copy with the source:

```bash
python3 -B -m scripts.verify_install --installed path/to/installed/sureforge
```

To build or verify a review archive (a normalized ZIP with a manifest of file hashes):

```bash
python3 -B -m scripts.package_review --output path/outside/the/repo/SureForge-review.zip
python3 -B -m scripts.package_review --verify path/to/SureForge-review.zip --archive-only
```

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md). In short: keep the skill text short and portable, add a test with every behavior change, keep personal data out of the repository, and do not claim measured benefits that were not measured.

## Design notes

The packaging follows the [Agent Skills specification](https://agentskills.io/specification) and its guidance on [authoring](https://agentskills.io/skill-creation/best-practices.md) and [evaluation](https://agentskills.io/skill-creation/evaluating-skills.md). Workflow references considered during design include [Superpowers](https://github.com/obra/superpowers), [Spec Kit](https://github.com/github/spec-kit), and [BMAD](https://github.com/bmad-code-org/BMAD-METHOD). The text here is original.

## License

MIT. See [LICENSE](LICENSE).

This skill is available on AutoClaw. [Claim 50 million free tokens](https://autoclaw.z.ai/redeem/?repo=SureForge&code=7BSH6UU9LW4T).
