# fabric/ - Microsoft Fabric native Git artifacts

This directory contains **Fabric-native Git artifacts**: the serialised
representation of Microsoft Fabric items, written by Fabric itself through
Git integration.

It is not a source directory. Nothing here is hand-authored except this
README and the `.gitkeep` placeholders.

---

## Workspace mapping

| Workspace | Directory | Branch |
|---|---|---|
| `ws_fabric_ai_project_agent_dev` | `fabric/ws_fabric_ai_project_agent_dev/` | **`dev`** |

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

**Notebook business logic may be edited in VS Code.** The PySpark logic is
plain text and is reviewable and diffable like any other source file.

**Fabric-managed metadata must remain consistent.** Do not rename item
folders, do not edit `.platform`, do not alter the logical identifiers or
the Fabric magic headers. Breaking that metadata breaks the binding
between the Git item and the workspace item, and the next synchronisation
will fail or create a duplicate item.

### Source of truth

| Directory | Role | Author |
|---|---|---|
| `generated/` | **Authoring** source of truth (`.ipynb`) | Agent, human-reviewed |
| `fabric/` | **Deployment** representation (`notebook-content.py`) | Microsoft Fabric |

The flow is one-way: `generated/` -> import into the workspace -> Fabric
commits into `fabric/`. A change made directly in the Fabric UI must be
back-propagated into `generated/`, never merged by hand.

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
