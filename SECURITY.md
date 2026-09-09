# Security

SureForge is text. The installed skill contains no executable code, runs nothing at install time, and asks for no permissions of its own. The scripts and tests in this repository are for maintainers checking the package and are not installed with the skill.

What can still go wrong is the text itself: a sentence that a model reads as permission to delegate, publish, spend, delete, or bypass a host control, or reference material that could be used to smuggle instructions into an agent's context. The skill is written to refuse those readings (external content is data, host permissions win, no gate becomes an approval), but wording can have holes.

If you find text in this repository that could steer an agent into unsafe or unauthorized behavior, report it through GitHub's private vulnerability reporting on this repository, or open an issue if the problem is already public. Include the file and line, the reading you are worried about, and, if you observed it, the host and model. Please leave out transcripts and personal data.

There is no bug bounty. Reports are read and answered in the repository.
