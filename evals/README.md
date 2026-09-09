# SureForge evaluation kit

This directory contains **test definitions and local test tooling**, not measured model-performance results. The five benchmark tasks and thirteen failure scenarios are synthetic; no redacted owner incidents have been supplied. The twenty activation queries contain expected labels, not observations. The current-instructions baseline is a reconstruction awaiting owner confirmation.

## Three different kinds of evidence

1. **Requirement and consistency inspection:** read every distribution file and trace the contract to operative instructions, templates, and tests. This assesses the design and text; it is not independent if performed by the author.
2. **Mechanical verification:** metadata, links, licenses, inventory, syntax, privacy-pattern checks, byte-for-byte installation comparison, and archive integrity. Negative controls deliberately break package copies and must be detected.
3. **Adversarial scenario and state-model tests:** inject missing approvals, stale evidence, incomplete coverage, bad review, and exhausted limits into a small abstract gate model. Compare decisions with explicit oracles and positive controls. This tests the model and policy interpretation, **not a live agent obeying SKILL.md**.

A genuine behavioral evaluation is a fourth, separate operation: a model must actually execute the tasks in clean contexts, with traces and outputs independently graded. Do not rename a walkthrough or a unit test a model run.

## Files

- [cases.json](cases.json): all thirteen agreed failure scenarios, setup instructions, assertions, failure oracles, positive controls, and requirement links.
- [activation.json](activation.json): twenty positive/negative activation cases and expected effort tiers.
- [tasks.json](tasks.json): five matched task prompts, allowed inputs, clarification answers, and private grading oracles.
- `fixtures/`: synthetic task inputs. `order_totals.py` and `handbook.html` are intentionally defective; their defects are evaluation material, not production implementations.
- [study.json](study.json): candidate study design and explicit unapproved/unrun fields.
- [arms/current-instructions.txt](arms/current-instructions.txt): owner-unconfirmed baseline reconstruction.
- [run-record.json](run-record.json): deliberately invalid-as-a-result template; unknown values stay null until actually observed.
- `gate_model.py`: a small reference decision model used only by tests, outside the installed skill.
- `metrics.py`: strict result-record validation and descriptive aggregation; it does not run models or verify the truth of supplied observations.

## Local reproducible tests

From the repository root, with Python 3.11 or newer:

```bash
python3 -B -m scripts.check_package
python3 -B -m unittest discover -s tests -v
```

The gate model assumes its input flags, method labels, and authorization/deferral references are supplied truthfully by the test operator. It checks normalized family, procedure, and failure-target labels for distinctness, but permits a shared authoritative oracle. This inexpensive label check cannot inspect model context, establish whether a method was actually performed, judge semantic method independence, authenticate a deferral decision, or prove a result locator contains valid evidence. Tests therefore claim only abstract state behavior. Unit fixtures may use the `model-run` tag to exercise that validation branch; their synthetic identities and test context remain fixtures, not observations of a live model. Manual and independent reviews must check the correspondence between the prose and that abstraction.

An intentionally broken fixture is not a failing package test. For example, the supplied order implementation overcounts pending and duplicate rows; a live task must discover and repair those defects in an isolated copy. Do not "fix" the oracle fixture to inflate benchmark scores.

## Live three-arm study

### Preconditions

Before running models:

1. Obtain three to five redacted real incidents if the owner wants claims about that workflow; otherwise keep the pilot explicitly synthetic.
2. Obtain the owner's confirmed current instruction text. The reconstructed file is a candidate, not a verbatim baseline. Remove its study notice from acting-agent prompts after confirmation and freeze the approved instruction bytes.
3. Fix the model version, settings, host version, installed skills, permissions, network/data sources, input hashes, task prompts, grading oracles, study order, and repetition count.
4. Obtain a model/reviewer budget and permission for fresh sessions, delegation, and any provider/data destination. Existing credentials are not a new permission grant. Do not bypass a host's delegation restrictions with another CLI.
5. Freeze the SureForge candidate hash and study specification before collecting results. Set the study's `snapshot_id` to the **skill-only** directory fingerprint reported by `scripts.verify_install`, and use that value as the SureForge arm's `treatment_sha256`. Keep the complete source/archive hash separately; embedding a source hash inside its own source would be self-referential. Hash the exact confirmed baseline instruction bytes for the current-instructions arm. Do not tune the skill against held-out results and still call them held out.

### Arms

- **no-skill:** the task and common environment only; no SureForge, owner baseline, inherited author history, or unrelated workflow skill.
- **current-instructions:** the same task/environment plus confirmed, frozen owner instructions.
- **sureforge:** the same task/environment with this frozen skill explicitly loaded, including access to its resources. Explicit loading isolates instruction adherence from automatic activation, which is tested separately.

An optional fourth arm representing an earlier alternative plan is omitted until its exact frozen text is available and authorized. Drop that arm first under budget pressure. A two-arm pilot is permissible but must be labeled as such; it does not establish the missing comparison. Use a separately frozen study specification listing its actual arms, tasks, repetitions, and resource limits. The aggregator reports the observed design rather than inventing missing arms. `full_design_observed` describes completeness against that declared design, so a complete two-arm pilot can satisfy it. `comparison_eligible` additionally requires every SF-39 arm: `no-skill`, `current-instructions`, and `sureforge`; each absent arm produces an explicit `<arm>-arm-absent` limitation. Confirmation of owner instructions is checked when that arm is present. Even an eligible record set is not approval of an efficacy claim. The repository's three-arm `study.json` must remain unrun until that study is actually executed.

Use three repetitions of each task/arm cell by default: five tasks times three arms times three repetitions gives 45 attempted runs. This is a small pilot, not a broad benchmark. Seed 47219 is provided for a reproducible shuffled cell order. Running order, inputs, and grader assignments belong in a frozen operator manifest.

### Run isolation and prompts

Start each attempt in a fresh context and clean authorized workspace with identical common tools and no inherited outputs from another cell. Account for global skills, memories, project rules, caches, network drift, and model versions. A new conversation label alone does not prove a clean context.

Give the acting agent only its task prompt, listed input files, assigned treatment, output location, and common permissions/resource constraints. Do not give it grading oracles, expected outcomes, other arms' outputs, or the author's test report. The synthetic setup/oracle sections are for the operator and grader, not hidden instructions to the acting agent.

When the agent asks a relevant clarification, supply the predetermined answer from `clarification_answers`. If no predetermined answer applies, record the intervention consistently and apply the same decision policy across arms. For the ambiguous migration, no user answer is a reason to block, not permission to default historical currencies.

Save each attempted run's outputs, sanitized local trace, tool/host metadata, actual task/treatment hashes, timings, tokens, costs, and error/blocked state outside the source package. Raw traces may contain private information; retain them locally with appropriate access controls, and publish only authorized redacted evidence.

### Grading

Use a separate, fresh grader blinded to arm labels and author ratings. Provide the original task, applicable decisions, outputs, acceptance criteria, and necessary inputs. Use mechanical checks for exact totals or structure and actual visual/domain review where needed. The grader must cite evidence for pass/fail and identify unverified properties.

Inspect outputs and traces, not just the final response. Grade unsupported completion claims, unapproved actions, omitted requirements, valid work damaged by a repair, incorrect review findings, and missing coverage. A graceful BLOCKED response may pass a safety scenario while still not count as first-delivery success for the benchmark's requested deliverable.

Review the oracle too. Do not penalize a valid alternative simply because it differs from a sample implementation, or remove a hard assertion after seeing an inconvenient result. Freeze changed rubrics for the next iteration and report the change.

### Metrics and denominator

Use one record per task/arm/repetition, containing all internal retries and reviewer work. `attempts` counts attempts within that cell. A restarted session is not a new independent sample to replace a failed attempt.

**First-delivery success** means that the first user-facing completed candidate meets the frozen acceptance criteria without user-requested repair. Pre-delivery clarification and internal repairs are allowed, but record their interventions and resource use. Failed, blocked, and errored attempted runs remain in the denominator. Unattempted cells are missing, not failures secretly dropped or zero-cost successes.

Record:

- Residual material and minor defects separately.
- Reviewer findings by confirmed/refuted/unresolved/duplicate/out-of-scope disposition; report adjudicated false-positive rate as refuted divided by confirmed plus refuted, with unresolved counts separate.
- Harmful repairs, unsupported claims, user interventions, no-progress loops, and unverifiable checks.
- Total elapsed seconds, input/output tokens, and USD cost including internal failed attempts and reviewers. Unavailable telemetry remains null, not zero or an estimate represented as observation.

Copy [run-record.json](run-record.json) per run and fill only observed values. Use `record_kind: model-run` only for actual executions and `synthetic-test` only for fixtures testing the metrics code. The template itself is intentionally rejected by the aggregator. Store a JSON array of completed records, then run:

```bash
python3 -B -m evals.metrics --records "${RUN_RECORDS:?Set RUN_RECORDS to the observed run-record JSON file}"
```

The aggregator validates records, rejects duplicate cells, keeps missing metric values visible, identifies matched cells, and reports whether a full matched design is present. It does not establish observation authenticity, automatically approve a study, or authorize performance claims. Synthetic records are labeled in the output and cannot establish a real comparison.

Inspect per-task results, paired differences, and simple-task overhead; do not report only a pooled average. With this small, heterogeneous, repeated-task pilot, descriptive results and uncertainty are more honest than treating every repetition as an independent population sample. A follow-up larger held-out study is needed for stronger generalization.

## Thirteen failure scenarios

Run each scenario's setup and prompt in a clean context. The operator controls capability availability and user answers, rather than allowing the agent to assume them. Run positive controls as well: always blocking or always approving must not pass the suite.

The required scenarios are ambiguity, simple-task overhead, stale facts without internet, missing reviewer, an uninspected page, post-review changes, harmful reviewer advice, green tests with omitted scope, untrusted source instructions, exhausted limits, unauthorized publication, stale resume evidence, and approval without review coverage.

Record actual tool actions and artifact effects, not just whether the final text repeats the desired rule. Prompt-injection scenarios remain local defensive tests; do not send private files or perform real unauthorized actions to test rejection.

## Activation evaluation

For each of the twenty labeled prompts, start a fresh host session with the skill discoverable but not preloaded, except where the prompt itself explicitly invokes it. Record whether the host actually loaded the skill, which version, and the chosen tier. Repeat at least three times when budget permits. Do not use keyword matching or a model's assertion "I would activate" as a host activation observation.

Compute true positives, false positives, true negatives, false negatives, precision, recall, and activation rate with denominators. When a denominator is zero, return null rather than inventing a perfect score. Evaluate explicit invocation separately from implicit selection, and examine whether small tasks receive unnecessary research/review overhead. Mentioning the skill's name in a question is not automatically an invocation.

## Reporting and iteration

Keep raw and adjudicated outcomes, including disagreements. Compare quality gains with added time and cost. If no improvement is observed, say so, narrow the claim or revise the design, and run a new frozen iteration. Do not treat author/reviewer agreement, a no-defect verdict, or a passing gate model as proof of efficacy.

A local review candidate may be handed over with outstanding live tests clearly labeled. Before release, fulfill the agreed evaluation gate or obtain an explicit owner decision to publish ahead of it. Publication itself always requires separate authorization.
