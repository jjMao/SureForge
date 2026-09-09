# Contributing to SureForge

SureForge is an instruction-only Agent Skill. Prefer a clear procedure over more slogans, additional roles, or a runtime framework. Keep the installed core portable and load detailed resources only when relevant.

## Before a change

Read the [review contract](review/CONTRACT.md), the [skill entry point](skills/sureforge/SKILL.md), and the affected reference. Identify the requirement or observed failure motivating the change. Preserve the four phases, review independence, honest evidence accounting, authority boundaries, and graduated effort unless the owner explicitly approves a contract revision.

For a reported bug, create a reproducible regression first where possible. For a behavioral problem, retain the sanitized prompt, host/model versions, task snapshot, observed behavior, and outcome oracle. Do not publish raw transcripts or personal data.

## Implementation expectations

- Use English in the distributable and public identity `Da7-Tech` only where attribution is needed.
- Do not add vendor-specific permissions, forced models, hooks, or executable dependencies to the installed skill without a justified scope change.
- Keep SKILL.md short and link each resource directly from the entry point with a clear loading trigger.
- Do not count repeated prompt wording as distinct verification or owner self-review as independent review.
- Distinguish documentation inspection, installation, discovery, instruction adherence, and comparative model performance.
- Update the affected tests, requirement mapping, declared inventory, and version/changelog together when appropriate.

## Local checks

Use Python 3.11 or newer from the repository root:

```bash
python3 -B -m scripts.check_package
python3 -B -m unittest discover -s tests -v
```

A local Skills CLI installation can additionally be checked with:

```bash
python3 -B -m scripts.verify_install --installed path/to/isolated/installed/sureforge
```

Use the exact tested installer version and keep install telemetry disabled. Never overwrite an existing real skill installation for a smoke test.

`python3 -B -m scripts.mutation_audit` seeds each fault listed in the script into a temporary copy and confirms that the named test module fails; the source tree is not touched. When you add a check to a validator, add a negative test for it and, where a one-line substitution can disable the check, add that substitution to the mutation list. A check with no negative test can be removed without any test noticing.

See [evals/README.md](evals/README.md) for failure scenarios, fresh-context live runs, activation measurements, grading, and metrics. Unit tests of the abstract gate model are not tests of a model obeying the skill. Add negative controls so a validator that simply approves or blocks every candidate cannot pass the test suite.

## Local linter boundaries

The version field uses ASCII SemVer syntax: three numeric components without leading zeros, optional prerelease identifiers, and optional build metadata. Stable, alpha, beta, and rc versions are supported. The package check requires the same version string in VERSION, the skill metadata, the study's candidate version, and as text in the README, changelog, and review contract; a bump that misses any of them fails the check.

The repository frontmatter linter intentionally accepts a small authoring subset: single-line plain strings or JSON-compatible double-quoted strings, plus a flat `metadata` map indented by two spaces. Anything else is rejected rather than read as a string: YAML null, booleans, numbers, lists, maps, folded or literal blocks, single-quoted strings, anchors, aliases, tags, and plain values with a trailing comment or an embedded `: `. This is not an added requirement of the Agent Skills standard; use the external reference validator for a separate format check and revise the local linter deliberately if this repository adopts a wider syntax.

Privacy patterns cover selected email, named-home-path, credential, and phone shapes. Home-relative documentation paths are review hints, not automatic evidence of a private identity. The named-home heuristic requires a standalone tilde followed by a letter or underscore, avoiding false positives on approximate numeric fractions or rates; it does not recognize every legal account-name syntax. The Unicode check detects non-Latin-script letters, not every non-English sentence; Latin-script languages still require manual review. These checks do not replace complete content/provenance inspection. Ordinary `.DS_Store` files are reported and excluded from distribution fingerprints and archives, not deleted; unknown files and symlinks are not silently ignored.

## Independent review

Provide a frozen artifact, latest contract, approved decisions, required inputs, and the [neutral reviewer intake](review/REVIEWER.md). Do not include author self-ratings or desired verdicts in a blind review package. Ask the reviewer to choose its own methods and report actual coverage and evidence. Investigate findings before applying changes; verify repairs and invalidated evidence on a new snapshot.

## Privacy and licensing

Inspect the entire distribution, including examples, generated archives, hidden files, metadata, and eventual Git history. Do not include personal names, personal email addresses, phone numbers, identifying local paths, credentials, session traces, or provider logs. Use synthetic or explicitly approved redacted examples. Automated privacy-pattern checks are only one layer; review the content and provenance manually.

Retain both MIT license copies. Cite genuine design influences without implying endorsement or copying licensed source unnecessarily. Third-party verification tools are separate dependencies and are not redistributed in the SureForge archive.

## Release policy

No automated check authorizes publication. Resolve material findings, obtain independent review and explicit owner approval, verify actual commit author/committer metadata without changing global Git configuration, and inspect the exact packaged candidate. Run the agreed live study before claims of benefit. If the owner explicitly approves an unbenchmarked experimental release instead, state that narrowed status prominently and do not claim the original benchmark requirement was met.

A remote install command must be tested against an authorized real repository before being labeled tested. Never push, create a public repository, create a release, alter security controls, or publish private evidence merely to make evaluation easier.
