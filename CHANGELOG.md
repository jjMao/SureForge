# Changelog

## 0.1.0-alpha.3 — first public alpha (2026-09-09)

### Fixed

- Require all three SF-39 arms before result records can set `comparison_eligible`; a complete narrower pilot remains descriptively useful but reports each absent comparison arm.
- Exercise that gate using unit fixtures tagged `model-run`, including a fully populated positive control, instead of relying on the unrelated synthetic-data limitation.
- Avoid privacy false positives on approximate numeric fractions/rates and embedded tildes while retaining detection of standalone named-home paths.

### Published

- Third external review of this snapshot found no new issues; the 21 findings from the three rounds are closed. The skill text is unchanged since the review; only README, CHANGELOG, and the review contract were updated for publication.
- Published to GitHub as Da7-Tech/SureForge by the owner's explicit decision as an experimental alpha with narrowed claims. Remote installation with the Skills CLI was tested on the published repository (five host targets, byte-identical to the source).
- Two behavioral pilots on synthetic inputs are summarized in the README: a single-arm GLM-5.2 adherence run (38 sessions) and a two-arm Grok 4.6 comparison (24 runs). Neither is the planned three-arm study, and neither shows an accuracy gain on a strong model; both show the workflow being followed without harmful behavior.

## 0.1.0-alpha.2 — unpublished review candidate

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

## 0.1.0-alpha.1 — unpublished review candidate

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
