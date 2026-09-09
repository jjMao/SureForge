# Changelog

## 1.0.0 — first public release (2026-09-09)

The skill text under `skills/sureforge/` is the third review candidate with two changes: the version identifier, and the installer-verification paragraph in `references/platforms.md`, which now names the five CLI targets and says how remote installation is checked. The root documentation, package checks, and tests were revised for publication as described below.

Four independent review rounds preceded this release. Rounds one to three (on the alpha candidates) closed 21 findings; the third found no new issues in the skill text. Round four reviewed the 1.0.0 candidate as four independent reviews of the same snapshot and led to the fixes listed here. The owner decided to publish without waiting for the three-arm study, with the claims narrowed accordingly.

Installation from the public repository with the Skills CLI is checked against the tagged release and recorded in the GitHub release notes; this file only records what can be verified from the source itself.

### Fixed

- The frontmatter linter now rejects YAML forms it does not support (null, booleans, numbers, lists, maps, block scalars, single-quoted strings, anchors, tags, and trailing comments) instead of silently reading them as plain strings.
- The package check requires the current version string to appear in the README, this changelog, and the review contract, so a version bump that misses the human-readable documents fails.
- Added negative tests for checks that previously had none: absolute and dot-segment inventory paths, archive metadata normalization on the verification side, resources not linked from `SKILL.md`, one-way requirement-to-scenario maps, and the `rounds-exhausted` reason at the third round. The live repository root is now validated by the test suite as well, so an unlisted file fails the tests and not only the package check.
- `scripts/mutation_audit.py` ships with the repository so the seeded-fault claim can be rerun; it carries the 20 faults used in the earlier rounds plus 8 that target the gaps above.
- Removed statements that described publication and remote installation in the past tense inside the source snapshot; they contradicted the platform notes and cannot be true of a snapshot that is itself the release candidate. The platform notes and contract now say where the remote-side checks are recorded.
- The README separates mechanical, installation, and behavioral evidence; names the Skills CLI target identifiers (including `hermes-agent`); states that Cursor and Codex share one directory; gives the Grok pilot's repetition breakdown; and describes the activation figure's denominator (two explicit invocations and one light-tier case are in the positive set).
- The reviewer intake no longer states that test summaries are absent from the bundle; the public documents in the source do carry the owner's summaries, and the intake now says to treat them as claims to verify.
- `review/toolchain.json` describes the installer's dependency versions as observed in the pinned test install rather than as pins, since the installer declares caret ranges.
- Placeholder account names in a privacy test were replaced with neutral ones.

### Pilots

Two behavioral pilots on synthetic inputs are summarized in the README: a single-arm GLM-5.2 adherence run (38 sessions) and a two-arm Grok 4.6 comparison (24 runs). Neither is the planned three-arm study, and neither shows an accuracy gain on a strong model. No harmful behavior was observed in the inspected runs. No performance claim is made.

The entries below are the internal review candidates that preceded this release. None of them was published.

## 0.1.0-alpha.3 — third review candidate

### Fixed

- Require all three SF-39 arms before result records can set `comparison_eligible`; a complete narrower pilot remains descriptively useful but reports each absent comparison arm.
- Exercise that gate using unit fixtures tagged `model-run`, including a fully populated positive control, instead of relying on the unrelated synthetic-data limitation.
- Avoid privacy false positives on approximate numeric fractions/rates and embedded tildes while retaining detection of standalone named-home paths.

## 0.1.0-alpha.2 — second review candidate

### Fixed

- Accept valid SemVer releases and prereleases instead of hard-coding alpha versions, and permit activation sets larger than twenty with unique canonical IDs.
- Count distinct normalized failure targets as well as method families and procedures; retain legitimate shared oracles.
- Require repair or documented authorized deferral for confirmed non-material findings, and classify duplicate method IDs consistently as malformed records.
- Distinguish unknown mandatory quality metrics from known nonzero failures.
- Ignore and report ordinary Finder metadata without changing source identity or including it in archives; preserve rejection of symlinks and unrelated files.
- Return concise CLI errors for invalid or existing report destinations without overwriting evidence.
- Add selected credential/obfuscated-email patterns, nonblocking home-path review hints, and an accurately named non-Latin-script signal.

### Clarified

- Standard-tier reviewer minimums, conditional plan context, dated host observations, generic evidence paths, installer-lock privacy, supported frontmatter syntax, and compression-dependent archive bytes.
- A09 now explicitly resumes standard-tier work. A04 retains a documented high-assurance planning rationale rather than conflating planning with execution permission.
- Archive-only verification is explicitly available and does not claim comparison with a current source directory.

### Evaluation boundaries

- The owner authorized a GLM 5.3 max-effort pilot with and without the repaired skill, including bounded subreviewers. Authorization is not a result.
- The three-arm study remains unrun until its separate inputs, including confirmed owner instructions, are supplied. A two-arm pilot must not be reported as that full study.
- No publication or general performance claim is authorized by this revision.

## 0.1.0-alpha.1 — first review candidate

### Added

- Instruction-only SureForge skill with graduated effort and explicit full mode.
- Four phases: research and clarification, plan, execute, and deliver.
- READY/REPAIR/BLOCKED gates, independent review briefs, evidence-bound coverage, finding triage, and a three-round limit.
- Capability fallbacks, privacy/authority boundaries, and resumable task and coverage templates.
- Separate synthetic evaluation kit: thirteen failure scenarios, twenty activation queries, five benchmark tasks, and a three-arm study protocol.
- Standard-library local validators, abstract gate-model tests, metrics tooling, and neutral review-archive generation.

### Not established

- Live model performance or superiority over the no-skill or current-instructions baselines.
- Behavioral compatibility across Claude Code, Codex, Cursor, Hermes, or a fresh Devin task session.
- Independent review approval, owner-confirmed baseline instructions, or validation on redacted real owner incidents.
- Remote installation, public release, or publication authorization.

The version identifies a local candidate, not a released tag or a claim that the pending checks have passed.
