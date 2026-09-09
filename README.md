# SureForge

An instruction-only Agent Skill for complex work. It tells an AI agent to research before it asks, ask before it plans, plan before it builds, verify before it delivers, and to get an independent review before it calls anything done.

Version 1.0.0. MIT license. Maintained by Da7-Tech.

## Why this exists

Agents fail in predictable ways on big tasks. They start building before the request is understood. They treat a skipped question as a yes. They check a sample and call it complete. They re-read their own work and call it a review. They run out of review rounds and ship anyway.

SureForge is a written procedure aimed at those gaps. It is plain text: a short entry point plus reference files the agent loads when it needs them. There is no runtime, no hook, and no dependency. The agent follows it the way it follows any other skill, which also means the skill cannot force anything; it can only make the right behavior explicit and the shortcuts visible.

## Install

With the Skills CLI (Node.js 22.20 or newer), from your project:

```bash
npx skills add Da7-Tech/SureForge
```

The CLI copies `skills/sureforge/` into the skill directory of the agents you select (Claude Code, Cursor, Codex, Devin, Hermes, and others that follow the Agent Skills standard). When you pass targets on the command line, use the CLI's own identifiers, for example `--agent claude-code --agent cursor --agent codex --agent devin --agent hermes-agent`; Cursor and Codex share `.agents/skills/`. The CLI may also write a `skills-lock.json` in your project; that file can contain local paths, so look at it before committing it.

Manual install: copy the whole `skills/sureforge/` folder, including `LICENSE`, `references/`, and `assets/`, into your host's skill directory.

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

## How it has been tested

Three kinds of evidence, kept apart because they prove different things.

Mechanical checks you can rerun from this repository: the unit tests (see [Verification](#verification)) pass on Python 3.11 and 3.14, and every fault listed in `scripts/mutation_audit.py` is caught by them when seeded into a temporary copy. The skill passes the reference `skills-ref` validator at the commit pinned in `review/toolchain.json`.

Installation checks, run locally with Skills CLI 1.5.23 in an isolated project: copies installed for the five CLI targets Claude Code, Cursor, Codex, Devin, and Hermes (four directories, since Cursor and Codex share one) were byte-identical to `skills/sureforge/`, and Devin CLI 3000.6.14 listed the installed skill. Installation from the public repository is checked when a release is tagged and recorded in that release's notes, not here.

Behavior, from two small pilots on synthetic inputs. These are the owner's observations; the run logs are not part of this repository.

- GLM-5.2 through Devin, skill installed, 38 sessions (13 scenarios, 20 activation prompts, 5 tasks). The model followed the workflow in 12 of 13 scenarios and partially in one. It did not activate on any of the 10 prompts labeled as not needing the skill, and activated on 5 of the 10 labeled for activation (that set includes two explicit invocations and one light-tier typo fix, so the figure is not an implicit-selection rate). The five tasks were correct except the visual render the model could not perform, which it reported as blocked instead of claiming. Single arm, no control.
- Grok 4.6 at maximum effort, with and without the skill, 24 runs: 4 tasks at two repetitions per arm (16) and 4 scenarios at one repetition per arm (8). Both arms met every frozen criterion. The skill arm added a declared tier, an explicit "self-review-only" disclosure when no reviewer existed, coverage ledgers, and evidence records, at the cost of reports two to three times longer and extra process files on the larger tasks.

What has not been done: the planned three-arm study against the owner's confirmed baseline instructions, tests on visual-document tasks, and broader model and host coverage. On a strong model and well-specified tasks the pilots show no accuracy gain, only more explicit process. Measure it on your own work before relying on it.

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
