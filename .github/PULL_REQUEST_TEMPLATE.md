**What this changes**

**Why**
The failure, gap, or request behind the change. Link the issue if there is one.

**Checks**
- [ ] `python3 -B -m scripts.check_package` passes
- [ ] `python3 -B -m unittest discover -s tests` passes
- [ ] If a validator check was added or changed: a negative test exists, and where a one-line substitution can disable the check it is listed in `scripts/mutation_audit.py`
- [ ] If the skill text changed: the affected scenario in `evals/cases.json` or requirement mapping in `review/requirements.json` was updated
- [ ] If files were added or removed: `review/inventory.json` was updated
- [ ] No personal names, contact details, local paths, credentials, or transcripts

**Notes for the reviewer**
Anything you could not check yourself, and hosts or models this was tried on, if any.
