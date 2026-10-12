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
| B-01 | 2026-10-07 | `_batch_id` generated as a UUID once per notebook run | This file - see below | APPROVED |
| B-02 | 2026-10-07 | Single source file `Files/customers.csv` in the attached Lakehouse | This file - see below | APPROVED - MVP |
| B-03 | 2026-10-07 | Data Quality reporting is notebook-output only | This file - see below | APPROVED - MVP, persistence deferred |
| B-04 | 2026-10-07 | Abort before write on DQ-01 failure only | This file - see below | APPROVED |
| B-05 | 2026-10-07 | `_ingestion_timestamp` in UTC, one value per batch | This file - see below | APPROVED |
| B-06 | 2026-10-09 | Schema-enabled Lakehouse `lkh_bronze`, target schema `customers` -> `customers.bronze_customers` | This file - see below | APPROVED |
| B-07 | 2026-10-09 | `fabric/.../notebook-content.py` becomes the single source of truth for executable notebook code; `generated/nb_bronze_customers.ipynb` is frozen as a superseded design artifact | This file - see below | APPROVED - architecture_change |

The `B-xx` series records **Bronze implementation decisions** for
`nb_bronze_customers`. They are implementation-level choices: they do not
create, alter or override any business rule, and they are scoped to the
Customers MVP unless explicitly promoted later.

B-07 is the single exception: it is an **architecture decision** about where
notebook code lives, not a Bronze implementation choice, and it applies to
every notebook in the repository.

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

## Remaining unresolved decisions

| ID | Subject | Blocking for |
|---|---|---|
| - | None | - |

HV-01 to HV-07, R-01 to R-03 and B-01 to B-07 are all resolved. No
decision remains open for the Customers use case. HV-07 is resolved for
batch `c5082b63-22b4-4c95-ad41-78c8cfb86507` only: the next Bronze run will
raise a new DQ-16 validation. **No decision blocks the preparation of
`nb_silver_customers`**; its execution remains unauthorised.

Deferred, non-blocking items carried forward:

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
| `nb_silver_customers` | Generate PySpark implementation | PREPARATION AUTHORISED - decision HV-07, design and code authoring only; execution in Fabric **not authorised** |
