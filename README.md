# SureForge

An instruction-only Agent Skill for quality control on complex tasks: research first, make decisions explicit, work through verifiable gates, review independently, and deliver with evidence.

**Version:** 0.1.0-alpha.3 — unpublished review candidate. **License:** MIT. **Maintainer:** Da7-Tech.

SureForge aims to improve the reliability of the first user-facing delivery. That is a goal, not a measured performance claim. Local package checks do not demonstrate that a model will obey the workflow or outperform a baseline. The previous candidate received an external review; this repair candidate requires the next review on its own snapshot. The planned three-arm evaluation remains incomplete. Any separately reported two-arm pilot is narrower evidence, not a general performance guarantee.

## What it does

1. **Research and clarify:** understand the request, research relevant uncertainty, analyze from three perspectives, ask decision-changing questions, then compare alternatives.
2. **Plan:** map the current contract to outputs, steps, coverage, checks, permissions, resources, and stop conditions.
3. **Execute:** keep sequential implementation with one owner, investigate findings before repairing, and return to planning when the plan itself is wrong.
4. **Deliver:** inspect the agreed scope on the final version, exercise the recipient's path, and report supported results and limitations.

Each gate is **READY**, **REPAIR**, or **BLOCKED**. There are at most three review rounds per gate: the initial round and two repair-and-recheck rounds. Exhausting the limit with a material blocker does not turn failure into delivery.

## Scales to the task

| Tier | Typical use | Expected verification |
| --- | --- | --- |
| Light | Small, clear, reversible task | Direct owner check; no mandatory research or review ceremony. |
| Standard | Substantial, bounded multi-step work | Four gates, at least two complementary owner methods per gate, and independent plan/delivery review when permitted and available. A required standard-tier reviewer performs at least one meaningful method over its complete agreed scope. Missing review is disclosed; explicitly required review still blocks. |
| Full | Explicit full mode or high-risk/extensive-assurance work | Three owner methods plus three methods freely selected by an independent reviewer at every gate. An extra critic is used when risk or a material dispute warrants it and permission exists. |

A complete-coverage requirement applies in every tier. A trivial edit does not become a research project simply because the skill was invoked. Conversely, a required full review cannot be replaced silently by the owner writing a second opinion in the same context.

## Use it

After installing the skill in a host that supports Agent Skills, use its skill picker or ask:

> Use SureForge for this task. Research the important unknowns before questions, then build a verifiable plan and keep the result local until I approve publication.

For explicit full mode:

> Use SureForge in full mode. Do not advance a gate without three owner verification methods and three independently chosen reviewer methods. If a required tool or reviewer is unavailable, tell me instead of simulating the check.

Exact invocation syntax and capabilities vary by host. See [platform notes](skills/sureforge/references/platforms.md). This package grants no permissions and does not bypass the host's rules.

## Local installation

The source is [skills/sureforge](skills/sureforge/SKILL.md), not an active host configuration. Copy the complete folder, including its license, references, and assets, into a skill directory approved for your host. Do not overwrite an existing installation without reviewing it.

For a local **Devin project** using the external Skills CLI, run from the target project and point to your local SureForge source:

```bash
DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 npx --yes skills@1.5.23 add ../SureForge --skill sureforge --agent devin --copy -y
```

Here `../SureForge` assumes the target project is a sibling of the source directory. Adjust the source path to your layout. Check that `.devin/skills/sureforge` does not already exist before running the command. The CLI writes project installation files and may create `skills-lock.json`. That lock file can retain local source paths, including identifying directory names; inspect it before any public commit rather than assuming it is safe metadata. The CLI requires Node.js 22.20.0 or newer and downloads external tooling if not cached; SureForge itself has no runtime dependency.

The local smoke-test procedure uses this exact installer version in an isolated project with telemetry disabled, then checks every installed file against the source. See [verification](#verification) for the reproducible comparison. File installation is not proof of live host behavior. No remote installation command is presented as tested, and no public GitHub repository is assumed to exist.

## What counts as evidence

- Evidence names the artifact snapshot, current contract, environment, inspected units, method, observation, and limits.
- Unaffected evidence may be reused only after a documented applicability check, explicitly labeled reuse.
- A global layout change requires renewed full visual coverage; old screenshots do not prove the new document is correct.
- Every agreed page, state, or content/environment combination must be accounted for. A sample, page count, or automated check is not a substitute for required visual or semantic inspection.
- A reviewer's bare approval is insufficient. No findings is acceptable after actual methods, evidence, and coverage are reported.
- A mistaken finding is investigated and refuted with evidence, not implemented merely to satisfy a reviewer.

The text cannot technically enforce these rules. New context does not guarantee independent errors. Shared instructions, models, and blind spots remain possible. Host capabilities, permissions, source quality, and task scope limit what can be verified.

## Package map

- [Skill entry point](skills/sureforge/SKILL.md): lean runtime instructions and on-demand resource links.
- `skills/sureforge/references/`: four phases, review protocol, verification catalog, and dated platform notes.
- `skills/sureforge/assets/`: reviewer and critic briefs, task ledger, and coverage CSV template.
- [Evaluation kit](evals/README.md): thirteen failure scenarios, twenty activation queries, five synthetic tasks, a three-arm study protocol, and local test tooling.
- [Review contract](review/CONTRACT.md): the agreed requirements and unresolved evaluation inputs.
- [Neutral reviewer intake](review/REVIEWER.md): instructions for fresh-context review before publication.
- [Contributing](CONTRIBUTING.md): change, testing, privacy, and release expectations.

Only `skills/sureforge/` needs to be installed. Repository tests and review tooling are not required when using the skill.

## Verification

The local tools use Python 3.11 or newer and the standard library. From the repository root:

```bash
python3 -B -m scripts.check_package
python3 -B -m unittest discover -s tests -v
```

The first command checks the declared file inventory, skill metadata, relative links, licenses, requirement references, evaluation data, syntax, and selected privacy patterns. The second tests package rejection paths, the abstract gate model, and evaluation metrics. Neither command runs a model or proves behavioral improvement.

After a local isolated installation, set `INSTALLED_SKILL` to the actual installed skill directory:

```bash
python3 -B -m scripts.verify_install --installed "${INSTALLED_SKILL:?Set INSTALLED_SKILL to the isolated installed directory}"
```

Set `EVIDENCE_DIR` to an existing output directory outside the source, then build a new neutral archive:

```bash
python3 -B -m scripts.package_review --output "${EVIDENCE_DIR:?Set EVIDENCE_DIR to an existing external directory}/SureForge-0.1.0-alpha.3-review.zip"
```

The builder refuses an existing output path, validates the source, hashes every distribution file, normalizes archive metadata, and verifies the new archive against the source. The archive contains the `SureForge/` source directory and a sibling `MANIFEST.json`, so the extracted source can run the same checks without treating generated metadata as a source file. Author evaluation reports, third-party tooling, raw sessions, and explicitly ignored Finder metadata are not included.

To check only an archive's integrity, set `REVIEW_ARCHIVE` to its path:

```bash
python3 -B -m scripts.package_review --verify "${REVIEW_ARCHIVE:?Set REVIEW_ARCHIVE to the archive path}" --archive-only
```

Omit `--archive-only` to compare with the current source, optionally selecting it using `--root`. Archive-only verification reports that no source comparison was made. ZIP-byte hashes can vary with compression-library versions; compare `source_sha256` and the per-file manifest for logical source identity. Neither an internally consistent manifest nor a matching hash is a signature or proof of reviewer approval.

## Evaluation status and release limits

The five benchmark tasks and thirteen failure scenarios are synthetic. The owner has not supplied redacted real incidents. The current-instructions baseline is an explicitly labeled reconstruction awaiting confirmation. Twenty activation labels are expectations, not observed activation rates.

Before making performance claims, run matched fresh-context tasks with no skill, with confirmed frozen owner instructions, and with SureForge. Include unsuccessful attempts and reviewer costs, use independent blind grading, report residual defects and harmful repairs, and check simple-task regressions. The [evaluation protocol](evals/README.md) explains the distinction between local deterministic tests and live agent runs.

Before any publication, obtain independent review, resolve material findings, audit the actual Git identities and distributable metadata, obtain explicit release approval, and test the intended remote installation. An unbenchmarked experimental release would require an explicit decision and must retain that limitation; local checks are not permission to publish.

## Design influences

The packaging follows the [Agent Skills specification](https://agentskills.io/specification) and its guidance on [authoring](https://agentskills.io/skill-creation/best-practices.md) and [evaluation](https://agentskills.io/skill-creation/evaluating-skills.md). The broader design conversation considered [Superpowers](https://github.com/obra/superpowers), [Spec Kit](https://github.com/github/spec-kit), and [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) as workflow references. SureForge's instructions are original text; these links do not imply endorsement, unique invention, comparative testing, or copied implementation.

No error-free, universal superiority, or quantified performance promise is made. See [LICENSE](LICENSE).
