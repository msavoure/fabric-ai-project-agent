# fabric-ai-project-agent

A **governance-first** Microsoft Fabric data engineering repository, operated
jointly by a human Data Engineer and an AI Data Engineering Agent.

The agent does not replace architectural or business decisions. It designs,
profiles, documents and generates code **against declared sources of truth**,
and it stops and asks whenever a decision is missing.

---

## 1. Purpose

Deliver Microsoft Fabric data pipelines where **every technical decision is
traceable to a repository source** — a project standard, a data contract, a
business rule, or an explicitly recorded human decision.

Nothing is invented. Anything the agent cannot derive from a source of truth is
raised as `HUMAN VALIDATION REQUIRED` and, once answered, persisted in a
decision log before any code is generated.

---

## 2. MVP scope

| Dimension | Scope |
|---|---|
| Use case | `distribution` |
| Dataset | `customers` |
| Source | `customers.csv` — synthetic data, 508 rows, 8 columns |
| Layers | **Bronze** designed and generated; **Silver** designed, not generated |
| Target | Microsoft Fabric Lakehouse, Delta tables, medallion architecture |
| Load mode | Full snapshot / full refresh, no historization (decision HV-05) |

Out of MVP scope: orchestration, scheduling, environment separation, persistent
Data Quality storage, Gold layer.

---

## 3. Governance hierarchy

Defined in [agent/system_prompt.md](agent/system_prompt.md). Sources of truth,
in strict priority order:

| # | Source | Location |
|---|---|---|
| 1 | **Project standards** | [standards/project_standards.yaml](standards/project_standards.yaml) |
| 2 | **Data contract** | `use_cases/<use_case>/contracts/` |
| 3 | **Business rules** | `use_cases/<use_case>/business_rules/` |
| 4 | **Source data profiling** | `use_cases/<use_case>/data/` |
| 5 | **Agent recommendations** | proposals only — never override levels 1–4 |

A lower-priority source may **never** override a higher-priority one through an
assumption.

### Reasoning labels

Every agent output distinguishes: `OBSERVATION`, `CONTRACT`, `BUSINESS RULE`,
`STANDARD`, `PROPOSAL`, `HUMAN VALIDATION REQUIRED`.

### Human approval triggers

Declared in `standards/project_standards.yaml` (`human_approval_required`):
undocumented business rule, ambiguous transformation, architecture change,
create / modify / delete a Fabric item, deploy.

---

## 4. Directory structure

```
fabric-ai-project-agent/
├─ README.md                  This document
├─ .gitignore                 Exclusion policy
├─ .gitattributes             Line ending and diff policy
│
├─ agent/
│  └─ system_prompt.md        Agent role, sources of truth, safety rules
│
├─ standards/
│  └─ project_standards.yaml  Priority 1 - architecture, naming, DQ, approvals
│
├─ use_cases/
│  └─ distribution/
│     ├─ contracts/           Priority 2 - data contracts
│     ├─ business_rules/      Priority 3 - business rules
│     ├─ data/                Priority 4 - source data (synthetic)
│     └─ decisions/           Human decision log (HV / R / B series)
│
└─ generated/                 Agent output, human-reviewed
   ├─ customers_data_quality.md
   └─ nb_bronze_customers.ipynb   Superseded design artifact (frozen)
```

The `fabric/` directory holds the Fabric-native artifacts synchronised with the
development workspace — see section 6.

---

## 5. Responsibilities

| Artifact | Authored by | Reviewed by | Rule |
|---|---|---|---|
| `agent/system_prompt.md` | Human | Human | Defines how the agent may act |
| `standards/` | Human | Human | The agent must never modify it |
| `use_cases/*/contracts/` | Human | Human | The agent must never modify it |
| `use_cases/*/business_rules/` | Human | Human | The agent must never invent a rule |
| `use_cases/*/data/` | Source system | Human | Profiled, never altered |
| `use_cases/*/decisions/` | Agent, from **human answers** | Human | Records approved decisions and their consequences |
| `generated/` | **Agent** | Human | Regenerable; must always trace back to levels 1–4. `nb_bronze_customers.ipynb` is frozen — superseded by `fabric/` |
| `fabric/**/notebook-content.py` | **Agent / human** | Human | Executable source of truth for notebook code |
| `fabric/**/.platform`, `*.metadata.json`, `alm.settings.json` | **Microsoft Fabric** | — | Fabric-owned metadata; never hand-edited |

**The agent may:** profile source data, compare it to the contract, design
Bronze and Silver, define Data Quality controls, generate PySpark, document
assumptions, persist decisions that a human has explicitly approved.

**The agent may not:** invent a business rule, silently correct ambiguous data,
modify a contract or a standard, delete data, create or modify a Fabric item,
or deploy — without explicit human approval.

---

## 6. Microsoft Fabric Git integration

**Connected.** The development workspace `ws_fabric_ai_project_agent_dev` is
synchronised with branch `dev` and with one sub-directory only, which isolates
Fabric-managed content from human- and agent-authored content:

```
fabric/
└─ ws_fabric_ai_project_agent_dev/        <- directory connected to the workspace
   ├─ lkh_bronze.Lakehouse/
   │  ├─ .platform                        <- Fabric-owned
   │  ├─ alm.settings.json                <- Fabric-owned
   │  ├─ lakehouse.metadata.json          <- Fabric-owned
   │  └─ shortcuts.metadata.json          <- Fabric-owned
   └─ nb_bronze_customers.Notebook/
      ├─ .platform                        <- Fabric-owned
      └─ notebook-content.py              <- executable source of truth
```

Rules:

- Fabric Git integration is connected to the **sub-directory only**, never to
  the repository root, so `standards/`, `use_cases/` and `generated/` stay
  outside Fabric's sync scope.
- `fabric/**/notebook-content.py` is the **single source of truth for
  executable notebook code**. It is edited in this repository, pushed to `dev`,
  then applied to the workspace with *Update from Git*.
- `generated/nb_bronze_customers.ipynb` is a **superseded design artifact**,
  kept unchanged for traceability. It is not regenerated and not deployed.
- Fabric-owned metadata — `.platform`, `alm.settings.json`, `*.metadata.json`,
  item folder names, logical identifiers, `# META` blocks — must never be
  hand-edited.
- *Update from Git* overwrites the workspace item and is a `modify_fabric_item`
  approval trigger. Pushing to `dev` does not authorise it.

See [fabric/README.md](fabric/README.md) for the editing rules that apply to
`notebook-content.py`.

---

## 7. Data policy

`use_cases/distribution/data/customers.csv` is **synthetic data**, approved for
versioning by the human Data Engineer on 2026-10-09.

Real customer data, personal data and credentials must never be committed. The
`.gitignore` excludes environment files, key material and local settings; it is
not a substitute for review.

---

## 8. Current status

| Item | Status |
|---|---|
| Project standards | `standard_version: 0.2` |
| Data contract — customers | `contract_version: 0.1`, frozen (decision HV-06) |
| Business rules — customers | BR-CUSTOMER-001 to 008 |
| Decision log — customers | HV-01…HV-06, R-01…R-03, B-01…B-06, B-07 — all resolved |
| Data Quality specification | DQ-01…DQ-26 (DQ-17 withdrawn) |
| `nb_bronze_customers` | Source of truth: `fabric/ws_fabric_ai_project_agent_dev/nb_bronze_customers.Notebook/notebook-content.py` — B-06 parity restored, execution in Fabric **not authorised** |
| `generated/nb_bronze_customers.ipynb` | **Superseded** design artifact, frozen (decision B-07) |
| `nb_silver_customers` | Not designed, not authorised |
| Fabric Git integration | **Connected** — `ws_fabric_ai_project_agent_dev` ↔ `dev` ↔ `fabric/ws_fabric_ai_project_agent_dev/` |
| Known follow-up | Existence of the `customers` schema in `lkh_bronze` not yet verified; *Update from Git* not yet run |

Bronze target table: `customers.bronze_customers` — schema-enabled Lakehouse
`lkh_bronze`, workspace `ws_fabric_ai_project_agent_dev` (decision B-06).

See [use_cases/distribution/decisions/customers_decisions.md](use_cases/distribution/decisions/customers_decisions.md)
for the full decision history.
