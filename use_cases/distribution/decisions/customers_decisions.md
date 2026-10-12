# Customers - Decision log

**Use case:** Distribution / Customers
**Scope:** MVP
**Last updated:** 2026-10-12

This file records the decisions taken by the human Data Engineer during
the Customers analysis, and the residual open points.

It is a traceability artifact. It is **not** a source of truth that
overrides project standards, the Data Contract or the business rules.

Priority order defined in `agent/system_prompt.md` remains:

1. Project standards
2. Data contract
3. Business rules
4. Source data profiling
5. Agent recommendations

---

## Decision register

| ID | Date | Decision | Persisted in | Status |
|---|---|---|---|---|
| HV-01 | 2026-10-07 | Conditional survivorship on strict identity | BR-CUSTOMER-001 | RESOLVED |
| HV-02 | 2026-10-07 | No automatic `Rhone Alpes` normalization | BR-CUSTOMER-004 | RESOLVED |
| HV-03 | 2026-10-07 | City casing: report only, no normalization | BR-CUSTOMER-008 | RESOLVED |
| HV-04 | 2026-10-07 | Data Quality failures kept in Silver | `standards/project_standards.yaml` | RESOLVED - applied in `standard_version: "0.2"` |
| HV-05 | 2026-10-07 | Full snapshot, full refresh, no historization | This file - see below | RESOLVED - MVP, Customers only |
| HV-06 | 2026-10-07 | Data Contract frozen, gaps still reported | No change | ACCEPTED - deferred |
| HV-07 | 2026-10-12 | DQ-16 batch validation - 5 `Rhone Alpes` records accepted as-is | This file - see below | APPROVED - batch `c5082b63-22b4-4c95-ad41-78c8cfb86507` only |
| R-01 | 2026-10-07 | All `Rhone Alpes` occurrences require human validation | BR-CUSTOMER-004 | RESOLVED |
| R-02 | 2026-10-07 | Two NULL values are identical for duplicate comparison | BR-CUSTOMER-001 | RESOLVED |
| R-03 | 2026-10-07 | `source_semantics` scoped to Customers, not global | This file | RESOLVED - MVP |
| R-04 | 2026-10-12 | `lkh_silver` admitted as the resolution key of the target-Lakehouse identity guard; final comparison still made on Fabric identifiers | This file - see below | RESOLVED - amends B-09 decision 5, closes S-06, MVP DEV only |
| B-01 | 2026-10-07 | `_batch_id` generated as a UUID once per notebook run | This file - see below | APPROVED |
| B-02 | 2026-10-07 | Single source file `Files/customers.csv` in the attached Lakehouse | This file - see below | APPROVED - MVP |
| B-03 | 2026-10-07 | Data Quality reporting is notebook-output only | This file - see below | APPROVED - MVP, persistence deferred |
| B-04 | 2026-10-07 | Abort before write on DQ-01 failure only | This file - see below | APPROVED |
| B-05 | 2026-10-07 | `_ingestion_timestamp` in UTC, one value per batch | This file - see below | APPROVED |
| B-06 | 2026-10-09 | Schema-enabled Lakehouse `lkh_bronze`, target schema `customers` -> `customers.bronze_customers` | This file - see below | APPROVED |
| B-07 | 2026-10-09 | `fabric/.../notebook-content.py` becomes the single source of truth for executable notebook code; `generated/nb_bronze_customers.ipynb` is frozen as a superseded design artifact | This file - see below | APPROVED - architecture_change |
| B-08 | 2026-10-12 | Dedicated schema-enabled Lakehouse `lkh_silver`, target schema `customers` -> `customers.silver_customers` | This file - see below | APPROVED - architecture_change, placement only |
| B-09 | 2026-10-12 | Silver technical columns, abort preconditions, Data Quality failure behaviour and target-Lakehouse identity guard | This file - see below | APPROVED - Silver implementation decision |

The `B-01` to `B-06` series records **Bronze implementation decisions** for
`nb_bronze_customers`. They are implementation-level choices: they do not
create, alter or override any business rule, and they are scoped to the
Customers MVP unless explicitly promoted later.

B-07 and B-08 are **architecture decisions**, approved under STANDARD
`human_approval_required: architecture_change`. B-07 governs where notebook
code lives and applies to every notebook in the repository. B-08 governs
where the Silver table lives and is scoped to the Customers MVP.

B-09 is the first **Silver implementation decision**. Like the Bronze series
it creates no business rule and is scoped to the Customers MVP. It is **not**
a transposition of B-04, which remains scoped to the Bronze layer.

HV-07 is the first **run-time** entry in this register. HV-01 to HV-06 are
design-time decisions that create or clarify a rule; HV-07 creates none. It
records the batch-level validation that DQ-16 mandates at every execution,
and its authority expires with the batch it names.

---

## HV-01 - Duplicate `customer_id` survivorship

**Decision.** After the trim transformations authorised by BR-CUSTOMER-002:

- records sharing the same `customer_id` that are strictly identical
  across all business attributes are reduced to a single record;
- records sharing the same `customer_id` with at least one conflicting
  business value are preserved, reported, and submitted to human
  validation. No survivor is selected automatically.

**Persisted in:** BR-CUSTOMER-001.

**R-02 - NULL comparison semantics.** Two missing values are considered
identical during the strict-identity comparison. Without this convention,
standard SQL semantics (`NULL != NULL`) would classify two records with a
missing `city` as conflicting.

**Impact on the current source file.** The 8 duplicated keys are strictly
identical after trim - the only raw difference is a trailing space in
`customer_name`:

`C0078`, `C0110`, `C0180`, `C0211`, `C0322`, `C0370`, `C0384`, `C0471`

Branch 1 applies. Expected result: 508 source rows to 500 Silver rows,
`quality.business_key.unique` satisfied.

---

## HV-02 / R-01 - Region normalization

**Decision.** The `Rhone Alpes` to `Auvergne-Rhône-Alpes` normalization
is **never applied automatically** for this MVP.

Every occurrence is preserved as-is, reported as a Data Quality issue,
and submitted to human validation.

No geographic validation is performed. No geographic reference dataset
is introduced.

**Rationale.** The repository contains no reference dataset of valid
(city, postal_code, region) combinations. Contract gap G-03 (`region`
without `allowed_values`) is frozen by HV-06. Evaluating a geographic
inconsistency criterion would require the agent to invent a business
rule, which is forbidden by
`standards/project_standards.yaml` - `ai_agent.forbidden_actions.invent_business_rule`.

**Persisted in:** BR-CUSTOMER-004.

**Consequence to accept.** BR-CUSTOMER-004 now carries a mapping that is
never applied. The rule is retained as documentation of the known
equivalence and as the anchor for the Data Quality control.

**Impact on the current source file.** 5 records preserved and reported:

| customer_id | city | postal_code | region (source) |
|---|---|---|---|
| C0053 | Vannes | 56000 | Rhone Alpes |
| C0161 | Vannes | 56000 | Rhone Alpes |
| C0189 | Bordeaux | 33000 | Rhone Alpes |
| C0375 | Lille | 59000 | Rhone Alpes |
| C0413 | Angers | 49000 | Rhone Alpes |

---

## HV-03 - City casing

**Decision.** No automatic casing normalization on `city`. Casing
inconsistencies are reported only.

**Persisted in:** BR-CUSTOMER-008.

**Impact on the current source file.** 13 occurrences in full uppercase,
producing duplicate representations of the same city:

`BORDEAUX` (C0001), `CLERMONT-FERRAND` (C0040), `LYON` (C0047, C0116),
`VANNES` (C0049), `NICE` (C0068, C0110 x2), `ANGERS` (C0245),
`TOULOUSE` (C0266), `PARIS` (C0304), `AMIENS` (C0336), `LIMOGES` (C0361)

---

## HV-04 - Data Quality failure routing

**Decision.** For this MVP, records failing a Data Quality control
remain in `silver_customers` and are reported. No quarantine table, no
rejection - unless an explicit business rule requires otherwise.

**Destination:** `standards/project_standards.yaml`, `data_quality.on_failure`.

**Status: RESOLVED.** The change was applied manually by the human Data
Engineer on 2026-10-07. `standards/project_standards.yaml` is now at
`standard_version: "0.2"` and carries:

```yaml
data_quality:
  on_failure:
    action: report
    record_handling: keep_in_target
    quarantine: false
    reject: false
```

The agent did not modify the standards
(`ai_agent.forbidden_actions.change_project_standard`).

Controls DQ-06, DQ-11 and DQ-24 now have a defined routing policy at
standards level.

---

## HV-05 / R-03 - Load strategy (Customers only)

**Decision.** The implementation strategy below is **specific to the
Customers use case** for this MVP. It is deliberately **not** promoted to
a global rule in `standards/project_standards.yaml`.

| Parameter | Value |
|---|---|
| `source_semantics` | `full_snapshot` |
| `load_mode` | `full_refresh` |
| `incremental_load` | `false` |
| `historization` | `none` |

**Reading.**

- `use_cases/distribution/data/customers.csv` is considered a complete
  image of the Customers population at each delivery.
- `bronze_customers` and `silver_customers` are fully rebuilt at each run.
- No MERGE logic, no incremental loading, no SCD historization.
- `silver_customers` is a current-state table carrying no history.

**Rationale for not making it global.** Whether a source is a snapshot or
a delta extract is a property of the dataset. Its natural home is the
`source` section of the Data Contract, which HV-06 freezes. Promoting
`full_snapshot` to a platform-wide default would impose it on future
datasets that may be delivered as delta extracts.

**To be revisited when HV-06 is lifted:** move `source_semantics` into
`use_cases/distribution/contracts/customers.yaml`.

---

## HV-06 - Data Contract completeness

**Decision.** The Data Contract is not modified for now. The identified
gaps continue to be reported by the Data Quality controls and must not
block the MVP.

**Gaps accepted and deferred:**

| ID | Gap | Reported by |
|---|---|---|
| G-01 | No resolution strategy on uniqueness violation | Resolved by HV-01 at business rule level |
| G-02 | `country` - no `allowed_values` declared | DQ-10 |
| G-03 | `region` - no reference list | DQ-16 |
| G-04 | `postal_code` - no pattern, no city/region relationship | DQ-14 for typing integrity. The city/region relationship is **not controlled** - DQ-17 withdrawn by HV-02 / R-01 |
| G-05 | `created_date` - no validity window | Not controlled |
| G-06 | Routing of DQ-failing rows undefined | Resolved by HV-04 at standards level |
| - | Trim scope excludes `customer_id` and `postal_code` | DQ-21 |

---

## HV-07 - DQ-16 batch validation - Bronze batch c5082b63

**Date:** 2026-10-12
**Type:** Run-time human validation mandated by DQ-16 - not a new rule
**Scope:** Bronze batch `c5082b63-22b4-4c95-ad41-78c8cfb86507` only

**Context.** `nb_bronze_customers` was executed and wrote to
`customers.bronze_customers`. Reported results: 508 rows ingested, 500
distinct `customer_id`, 8 duplicate keys preserved, 0 rows deleted. 16 of
the 26 controls are evaluable at Bronze level; 12 passed and 4 failed by
design: DQ-03 (BLOCKING, 16 rows), DQ-05 (MEDIUM, 18 rows), DQ-09 (MEDIUM,
10 rows), DQ-16 (HIGH, 5 rows). Every count matches the profiling baseline
recorded in `generated/customers_data_quality.md` exactly.

The repository revision actually deployed to the Fabric workspace at the
time of the run is **not verified** from this repository. The only
confirmed fact is that the run targeted `customers.bronze_customers`, which
is the table designated by B-06.

DQ-16 requires a human validation **at each run** - see
`generated/customers_data_quality.md`, section *Run-time human validation -
standing, by design*.

**Decision.** The human Data Engineer **approves** the batch on DQ-16. The
5 records carrying `region = "Rhone Alpes"` are accepted **as-is**:

| customer_id | city | postal_code | region (source, preserved) |
|---|---|---|---|
| C0053 | Vannes | 56000 | Rhone Alpes |
| C0161 | Vannes | 56000 | Rhone Alpes |
| C0189 | Bordeaux | 33000 | Rhone Alpes |
| C0375 | Lille | 59000 | Rhone Alpes |
| C0413 | Angers | 49000 | Rhone Alpes |

**Explicitly not authorised by this validation.**

- No automatic normalization of `Rhone Alpes` to `Auvergne-Rhône-Alpes`.
- No manual correction of the 5 `region` values.
- No geographic deduction from `city` or `postal_code`, and no introduction
  of a geographic reference dataset.
- No execution of any Silver notebook.

**What this validation does authorise.** The **preparation** of the Silver
layer only: specification and code authoring for `nb_silver_customers`.
Execution in Fabric remains unauthorised and requires a separate human
approval (STANDARD `human_approval_required`: `modify_fabric_item`,
`deploy`).

**Consequences.**

- **No rule is created, altered or lifted.** BR-CUSTOMER-004, HV-02 and
  R-01 remain in force unchanged. DQ-16 keeps severity HIGH and keeps
  firing on every future batch.
- **The validation does not carry forward.** A new `_batch_id` requires a
  new validation. This entry authorises nothing beyond
  `c5082b63-22b4-4c95-ad41-78c8cfb86507`.
- **This entry is the only persistent trace of the validation.** B-03
  limits Data Quality reporting to ephemeral notebook output. Until
  persistent DQ storage is implemented, this register is the audit record.
- Contract gap G-03 (`region` without a reference list) stays accepted and
  deferred by HV-06. This validation does not close it.
- DQ-26 did not fire on this batch (0 conflicting key), so no survivorship
  validation was required.

---

## B-01 to B-06 - Bronze implementation decisions

**Scope.** `nb_bronze_customers` -> `customers.bronze_customers`, Customers MVP.
B-01 to B-05 were validated by the human Data Engineer on 2026-10-07 in
response to the Bronze implementation plan; B-06 was validated on
2026-10-09 as an architecture decision on the target Lakehouse.

These decisions complete the implementation parameters that were **not
defined** anywhere in the repository. They sit at priority level 5 of the
`agent/system_prompt.md` hierarchy and must never override the project
standards, the Data Contract or the business rules.

### B-01 - `_batch_id` generation

**Decision.** `_batch_id` is generated as a **UUID**, produced **once at
notebook execution start**. The same value is applied to every row of the
ingestion run.

**Consequences.**

- Type remains `string` as declared by STANDARD `bronze.technical_columns`.
- The value must be materialised as a constant before the write, never as
  a lazily re-evaluated expression, otherwise rows of the same batch could
  receive different identifiers.
- DQ-25 (full refresh integrity) expects exactly **one distinct
  `_batch_id`** in `bronze_customers` after a successful run.
- A UUID is not sortable and carries no chronology. Run ordering must be
  derived from `_ingestion_timestamp` (B-05), not from `_batch_id`.
- A re-run produces a **new** `_batch_id`; the identifier is not stable
  across retries of the same logical load.

### B-02 - Source location

**Decision.** The source is a **single file**, `Files/customers.csv`,
located in the Lakehouse attached to the Fabric notebook. No wildcard, no
folder ingestion, no multi-file behaviour for this MVP.

**Consequences.**

- Resolves the gap left by CONTRACT `source.file: customers.csv`, which
  declares a bare file name with no path.
- `_source_file` is therefore **constant across the batch**.
- A missing or unreadable file is a technical failure and must abort the
  run (see B-04, category (b)).
- The Lakehouse is **attached to the notebook**: no absolute workspace or
  lakehouse name is hardcoded in the implementation.

### B-03 - Data Quality reporting destination

**Decision.** For this MVP, Data Quality reporting is **notebook output
only**. No persistent Data Quality table is created. Persistent DQ
reporting is **explicitly deferred**.

**Required structure of each emitted DQ result:**

| Field | Content |
|---|---|
| `batch_id` | The UUID of B-01 |
| `control_id` | `DQ-01` ... `DQ-25` |
| `severity` | INFORMATIONAL / LOW / MEDIUM / HIGH / BLOCKING |
| `status` | PASS / FAIL |
| `affected_row_count` | Number of rows concerned by the control |
| `message` | Human-readable detail of the finding |

**Consequences.**

- STANDARD `data_quality.on_failure.action: report` is satisfied at MVP
  level by this structured notebook output.
- The results are **ephemeral**: they disappear with the notebook session.
  No cross-batch trend, no historical DQ analysis is possible yet.
- Creating a DQ table would be a Fabric item creation and requires a
  separate human approval (STANDARD `human_approval_required:
  create_fabric_item`).

**Deferred:** persistent Data Quality storage, its schema, its retention
and its link to `_batch_id`.

### B-04 - Notebook behaviour on a Data Quality failure

**Decision.** Two distinct behaviours:

| Condition | Behaviour |
|---|---|
| **DQ-01 schema conformity fails** | Report the failure and **abort before writing** `bronze_customers` |
| **Any other Bronze DQ control fails** | Report the failure, **keep the affected records**, **continue** the Bronze write |

**Consequences.**

- DQ-01 is the only pre-write gate. Aborting before the write destroys
  nothing and leaves the previous content of `bronze_customers` intact,
  which is compatible with STANDARD `forbidden_actions.delete_data`.
- A schema divergence invalidates every downstream control, so writing a
  structurally wrong table is worse than not writing at all.
- DQ-02 and DQ-03 are BLOCKING in the specification but **do not block the
  Bronze write**: their records are kept, as required by STANDARD
  `record_handling: keep_in_target`, `reject: false`, `quarantine: false`.
  "BLOCKING" qualifies the severity of the finding, not the run.
- No row is ever rejected, quarantined or corrected at Bronze level.

### B-05 - `_ingestion_timestamp` semantics

**Decision.** `_ingestion_timestamp` is expressed in **UTC**. A single
timestamp is captured at notebook execution start and applied to every row
of the batch.

**Consequences.**

- Type remains `timestamp` as declared by STANDARD `bronze.technical_columns`.
- The value must not depend on the Spark session timezone default.
- Like `_batch_id`, it must be materialised as a constant, never as a
  per-row `current_timestamp()` evaluation.
- `_ingestion_timestamp` is the chronological ordering key across runs,
  compensating for the non-sortable UUID of B-01.

### B-06 - Target schema in the Bronze Lakehouse

**Decision.** The Microsoft Fabric Lakehouse `lkh_bronze`, in workspace
`ws_fabric_ai_project_agent_dev`, is **schema-enabled**. The human Data
Engineer selected the **existing** schema `customers` as the target schema
for the Customers Bronze dataset. The Bronze table is therefore addressed
as `customers.bronze_customers`.

This is an architecture decision (STANDARD `human_approval_required:
architecture_change`) and it was given by the human Data Engineer.

**Consequences.**

- The **table name is unchanged**: it remains `bronze_customers`. The
  schema is a **physical placement qualifier**, not a renaming. STANDARD
  `naming.tables.bronze: "bronze_{entity}"` and CONTRACT
  `target.bronze_table: bronze_customers` both remain satisfied; the Data
  Contract is **not** modified.
- `nb_bronze_customers` addresses the table through the single
  `TARGET_TABLE` configuration variable, now set to
  `"customers.bronze_customers"`. No other code reference is affected.
- No Bronze transformation, no technical column and no Data Quality
  control changes. DQ-22, DQ-23 and DQ-25 read back the same table through
  `TARGET_TABLE`.
- The schema `customers` is **pre-existing**: the notebook must not create
  it. Creating a schema would be a Fabric item creation and would require
  a separate human approval.
- `nb_silver_customers`, when it is designed, must state its own target
  schema. B-06 is scoped to the Bronze layer only and is **not**
  automatically transposed to Silver.

---

## B-07 - Fabric-native notebook as the single source of truth

**Date:** 2026-10-09
**Type:** Architecture decision - STANDARD `human_approval_required:
architecture_change`
**Scope:** Repository-wide, all notebooks

**Context.** The development workspace `ws_fabric_ai_project_agent_dev` is
connected to branch `dev` and to the directory
`fabric/ws_fabric_ai_project_agent_dev/`. Microsoft Fabric committed its two
items on 2026-10-09. The notebook had been imported into the workspace from a
revision predating B-06, so the Fabric-serialised copy targeted
`bronze_customers` instead of `customers.bronze_customers`.

Two copies of the same executable logic therefore existed: the authoring
notebook `generated/nb_bronze_customers.ipynb` and the Fabric payload
`fabric/ws_fabric_ai_project_agent_dev/nb_bronze_customers.Notebook/notebook-content.py`.

**Decision.** The human Data Engineer designated
`fabric/**/notebook-content.py` as the **single source of truth for
executable notebook code**. This reverses the one-way flow previously
documented in `README.md` section 6 and in `fabric/README.md`.

**Consequences.**

- Notebook code is edited in `fabric/**/notebook-content.py`, pushed to
  `dev`, then applied to the workspace with *Update from Git*. That
  operation overwrites the workspace item and remains a
  `modify_fabric_item` approval trigger; pushing to `dev` does not
  authorise it.
- `generated/nb_bronze_customers.ipynb` is **frozen as a superseded design
  artifact**. It is kept unchanged for traceability, it is not regenerated,
  and it must not be imported into a workspace. At the date of this
  decision it is cell-for-cell identical to the corrected Fabric payload.
- Fabric-owned metadata - `.platform`, `alm.settings.json`,
  `*.metadata.json`, item folder names, logical identifiers, `# META`
  blocks, cell separators - stays owned by Microsoft Fabric and must never
  be hand-edited. B-07 opens the notebook payload to editing, nothing else.
- `generated/customers_data_quality.md` is **not** affected: it is a
  specification, not executable code, and `generated/` remains the output
  directory for agent-authored documentation.
- **No business decision is altered.** B-06 remains the authority for the
  target table; B-07 only changes where the code implementing it lives.
  The Data Contract, the business rules and the project standards are
  unchanged.
- A change made directly in the Fabric UI arrives through a Fabric commit
  and is reconciled in `fabric/`, never by a textual merge of the two
  notebook representations.

---

## B-08 - Silver Lakehouse and target schema

**Date:** 2026-10-12
**Type:** Architecture decision - STANDARD `human_approval_required:
architecture_change`
**Scope:** `nb_silver_customers` -> `customers.silver_customers`, Customers MVP

**Context.** B-06 deliberately refused to transpose the Bronze placement to
Silver: *"`nb_silver_customers`, when it is designed, must state its own
target schema. B-06 is scoped to the Bronze layer only."* B-08 supplies that
statement, and nothing more.

### What is approved

The human Data Engineer approved the following **placement** decisions. They
are settled and require no further validation.

| # | Approved |
|---|---|
| 1 | A **dedicated Lakehouse `lkh_silver`**, schema-enabled, in workspace `ws_fabric_ai_project_agent_dev`, distinct from `lkh_bronze` |
| 2 | Target **schema `customers`** inside `lkh_silver` |
| 3 | Target **table `customers.silver_customers`** |
| 4 | **No change** to the Bronze target: `customers.bronze_customers` in `lkh_bronze` remains governed solely by B-06 |
| 5 | **No change** to any business rule, Data Contract clause or project standard |

### What is explicitly NOT approved by B-08

The items below were raised during the analysis of B-08. They are **technical
proposals, not validated behaviour, and not authorisations**. B-08 does not
settle any of them.

| # | Open point | Why it is not settled |
|---|---|---|
| 1 | `nb_silver_customers` configured with `lkh_silver` as default Lakehouse and `lkh_bronze` as a secondary attached Lakehouse | **Proposal to verify.** Not tested in this workspace. |
| 2 | Cross-Lakehouse read through a four-segment Spark SQL name `{workspace}.{lakehouse}.{schema}.{table}` | **Proposal to verify.** The format is documented for schema-enabled non-default Lakehouses, but it has **not been executed here**. |
| 3 | Whether the source Lakehouse must be attached for a four-segment name to resolve | **Not documented.** Must be tested. |
| 4 | The absolute ABFSS alternative | **The Microsoft documentation contradicts itself** on whether a schema segment belongs in the path for a schema-enabled Lakehouse. Must be tested before any use. An absolute path would also hardcode workspace and Lakehouse identifiers, which the principle stated by B-02 avoids. |
| 5 | Whether `saveAsTable("customers.silver_customers")` creates the schema when it is absent | **Not documented.** Must be tested. The B-06 precedent is that a notebook does **not** create a schema. |
| 6 | Creation of `lkh_silver` and of the schema `customers` inside it | Separate `create_fabric_item` approvals. **Not granted by B-08.** |
| 7 | Any execution of `nb_silver_customers` in Fabric | **Not authorised.** HV-07 authorised Silver *preparation* only. |

These open points are carried in the `S-xx` series below.

**Consequences.**

- The **table name is unchanged**: it remains `silver_customers`. The schema
  is a physical placement qualifier, not a renaming. STANDARD
  `naming.tables.silver: "silver_{entity}"` and CONTRACT
  `target.silver_table: silver_customers` both remain satisfied. The Data
  Contract is **not** modified and remains frozen by HV-06.
- The Bronze placement is untouched. B-06 remains the sole authority for
  `customers.bronze_customers`.
- Unlike the Bronze case, `lkh_silver` and its schema `customers` **do not
  pre-exist**. B-06 could rely on an existing schema; B-08 cannot. Their
  creation is a separate human approval and the notebook must not perform it.
- The default Lakehouse of `nb_silver_customers` would be the **target**, not
  the source. This **inverts the convention** of `nb_bronze_customers` and is
  the principal maintenance hazard of this design. A relative path or an
  unqualified table name would silently resolve against the Silver Lakehouse.
- The Silver write is an `overwrite` (HV-05). A misconfigured attachment
  would therefore overwrite the wrong table. A runtime guard asserting the
  identity of the default Lakehouse before writing is proposed, not decided.
- Lakehouse attachment lives in the `# META` block of the notebook payload,
  which is **Fabric-owned metadata**. Per B-07 it must be configured in the
  Fabric UI and arrive through a Fabric commit. It must never be hand-edited
  in `notebook-content.py`.
- B-02 states that no absolute workspace or Lakehouse name is hardcoded,
  the Lakehouse being attached to the notebook. B-02 is **scoped to Bronze**
  and is not binding here, but B-08 records the intent to preserve that
  principle in Silver rather than to depart from it.
- No business rule, Data Quality control, transformation or ordering
  constraint is altered. B-08 is a **placement decision only**.

---

## B-09 - Silver implementation: technical columns, preconditions and Data Quality behaviour

**Date:** 2026-10-12
**Type:** Implementation decision - Silver layer
**Scope:** `nb_silver_customers` -> `customers.silver_customers`, Customers MVP

**Context.** B-08 settled **where** the Silver table lives. It deliberately
settled nothing about what the notebook carries, when it refuses to write, or
how it reacts to a Data Quality finding. B-04 answered those questions for
Bronze and was **explicitly scoped to the Bronze layer**; it is **not**
transposed here. B-09 answers them for Silver on its own authority.

### What is approved

**1. Technical columns.** `silver_customers` carries the three Bronze
technical columns - `_batch_id`, `_ingestion_timestamp`, `_source_file` -
**propagated unchanged from `bronze_customers`, never regenerated**.

- `_batch_id` is **mandatory**: DQ-25 declares its evaluation layer as
  "Bronze and Silver" and requires exactly one distinct value in
  `silver_customers`.
- `_ingestion_timestamp` is retained as the cross-run chronological key
  (B-05), the UUID of B-01 carrying no chronology.
- `_source_file` is retained for lineage (B-02).
- **No new technical column is created.** A column that no business rule and
  no Data Quality control requires would be an undocumented rule (STANDARD
  `silver.undocumented_business_rule`,
  `forbidden_actions.invent_business_rule`).

**2a. Abort preconditions - evaluated BEFORE the write.** The run aborts and
`customers.silver_customers` is **left untouched** when any of the following
holds:

| # | Precondition | Checked |
|---|---|---|
| 1 | The Bronze source is unreadable or cannot be resolved | Before read |
| 2 | The Bronze source is **empty** | Before transformation |
| 3 | `_batch_id` is **null** on any Bronze source row | Before transformation |
| 4 | The Bronze source holds a number of distinct `_batch_id` **other than exactly 1** | Before transformation |
| 5 | The Bronze source does **not expose the 11 required columns** (decision 2c) | Before transformation |
| 6 | The **target Lakehouse identity** does not match the expected one | Immediately before the write |

All six are evaluated **before any write is attempted**. Aborting at this
stage writes nothing, deletes nothing and leaves the previous content of the
target intact. This guarantee is **structural**: the write statement is never
reached.

**2b. Technical failure DURING or AFTER the write.** A failure raised by the
write itself, or by any step following it, is **logged and propagated**. The
run stops.

**No claim is made that the target is unchanged.** Unlike 2a, the write
statement has been reached, and the notebook **cannot assert** the resulting
state of `customers.silver_customers`.

Consequently:

- the notebook must **not** log any message asserting that the target is
  intact after a failure of this class;
- the state of `customers.silver_customers` is **undetermined** and must be
  **verified by a human** before any re-run;
- the Data Quality report of that execution **may be incomplete, depending on
  where the failure occurred**. The post-write controls DQ-24 and DQ-25 may
  have run, partially run, or not run at all. The notebook must not assert
  which. The absence of a `control_id` from the output means **not
  evaluated** - neither PASS nor FAIL.

This distinction is deliberate. 2a offers a guarantee; 2b offers only
traceability.

**2c. Required Bronze source columns.** `customers.bronze_customers` must
expose **at least these 11 columns**, verified by **name and presence**:

| Group | Columns | Authority |
|---|---|---|
| Contract columns (8) | `customer_id`, `customer_name`, `customer_type`, `city`, `postal_code`, `region`, `country`, `created_date` | CONTRACT `schema` - exact names |
| Technical columns (3) | `_source_file`, `_ingestion_timestamp`, `_batch_id` | STANDARD `bronze.technical_columns` |

- **Column order is irrelevant.** Silver addresses columns by name.
- **A missing column aborts the run** - precondition 2a-5.
- **An extra column does not block the read.** It is **not propagated** to
  `silver_customers`: Silver projects the 8 contract columns plus the 3
  technical columns of decision 1, and nothing else. An unexpected column is
  ignored, never silently persisted.
- Propagating an undeclared column would extend the Silver structure without
  any authority. **The Data Contract and the business rules are unchanged.**
- **Column types are deliberately NOT verified.** STANDARD
  `bronze.preserve_source_schema: true` means Bronze carries the source
  representation, and the `created_date` conversion is a **Silver** operation
  (BR-CUSTOMER-007, DQ-11, STANDARD `silver.allowed_operations: cast`).
  Asserting a Bronze type would invent a type contract that no authority
  states.
- This precondition is **not** DQ-01 under another name. DQ-01 checks the 8
  contract columns of the **source file at Bronze read**. 2c checks the
  columns of the **Bronze table read by Silver**. It carries no `control_id`
  and is not added to the Data Quality catalogue (decision 6).

**3. Data Quality findings on business data.** Every Data Quality control
evaluating the business content reports, **keeps the affected records**, and
**lets the run continue**. No correction, no rejection, no quarantine, no
deletion. This follows directly from STANDARD `data_quality.on_failure` -
`action: report`, `record_handling: keep_in_target`, `quarantine: false`,
`reject: false` - which is **not scoped by layer** - and from HV-04. A
`BLOCKING` severity qualifies the gravity of the finding, never the fate of
the run.

**4. DQ-26 - survivorship conflict.** When records sharing a `customer_id`
differ on at least one business attribute **after trim**, the notebook:

1. **keeps every conflicting record** - none is removed, corrected or
   quarantined;
2. **reports** the `customer_id`, the conflicting records and the differing
   attributes;
3. **raises a human validation request** (STANDARD `human_in_the_loop`,
   BR-CUSTOMER-001 branch (b), HV-01);
4. **continues execution**, provided preconditions 2a-1 to 2a-6 are
   satisfied.

The agent **never selects a survivor** when a conflict exists.

**DQ-26 never aborts the run by itself, and never overrides a safety
precondition.** The two mechanisms are independent and the preconditions
prevail: if the target-Lakehouse identity guard 2a-6 fails, the run aborts
regardless of the DQ-26 outcome.

**Ordering.** DQ-26 is evaluated during survivorship, therefore **before** the
identity guard and before the write. A DQ-26 finding is recorded, then the run
proceeds to 2a-6 and to the write.

**Expected side effects of a DQ-26 finding.** Duplicate keys remain in
`silver_customers`, so CONTRACT `quality.business_key.unique: true` is
breached - that breach is **reported by DQ-03** and **must not be resolved by
the agent** - and DQ-24 reports a smaller row-count delta than the
deduplication would otherwise have produced. Neither is a defect to correct.
Both are the documented consequence of BR-CUSTOMER-001 branch (b).

**Current state.** DQ-26 is **PASS** on the profiled file: the 8 duplicated
keys are strictly identical on all 7 business attributes after trim. Branch
(b) has never fired.

**5. Target Lakehouse identity guard.** Immediately before the write, the
notebook verifies the identity of the default Lakehouse through its **Fabric
identifiers - Lakehouse identifier and workspace identifier**, not through its
display name. A Lakehouse can be renamed while keeping its identifier, and a
different Lakehouse may carry the same display name in another workspace; the
name is therefore used for diagnostic messages only. **The expected
identifiers are supplied by configuration and are not hardcoded in the
business code.** On mismatch the run aborts before the write.

**6. No extension of DQ-01 or DQ-23 to Silver in this MVP.** Preconditions 2a-2
to 2a-6 are **technical preconditions**, not Data Quality controls. They carry
no `control_id`, they are not added to the Data Quality catalogue, and
`generated/customers_data_quality.md` is **not regenerated**.

**7. `_batch_id` semantics.** In `silver_customers`, `_batch_id` identifies the
**Bronze batch the data originates from**. It does **not** identify a Silver
execution.

### R-04 - Amendment to decision 5: name as resolution key

**Date:** 2026-10-12
**Type:** Amendment to an approved decision - limited scope
**Amends:** B-09 decision 5 only. Decisions 1, 2a, 2b, 2c, 3, 4, 6 and 7 are
unchanged.
**Closes:** open point S-06

#### Clause superseded

Decision 5 reads:

> the name is therefore used for diagnostic messages only

Those words are **superseded for this guard only**. Everything else in
decision 5 - verification through Fabric identifiers, expected identifiers not
hardcoded in business code, abort before the write on mismatch - **stands
unchanged**.

#### What is now authorised

The notebook may use the **governed display name `lkh_silver`** as a
**resolution key** to obtain the expected Lakehouse identifier at run time.

`lkh_silver` is not an arbitrary configuration value. It is fixed by STANDARD
`naming`, by CONTRACT `target.silver_table` and by decision B-08. It is
already written, in plain text, in this decision file.

#### What remains mandatory

1. The **final comparison is made on Fabric identifiers**, never on names. The
   resolved identifier is compared to the identifier of the Lakehouse actually
   attached, obtained from the notebook runtime context.
2. The guard additionally asserts that the attached Lakehouse belongs to the
   **workspace the notebook is executing in**.
3. The display name is used for the resolution lookup and for diagnostic
   messages. It is **never** accepted as proof of identity by itself.
4. A **failed resolution** - `lkh_silver` absent, or insufficient permission -
   is treated as a **mismatch** and aborts the run under precondition 2a-6. It
   creates no new precondition and is never treated as a pass-through.
5. **No GUID is hardcoded in the business code, and none is written into any
   hand-authored configuration file.** GUIDs do appear in the
   Fabric-generated `# META` block of `notebook-content.py`: they are written
   by Microsoft Fabric, they are **authorised**, and they must **never be
   hand-edited** (B-07). The guard does not read them.

#### What this amendment explicitly is NOT

**This is not an independent GUID validation.**

The expected identifier is derived from the workspace itself at run time. It
is **not** an external, independently supplied reference value. A workspace
whose contents have been renamed or replaced will resolve a different item
under the same governed name, and the guard will accept it.

The guard therefore proves **"the attached Lakehouse is the one currently
named `lkh_silver` in this workspace"**. It does **not** prove **"the attached
Lakehouse is the Silver Lakehouse approved by B-08"**.

#### Relationship to B-02

B-02 forbids hardcoding a name **to address data**. R-04 uses a governed name
**to verify a target**. The write path stays relative to the attached
Lakehouse and is unchanged. **B-02 is not amended.**

#### Relationship to B-07

The guard reads the notebook **runtime context**. It never parses the `# META`
block, which stays Fabric-owned and is never read as a configuration source,
nor hand-edited.

#### Dependency on S-03

R-04 presupposes that `lkh_silver` is the default attached Lakehouse. If it is
not attached, the guard aborts the run, which is the intended behaviour.

#### Scope limit

This amendment is scoped to the **target-Lakehouse identity guard** of
`nb_silver_customers`, the **Customers MVP** and the **DEV workspace**. It is
not a general project convention, it does not authorise name-based addressing
anywhere else, and it does not modify B-02, B-07 or B-08.

**Execution of `nb_silver_customers` remains not authorised.**

### What is explicitly NOT settled by B-09

| # | Open point | Status |
|---|---|---|
| 1 | The **configuration mechanism** supplying the expected Fabric identifiers | **Closed by R-04** - no configuration mechanism; run-time resolution of the governed name |
| 2 | Verification of the **source** Lakehouse identity | **Undetermined**, depends on S-04 |
| 3 | The cross-Lakehouse read method | Unchanged: open point S-04 |
| 4 | Any execution of `nb_silver_customers` | **Not authorised.** HV-07 covers preparation only |

**Consequences.**

- The Data Contract, the business rules and the project standards are
  **unchanged**. B-09 creates no business rule and alters none.
- The contract declares 8 columns and does not enumerate the Silver table's
  columns. Bronze already carries 8 contract columns plus 3 technical columns
  by STANDARD `bronze.technical_columns`; B-09 **extends an established
  pattern** rather than creating one.
- Technical columns are **excluded from survivorship comparison**
  (BR-CUSTOMER-001, 7 business attributes). B-01, B-02 and B-05 make the three
  values constant across a batch, so duplicate rows carry identical technical
  values and **the choice of survivor is never affected** by this decision.
- Preconditions 2a-2 to 2a-6 **appear in the notebook log, not in the Data
  Quality result set** of B-03, since they carry no `control_id`. A run aborted
  by a precondition therefore produces an incomplete DQ report by design.
- Because `_batch_id` identifies the Bronze batch (decision 7), **two Silver
  runs over the same Bronze batch are indistinguishable** from the table
  content alone. This is accepted for the MVP; cross-run Silver audit is
  deferred together with persistent Data Quality storage (B-03).
- DQ-25 evaluated on `silver_customers` after the write remains **report
  only**: it deletes no residual batch (STANDARD
  `forbidden_actions.delete_data`).
- Expected results for the Bronze batch validated by HV-07, should Silver ever
  be executed on it: DQ-03 PASS with 500 unique keys, DQ-24 a -8 row delta from
  508 to 500, DQ-25 one distinct `_batch_id`, DQ-26 PASS, DQ-16 FAIL on 5 rows
  and DQ-19 reporting 12 rows - both by design.

### Documentation inconsistency flagged, not corrected

`B-03` bounds the `control_id` field of an emitted Data Quality result to
`DQ-01 ... DQ-25`, while the Data Quality catalogue reaches **DQ-26**. The
bound has no effect in Bronze, DQ-26 being a Silver control, but it becomes
**factually wrong as soon as `nb_silver_customers` emits DQ-26**.

This is a **pre-existing inconsistency**, older than B-08 and B-09. It is
**deliberately not corrected here**: amending B-03 would modify an already
approved decision and requires a separate human validation.

A second, related gap: B-03 defines no notion of a **partial** Data Quality
report, although B-09 creates two situations that produce one - an abort on a
precondition, and a failure during or after the write. In both cases the
absence of a `control_id` from the output means **not evaluated**, neither
PASS nor FAIL. This tri-state is recorded here and is not documented in B-03.

---

## Remaining unresolved decisions

The `S-xx` series records **Silver open points**, opened by B-08 and B-09.
None of them is approved, and none of them is a business decision. They fall
into two distinct categories, and **neither category suspends the design and
code authoring authorised by HV-07**.

### Category A - Fabric configuration and deployment prerequisites

Environment prerequisites. **All three are now done**, carried out in Fabric
by the human Data Engineer and synchronised to `dev` by Fabric Git
integration at commit `d07266f`.

| ID | Subject | Approval trigger | Status |
|---|---|---|---|
| S-01 | Creation of Lakehouse `lkh_silver`, schema-enabled | `create_fabric_item` | **DONE** - `lkh_silver.Lakehouse/` serialised on `dev`; `lakehouse.metadata.json` reports `defaultSchema: dbo` |
| S-02 | Creation of schema `customers` inside `lkh_silver` | `create_fabric_item` | **DONE** - **verified visually in the Fabric UI** by the human Data Engineer. A serialised Lakehouse carries no schema or table inventory, so this is **not verifiable from this repository** |
| S-03 | Attachment of `lkh_silver` as default and `lkh_bronze` as secondary Lakehouse - Fabric UI only, per B-07 | `modify_fabric_item` | **DONE** - evidenced by the `# META` block of `nb_silver_customers`: `default_lakehouse_name` is `lkh_silver` and `known_lakehouses` also lists `lkh_bronze` |

Category A no longer blocks deployment. **Execution remains unauthorised** for
reasons unrelated to it: HV-07 covers preparation only.

### Category B - Decisions required to finalise part of the implementation

These block only the code sections they name. The remainder of
`nb_silver_customers` can be designed and authored now.

| ID | Subject | Blocks | Does not block |
|---|---|---|---|
| S-04 | Cross-Lakehouse read method, to be confirmed by test before being coded | The source read cell only | Every transformation and Data Quality cell |

**Resolved in this category.** S-05 - Silver technical columns, abort policy
and target-Lakehouse guard - is **resolved in principle by B-09**. B-09
settles *what* the notebook carries, *when* it refuses to write, and *how* it
reacts to a Data Quality finding.

**S-06 is closed by R-04.** The answer is that **no configuration mechanism is
introduced**. The expected identifier is resolved at run time from the
governed name `lkh_silver` in the current workspace. No Variable Library, no
notebook resource file, no parameter cell and no Environment item is created,
so no additional `create_fabric_item` approval is opened.

**Accepted security assumptions.** The guard is only as strong as these, and
none of them is enforced by code:

| # | Assumption | Basis | If violated |
|---|---|---|---|
| H1 | Lakehouse display names are unique within a workspace | Documented Fabric constraint | Resolution ambiguous - not expected to occur |
| H2 | The Lakehouse named `lkh_silver` in the workspace **is** the Silver target approved by B-08 | Workspace governance, **not verifiable by the notebook** | The guard accepts the wrong Lakehouse |
| H3 | No item is renamed to `lkh_silver` while being something else | Workspace governance | Same as H2 - **the accepted residual risk** |
| H4 | The identity reported by the runtime context is the Lakehouse the write actually resolves to | **Not verified** - see test T4 | The guard is decorative |
| H5 | Resolution without an explicit workspace argument targets the current workspace | Documented default scope | Cross-workspace resolution |
| H6 | The executing identity may read the Lakehouse metadata | Documented permission requirement | Resolution fails - aborts, which is safe |

**H2 and H3 are the price of this option and are accepted knowingly for the
MVP.** They are replaced by an externally supplied identifier the day a
Variable Library is introduced, which remains the documented target beyond the
MVP.

**Fabric tests still required before the guard is trusted.** None can be run
without executing a notebook in Fabric, which is not authorised.

| # | Test | Decides |
|---|---|---|
| T1 | Values returned by the runtime context with, and without, an attached Lakehouse | Handling of empty identities |
| T2 | Behaviour of the Lakehouse resolution when the item is absent or permission is denied - exception or empty return | Shape of the error handling |
| T3 | Context access notation - the documentation shows bracket access only | Correctness of the read |
| T4 | **Coherence between the identity reported by the runtime context and the Lakehouse the relative-name write actually resolves to** | **Whether the guard protects anything at all** |
| T5 | Effect of the secondary attached Lakehouse on the reported default identity | Interaction with the cross-Lakehouse read |

**T4 is decisive.** Until it passes, R-04 describes an intent, not a proven
protection.

### What is not blocked

HV-07 remains in force: the **design and code authoring** of
`nb_silver_customers` are authorised. Nothing in S-04 suspends that
authorisation. The following are fully determined by the Data Contract, the
business rules and the Data Quality specification, and can be written now:

- the transformation chain and its mandatory ordering - trim
  (BR-CUSTOMER-002) before survivorship (BR-CUSTOMER-001), per DQ-20;
- the `FR` -> `France` normalization (BR-CUSTOMER-003) and the
  `created_date` cast (BR-CUSTOMER-007);
- the active non-transformations - region preserved (BR-CUSTOMER-004,
  HV-02, R-01), city casing preserved (BR-CUSTOMER-008, HV-03);
- the Data Quality controls evaluated on the Silver layer.

B-09 additionally determines, and therefore unblocks:

- the projection of the three technical columns and the required Bronze
  source columns;
- the abort preconditions and the distinct handling of a failure during or
  after the write;
- the behaviour on a Data Quality finding, DQ-26 included.

What remains unauthorised is the **execution** of `nb_silver_customers` in
Fabric, which HV-07 explicitly excluded.

### Status roll-up

HV-01 to HV-07, R-01 to R-04 and B-01 to B-09 are resolved. No **business**
decision remains open for the Customers use case. HV-07 is resolved for
batch `c5082b63-22b4-4c95-ad41-78c8cfb86507` only: the next Bronze run will
raise a new DQ-16 validation.

B-08 settles **where** the Silver table lives. B-09 settles **what it
carries and when it refuses to write**. R-04 settles **how the target is
identified**. None of them authorises any execution.

**Silver open points: `S-04` only**, and it remains **untested**. S-01, S-02
and S-03 are done, S-05 is resolved in principle by B-09, S-06 is closed by
R-04.

### Deferred, non-blocking items carried forward

| Item | Deferred by | Revisit when |
|---|---|---|
| Data Contract gaps G-02 to G-05 | HV-06 | The contract is unfrozen |
| `source_semantics` promotion to the contract | HV-05 / R-03 | HV-06 is lifted |
| Persistent Data Quality storage | B-03 | Beyond MVP |
| Orchestration, scheduling, environment separation | Not raised | Beyond MVP |

---

## Downstream artifacts to refresh

| Artifact | Required action | Status |
|---|---|---|
| `generated/customers_data_quality.md` | Regenerate - DQ-03, DQ-06, DQ-11, DQ-16, DQ-17, DQ-19, DQ-24 are impacted | REGENERATED |
| `nb_bronze_customers` | Generate PySpark implementation | GENERATED - `generated/nb_bronze_customers.ipynb`, B-01 to B-06 applied, execution in Fabric not authorised |
| `nb_bronze_customers` (Fabric item) | Align the Fabric-serialised payload with B-06 - it was imported from a pre-B-06 revision | CORRECTED on `dev` - `fabric/ws_fabric_ai_project_agent_dev/nb_bronze_customers.Notebook/notebook-content.py`, cell-for-cell parity verified. **Executed 2026-10-12**, batch `c5082b63-22b4-4c95-ad41-78c8cfb86507`: 508 rows written to `customers.bronze_customers`, 500 distinct keys, 12 PASS / 4 FAIL by design. The revision deployed to the workspace at run time is **not verified** from this repository |
| `generated/nb_bronze_customers.ipynb` | Freeze as superseded design artifact | FROZEN - decision B-07, kept unchanged, no longer the deployment path |
| `lkh_silver` (Fabric item) | Create a schema-enabled Lakehouse and the schema `customers` inside it | **CREATED** - serialised on `dev` at commit `d07266f`, `defaultSchema: dbo`. The schema `customers` was **verified visually in the Fabric UI**; it is not visible in the serialised item (S-01 / S-02 done) |
| `nb_silver_customers` (Fabric item) | Create the notebook and attach the Lakehouses | **CREATED** - serialised on `dev` at commit `d07266f`, **initial Fabric code only**. `lkh_silver` default, `lkh_bronze` secondary (S-03 done) |
| `nb_silver_customers` | Generate PySpark implementation | PREPARATION AUTHORISED - decision HV-07, design and code authoring only. Target placement settled by B-08; technical columns, abort preconditions, Data Quality behaviour and identity guard settled by B-09; guard resolution mechanism settled by R-04. The cross-Lakehouse read method remains open point S-04, **untested**. Execution in Fabric **not authorised** |
| `B-03` - `control_id` bound `DQ-01 ... DQ-25` | Decide whether to extend the bound to DQ-26 or make it unbounded | NOT CORRECTED - inconsistency flagged in B-09, amending an approved decision requires a separate human validation |
