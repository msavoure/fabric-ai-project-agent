# fabric/ - Microsoft Fabric native Git artifacts

This directory contains **Fabric-native Git artifacts**: the serialised
representation of Microsoft Fabric items, written by Microsoft Fabric itself
through Git integration.

It holds two different kinds of content, and the distinction is strict:

- **Fabric-owned metadata** - `.platform`, `alm.settings.json`,
  `*.metadata.json`, item folder names. Written and consumed by Fabric. Never
  hand-edited.
- **Notebook payloads** - `notebook-content.py`. This is the **executable
  source of truth** for notebook code and it **is** edited in this repository.

`README.md` and the `.gitkeep` placeholders are the only other hand-authored
files here.

---

## Workspace mapping

| Workspace | Directory | Branch | Status |
|---|---|---|---|
| `ws_fabric_ai_project_agent_dev` | `fabric/ws_fabric_ai_project_agent_dev/` | **`dev`** | **Connected** |

The development workspace is connected to the **`dev`** branch and to that
sub-directory only. Fabric Git integration must never be connected to the
repository root, so that `agent/`, `standards/`, `use_cases/` and
`generated/` stay outside Fabric's synchronisation scope.

Each Fabric item appears as a folder named `<ItemName>.<ItemType>` — for
example `nb_bronze_customers.Notebook/` — containing a `.platform`
descriptor and the item payload. A notebook is serialised as
`notebook-content.py`, not as `.ipynb`.

---

## Editing rules

**Notebook business logic is edited in VS Code.** The PySpark logic is plain
text and is reviewable and diffable like any other source file. It is the
authoritative copy of the executable code.

**Fabric-managed metadata must remain consistent.** Do not rename item
folders, do not edit `.platform`, do not alter the logical identifiers or
the Fabric magic headers. Breaking that metadata breaks the binding
between the Git item and the workspace item, and the next synchronisation
will fail or create a duplicate item.

When editing `notebook-content.py`, the following must be preserved byte for
byte:

- the `# Fabric notebook source` first line;
- every `# META ...` line and every `# METADATA ********************` block;
- the `# MARKDOWN ********************` and `# CELL ********************`
  separators, and their order;
- the `# ` prefix on every markdown line, including blank markdown lines,
  which are a `#` followed by a single space;
- LF line endings and the absence of a byte order mark.

### Source of truth

| Artifact | Role | Author |
|---|---|---|
| `fabric/.../notebook-content.py` | **Executable source of truth** for notebook code | Agent / human, reviewed; pushed to `dev`, then applied with *Update from Git* |
| `fabric/.../.platform`, `*.metadata.json`, `alm.settings.json` | Fabric-owned item metadata | Microsoft Fabric only |
| `generated/*.ipynb` | **Superseded design artifact**, kept unchanged for traceability | Agent, human-reviewed |

The flow is `fabric/` -> push to `dev` -> *Update from Git* in the workspace.
`generated/nb_bronze_customers.ipynb` is frozen: it documents the approved
design, it is no longer the deployment path, and it must not be regenerated
to chase changes made here.

A change made directly in the Fabric UI arrives through a Fabric commit and is
reconciled in `fabric/`, never by a textual merge of the two notebooks.

### Line endings

Fabric commits some item metadata with CRLF through its Git integration API,
which bypasses local normalisation. `.gitattributes` therefore exempts
`.platform`, `alm.settings.json` and `*.metadata.json` from EOL conversion
(`-text`) and keeps `notebook-content.py` on LF.

---

## Human approval

**Human approval is required before deploying or executing any change in
Microsoft Fabric.**

This repeats the triggers declared in `standards/project_standards.yaml`
(`human_approval_required`): `create_fabric_item`, `modify_fabric_item`,
`delete_fabric_item`, `deploy`, and `architecture_change`.

Committing to `dev` does **not** authorise execution. Updating the
workspace from Git, running a notebook, or writing to a Lakehouse table
each require an explicit human decision, recorded in the relevant decision
log under `use_cases/<use_case>/decisions/`.

In particular, *Update from Git* overwrites the workspace item and is a
`modify_fabric_item` trigger. Pushing a corrected `notebook-content.py` to
`dev` is a repository operation; applying it to the workspace is not.
