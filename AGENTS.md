# AGENTS.md

## Index

* [General rules](#general-rules)
* [Change log](#change-log)
* [Change log entry format](#change-log-entry-format)
* [Plan creation](#plan-creation)
* [Git commit rules](#git-commit-rules)
* [Before implementing a change](#before-implementing-a-change)
* [During implementation](#during-implementation)
* [Validation](#validation)
* [Existing failures](#existing-failures)
* [Docker and infrastructure changes](#docker-and-infrastructure-changes)
* [API changes](#api-changes)
* [Database and persistent state changes](#database-and-persistent-state-changes)
* [Security](#security)
* [Scope control](#scope-control)
* [End-of-task report](#end-of-task-report)
* [Git safety](#git-safety)
* [Core principle](#core-principle)

---

## General rules

These instructions apply to every change made in this repository.

Before modifying code:

1. Read the existing implementation and surrounding code.

2. Check the current Git branch with:

   `git branch --show-current`

3. Understand the purpose of the requested change before editing files.

4. Do not modify unrelated code.

5. Preserve the existing architecture, conventions, and coding style unless a change is explicitly required.

6. Prefer small, focused changes over large unrelated refactors.

7. Do not remove existing behavior unless it is explicitly requested or clearly obsolete because of the requested change.

8. Do not assume that a broader refactor is desirable simply because a local improvement is possible.

9. Preserve existing user changes that are unrelated to the current task.

---

## Change log

Every significant code change must be documented.

The change log must be written in French.

Change logs are stored using the following structure:

`docs/changes/<YYYY-MM-DD>_<branch-name>/changes.md`

Where:

* `<YYYY-MM-DD>` is the current date.
* `<branch-name>` is the current Git branch name.
* `/` in branch names must be replaced with `-`.

Examples:

Branch:

`change-mlflow-port`

on `2026-09-11`

becomes:

`docs/changes/2026-09-11_change-mlflow-port/changes.md`

Branch:

`feature/train-api`

on `2026-09-11`

becomes:

`docs/changes/2026-09-11_feature-train-api/changes.md`

Branch:

`refactor/predict-api`

on `2026-09-11`

becomes:

`docs/changes/2026-09-11_refactor-predict-api/changes.md`

Before writing the change log:

1. Determine the current date.

2. Determine the current Git branch using:

   `git branch --show-current`

3. Replace `/` in the branch name with `-`.

4. Build the path:

   `docs/changes/<YYYY-MM-DD>_<branch-name>/changes.md`

5. Create the directory if it does not already exist.

6. Create `changes.md` if it does not already exist.

7. Append new significant changes to the existing `changes.md` file for that date and branch.

Do not create multiple change-log files for the same branch on the same day.

If several significant changes are made on the same branch during the same day, append all entries to the same file.

Do not create change-log entries for insignificant actions such as:

* formatting-only changes;
* typo corrections;
* temporary debugging;
* exploratory commands;
* comments that do not alter behavior;

unless they are part of a meaningful logical change or commit.

---

## Change log entry format

Every significant logical change must append an entry using this structure:

```markdown
## Short descriptive title

**Message de commit**

`type(scope): short description`

**Ce qui a changé**

- Description de la modification principale.
- Description des modifications importantes associées.

**Pourquoi**

- Expliquer pourquoi la modification était nécessaire.
- Mentionner le problème, le besoin, la contrainte ou la raison architecturale lorsque pertinent.

**Fichiers**

- `path/to/file.py`
- `path/to/other_file.yml`

**Validation**

- Tests exécutés.
- Linting ou formatage exécuté.
- Validation manuelle effectuée si nécessaire.
```

The change log must be written in French.

The Git commit message must be written in English.

Keep entries concise.

The change log must explain both:

* WHAT was changed;
* WHY it was changed.

Do not paste large diffs.

Do not duplicate implementation details that are already obvious from the code.

Document architectural, operational, behavioral, compatibility, or security consequences when relevant.

---

## Plan creation

When the user explicitly asks to create a plan, create a persistent implementation plan before modifying the code.

The plan must be stored in the same date-and-branch directory used for the change log:

`docs/changes/<YYYY-MM-DD>_<branch-name>/plan.md`

Example:

Branch:

`feature/train-api`

on `2026-09-11`

becomes:

`docs/changes/2026-09-11_feature-train-api/plan.md`

Before creating the plan:

1. Determine the current date.

2. Determine the current Git branch using:

   `git branch --show-current`

3. Replace `/` in the branch name with `-`.

4. Build the path:

   `docs/changes/<YYYY-MM-DD>_<branch-name>/plan.md`

5. Create the directory if it does not already exist.

6. Inspect the relevant implementation, tests, configuration, documentation, and dependencies.

7. Create or update `plan.md`.

8. Do not begin implementation until the plan has been written.

The plan must be written in French.

The plan must define the implementation sequence clearly enough that each step can be implemented, validated, reviewed, and committed independently.

Use the following structure:

```markdown
# Plan d'implémentation

## Objectif

Description concise du résultat attendu.

## Contexte

Résumé du problème, de l'état actuel et des contraintes importantes.

## Périmètre

### Inclus

- Élément concerné.
- Élément concerné.

### Hors périmètre

- Élément volontairement non modifié.
- Élément volontairement non modifié.

## Étape 1 — Titre descriptif

### Objectif

Décrire précisément le résultat attendu à la fin de cette étape.

### Modifications prévues

- Modification prévue.
- Modification prévue.

### Fichiers potentiellement concernés

- `path/to/file.py`
- `path/to/test.py`

### Validation prévue

- Test ou commande de validation.
- Vérification manuelle éventuelle.

### Message de commit proposé

`type(scope): short description`

## Étape 2 — Titre descriptif

### Objectif

...

### Modifications prévues

...

### Fichiers potentiellement concernés

...

### Validation prévue

...

### Message de commit proposé

`type(scope): short description`

## Critères de fin

- Critère permettant de considérer le plan terminé.
- Critère permettant de considérer le plan terminé.
```

Each plan step must represent one logical unit of work that can reasonably correspond to one Git commit.

Do not make steps artificially small.

Do not combine unrelated work into the same plan step.

Each step must clearly identify:

* its objective;
* the expected modifications;
* the main files likely to be affected;
* the validation to perform;
* one proposed Git commit message.

Commit messages proposed in `plan.md` must be written in English and follow the Git commit rules defined in this file.

The plan is a living document.

If implementation reveals that the initial plan is incorrect, incomplete, or needs to change:

* update `plan.md`;
* keep the plan aligned with the actual implementation;
* document important changes in direction;
* do not silently diverge from the plan.

### Executing a plan

When implementing an existing `plan.md`:

1. Read the complete plan before modifying code.
2. Execute the steps in order unless there is a clear technical reason to change the sequence.
3. Work on one logical step at a time.
4. Do not mix changes belonging to later steps unless technically necessary.
5. At the end of each step:

   * run the validation defined for that step;
   * review the diff for that step;
   * update `changes.md`;
   * report the completed step in the chat;
   * propose the Git commit message for that step.

The user is responsible for creating the Git commit.

Do not automatically run `git commit`.

Do not automatically run `git push`.

Do not assume that a commit was created.

Do not continue by reporting that a commit exists unless the user created it or explicitly asked the agent to create it.

After each completed plan step, report something similar to:

```text
Étape 2 terminée.

Validation:
- pytest tests/train_api: passed
- ruff check: passed

Change log:
- docs/changes/2026-09-11_feature-train-api/changes.md updated

Commit proposé:
fix(train-api): recover interrupted training state
```

The proposed commit message in the chat must match:

* the message defined for the step in `plan.md`;
* the message recorded in `changes.md`.

If implementation requires changing the proposed commit message:

1. Update the message in `plan.md`.
2. Use the updated message in `changes.md`.
3. Propose the same updated message in the chat.

---

## Git commit rules

Everything related to Git commit messages must be written in English.

One change-log entry should correspond to one logical Git commit.

When executing a plan, one completed plan step should normally correspond to one logical Git commit.

Do not group unrelated modifications into the same change-log entry or commit.

Use Conventional Commits when possible.

Preferred commit types:

* `feat`: new functionality
* `fix`: bug fix
* `refactor`: internal restructuring without changing expected behavior
* `test`: tests
* `docs`: documentation
* `chore`: tooling, dependencies, infrastructure, configuration, or maintenance
* `perf`: performance improvement
* `ci`: CI/CD changes
* `build`: build system or dependency changes

Examples:

```text
feat(train-api): add training state recovery
fix(mlflow): use configured tracking port
refactor(predict-api): simplify model loading
test(train-api): add idempotency tests
chore(docker): simplify runtime volumes
```

The commit message stored in the change log must be the same message intended for the corresponding Git commit.

When a plan exists, it must also match the proposed commit message for the corresponding plan step.

Do not store commit hashes in the change log or plan.

Do not create a Git commit unless explicitly requested.

By default, the user creates commits manually.

Do not claim that a commit was created unless it was actually created.

---

## Before implementing a change

Before editing files:

1. Inspect the current implementation.

2. Inspect surrounding code.

3. Inspect relevant tests.

4. Check the current Git branch.

5. Check the working tree with:

   `git status`

6. Identify configuration, Docker, API, database, infrastructure, persistence, or dependency implications.

7. Determine whether the requested modification can be implemented without affecting unrelated components.

8. Identify existing conventions that should be preserved.

9. If a `plan.md` exists for the current date and branch, read it before making changes.

Do not start with a broad refactor when a focused change is sufficient.

Do not overwrite or discard existing uncommitted user changes.

---

## During implementation

While implementing:

* follow the project's existing coding conventions;
* keep functions and modules focused;
* prefer explicit code over unnecessary abstraction;
* avoid duplicating logic when an existing reusable implementation already exists;
* preserve public interfaces unless changing them is explicitly required;
* update tests when behavior changes;
* update configuration examples when configuration changes;
* update documentation when developer-facing behavior changes;
* avoid adding new dependencies unless they provide a clear benefit;
* keep changes scoped to the requested task;
* follow the current `plan.md` when one exists.

Do not silently change:

* environment variables;
* API contracts;
* ports;
* volumes;
* paths;
* startup order;
* persistence behavior;
* database schemas;
* authentication behavior;
* deployment assumptions.

If such a change is required:

* document it explicitly in `changes.md`;
* update `plan.md` if a plan exists and the change affects the planned approach.

---

## Validation

Before considering a logical change or plan step complete:

1. Review the complete relevant diff.

2. Run the relevant tests.

3. Run linting and formatting tools when configured.

4. Validate configuration files when relevant.

5. Check that no unrelated files were modified.

6. Update:

   `docs/changes/<YYYY-MM-DD>_<branch-name>/changes.md`

7. Ensure the change-log commit message matches the intended Git commit message.

8. If a plan exists, ensure the commit message also matches the corresponding `plan.md` step.

9. Check `git status` again before reporting completion.

Examples of validation may include:

```bash
pytest
ruff check .
ruff format --check .
docker compose config
```

Only run commands that are relevant to the modified component.

Do not claim a test or validation succeeded unless it was actually executed successfully.

If a validation command is not available or cannot be run, say so explicitly.

---

## Existing failures

If tests, linting, builds, or other validation already fail for reasons unrelated to the requested change:

* do not modify unrelated code solely to make the whole repository pass;
* clearly distinguish pre-existing failures from failures caused by the current change;
* document relevant unresolved validation issues in the final report;
* avoid hiding or ignoring failures that may affect confidence in the change.

---

## Docker and infrastructure changes

When modifying Dockerfiles, Docker Compose, volumes, networks, environment variables, ports, startup order, health checks, users, groups, file permissions, or persistent storage:

* inspect dependent services before changing configuration;
* preserve existing runtime behavior unless the requested change requires otherwise;
* check whether `.env.example` or documentation must also be updated;
* run `docker compose config` when applicable;
* preserve non-root execution when already used;
* consider bind-mount permissions and shared-volume ownership;
* document important operational consequences in the change log;
* avoid machine-specific assumptions where a portable configuration is possible.

---

## API changes

When modifying an API:

* preserve existing endpoint contracts unless a contract change is explicitly required;
* update request or response schemas when necessary;
* update tests for changed behavior;
* document breaking changes explicitly;
* consider backward compatibility;
* preserve meaningful HTTP status codes;
* preserve explicit and useful error handling;
* avoid silently changing authentication or authorization behavior.

---

## Database and persistent state changes

When modifying database schemas, persistent state, runtime directories, volumes, state files, or migration logic:

* avoid destructive changes unless explicitly requested;
* preserve existing data when possible;
* document migrations or compatibility concerns;
* clearly identify any change that requires resetting local or production state;
* consider upgrade and rollback implications when relevant.

---

## Security

Never commit:

* passwords;
* API keys;
* access tokens;
* JWT secrets;
* private keys;
* production credentials;
* sensitive `.env` values.

Use environment variables or the project's existing secret-management mechanism.

When adding a new environment variable, update `.env.example` with a safe placeholder when appropriate.

Do not expose secrets in:

* logs;
* test output;
* documentation;
* plans;
* change logs.

---

## Scope control

Do not modify unrelated files simply because improvements are possible.

If you notice an unrelated issue:

* leave it unchanged;
* mention it separately if it is important;
* do not include it in the current logical change unless explicitly requested.

Avoid opportunistic refactoring.

Avoid cleanup that is not necessary for the requested task.

Keep each logical change easy to review.

---

## End-of-task report

At the end of every task, provide a concise report containing:

* files modified;
* main changes made;
* tests or validation executed;
* whether validation passed or failed;
* change-log file updated;
* plan file updated, when applicable;
* intended or proposed commit message;
* unresolved issues or assumptions, if any.

Example:

```text
Modified:
- src/train_api/main.py
- src/train_api/state.py
- docs/changes/2026-09-11_change-mlflow-port/changes.md
- docs/changes/2026-09-11_change-mlflow-port/plan.md

Changes:
- Added recovery of interrupted training runs.
- Running states left after a crash are marked as failed during startup.

Validation:
- pytest tests/train_api: passed
- ruff check: passed

Change log:
- docs/changes/2026-09-11_change-mlflow-port/changes.md updated

Plan:
- Step 2 completed

Commit proposed:
fix(train-api): recover interrupted training state
```

Do not claim that a commit was created unless it was actually created.

By default, report the proposed commit message and let the user create the commit.

---

## Git safety

Do not perform destructive Git operations unless explicitly requested.

This includes:

```text
git reset --hard
git clean -fd
git push --force
git rebase
git branch -D
```

Do not discard existing uncommitted user changes.

Before operations that may interact with existing modifications, inspect:

```bash
git status
```

Preserve user work that is unrelated to the current task.

Do not rewrite Git history unless explicitly requested.

Do not automatically create or push commits unless explicitly requested.

---

## Core principle

For a normal significant change:

```text
understand
→ inspect branch and working tree
→ modify
→ validate
→ review diff
→ document in docs/changes/<YYYY-MM-DD>_<branch-name>/changes.md
→ propose commit message
→ user creates commit
```

When the user asks for a plan:

```text
understand
→ inspect repository
→ create docs/changes/<YYYY-MM-DD>_<branch-name>/plan.md
→ define logical implementation steps
→ execute one step
→ validate
→ review diff
→ update changes.md
→ propose the step commit message in chat
→ user creates commit
→ continue with the next step
```

The goal is to keep every modification focused, traceable, documented, reproducible, and easy for another developer to understand later.
