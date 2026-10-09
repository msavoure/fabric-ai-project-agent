# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "a0f34c7c-1ec6-47e3-add7-c3699f958e82",
# META       "default_lakehouse_name": "lkh_bronze",
# META       "default_lakehouse_workspace_id": "fa788bf5-52b0-43e4-9e7d-74d4893573c0",
# META       "known_lakehouses": [
# META         {
# META           "id": "a0f34c7c-1ec6-47e3-add7-c3699f958e82"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # nb_bronze_customers
# 
# **Bronze ingestion of the Customers dataset.**
# 
# | Item | Value | Repository source |
# |---|---|---|
# | Notebook | `nb_bronze_customers` | STANDARD `naming.notebooks.ingestion` |
# | Target table | `bronze_customers` | STANDARD `naming.tables.bronze` + CONTRACT `target.bronze_table` |
# | Source | `Files/customers.csv` | DECISION B-02 |
# | Format | Delta | STANDARD `bronze.storage_format` |
# | Load mode | Full refresh / overwrite | DECISION HV-05 |
# 
# ## Bronze principles enforced by this notebook
# 
# STANDARD `architecture.layers.bronze.preserve_source_data: true` and
# `transformations_allowed: false`:
# 
# - **no trim** - the BR-CUSTOMER-002 trim is a Silver operation;
# - **no normalization** - BR-CUSTOMER-003 / 004 / 008 are Silver rules;
# - **no cast of business columns** - `created_date` stays a string, the cast is Silver (DQ-11);
# - **no deduplication** - duplicate keys are detected, never removed (BR-CUSTOMER-001 is Silver);
# - **no filtering, no row rejection** - STANDARD `data_quality.on_failure`:
#   `action: report`, `record_handling: keep_in_target`, `quarantine: false`, `reject: false`.
# 
# ## Approved human decisions implemented here
# 
# | Decision | Content |
# |---|---|
# | B-01 | `_batch_id` = one UUID per run, identical on every row |
# | B-02 | Single source file `Files/customers.csv` in the attached Lakehouse |
# | B-03 | Data Quality reporting is notebook output only - no persistent DQ table |
# | B-04 | Abort before write on DQ-01 only; all other controls report, keep, continue |
# | B-05 | `_ingestion_timestamp` in UTC, one value per batch |
# | HV-05 | `full_snapshot` / `full_refresh` / no historization |
# 
# > **Execution is not authorised by the generation request.** Running this notebook
# > creates or overwrites a Fabric Lakehouse table, which is a human-approval trigger
# > (STANDARD `human_approval_required: create_fabric_item` / `modify_fabric_item`).


# MARKDOWN ********************

# ## 1. Imports and configuration

# CELL ********************

# =============================================================================
# Imports and configuration
# =============================================================================
import logging
import uuid
from datetime import datetime, timezone

from pyspark.sql import functions as F
from pyspark.sql.types import (
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# --- Source and target -------------------------------------------------------
# DECISION B-02 - single file, no wildcard, no folder ingestion.
# The path is relative to the Lakehouse attached to this notebook: no workspace
# name and no lakehouse name are hardcoded.
SOURCE_PATH = "Files/customers.csv"

# STANDARD naming.tables.bronze + CONTRACT target.bronze_table
TARGET_TABLE = "bronze_customers"

# Technical column used by the PERMISSIVE reader to capture unparseable rows.
# It is reported, then dropped before the write: STANDARD bronze.technical_columns
# is an exhaustive list and no fourth technical column may be persisted.
CORRUPT_RECORD_COLUMN = "_corrupt_record"

# --- Contract schema ---------------------------------------------------------
# CONTRACT use_cases/distribution/contracts/customers.yaml - exact names, exact order.
CONTRACT_COLUMNS = [
    "customer_id",
    "customer_name",
    "customer_type",
    "city",
    "postal_code",
    "region",
    "country",
    "created_date",
]

# STANDARD bronze.technical_columns - exhaustive.
TECHNICAL_COLUMNS = ["_source_file", "_ingestion_timestamp", "_batch_id"]

# Profiling baseline documented in generated/customers_data_quality.md for the
# current source file. Used for an INFORMATIONAL comparison only, never as a
# hard assertion: a future delivery may legitimately carry a different volume.
BASELINE = {
    "source_data_rows": 508,
    "bronze_rows": 508,
    "distinct_customer_id": 500,
}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Logging and Data Quality result collector
# 
# STANDARD `code_generation.generated_code_must_include: [logging, error_handling, data_quality_checks]`.
# 
# DECISION B-03: Data Quality results are emitted to the notebook output only.
# No persistent Data Quality table is created.

# CELL ********************

# =============================================================================
# Logging
# =============================================================================
logger = logging.getLogger("nb_bronze_customers")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class SchemaConformityError(Exception):
    """Raised when DQ-01 fails.

    DECISION B-04: this is the only Data Quality condition that aborts the run,
    and it aborts BEFORE the write, so no data is deleted or overwritten.
    """


# =============================================================================
# Data Quality result collector (DECISION B-03)
# =============================================================================
DQ_RESULTS = []

SEVERITY_LOG_LEVEL = {
    "INFORMATIONAL": logging.INFO,
    "LOW": logging.INFO,
    "MEDIUM": logging.WARNING,
    "HIGH": logging.ERROR,
    "BLOCKING": logging.ERROR,
}


def record_dq(control_id, severity, status, affected_row_count, message):
    """Record one structured Data Quality result.

    This function REPORTS only. It never removes, quarantines, corrects or
    rejects a row - STANDARD data_quality.on_failure.
    """
    entry = {
        "batch_id": BATCH_ID,
        "control_id": control_id,
        "severity": severity,
        "status": status,
        "affected_row_count": int(affected_row_count),
        "message": message,
    }
    DQ_RESULTS.append(entry)
    level = SEVERITY_LOG_LEVEL[severity] if status == "FAIL" else logging.INFO
    logger.log(
        level,
        "%s | %s | %s | affected_rows=%d | %s",
        control_id,
        severity,
        status,
        entry["affected_row_count"],
        message,
    )
    return entry


def show_df(df, n=50):
    """Render a DataFrame using the Fabric display() when available."""
    try:
        display(df)  # noqa: F821 - injected by the Fabric notebook runtime
    except NameError:
        df.show(n, truncate=False)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Batch identity
# 
# DECISION B-01 - one UUID generated at execution start, applied to every row.
# 
# DECISION B-05 - one UTC timestamp captured at execution start, applied to every row.
# 
# Both are materialised as **constants** before the write. They must never be
# lazily re-evaluated expressions such as a per-row `current_timestamp()`, which
# could yield different values across rows and partitions and would break the
# batch attribution verified by DQ-22 and DQ-25.

# CELL ********************

# =============================================================================
# Batch identity
# =============================================================================
# DECISION B-05 - the session timezone is pinned to UTC so that the timestamp
# literal below is interpreted as UTC and not as the cluster default.
spark.conf.set("spark.sql.session.timeZone", "UTC")

# DECISION B-01 - one UUID per notebook run.
BATCH_ID = str(uuid.uuid4())

# DECISION B-05 - one UTC instant, captured once, held as a naive datetime.
# Combined with the UTC session timezone above, Spark stores the correct instant.
INGESTION_TIMESTAMP = datetime.now(timezone.utc).replace(tzinfo=None)

logger.info("=" * 78)
logger.info("Bronze ingestion started")
logger.info("batch_id                = %s", BATCH_ID)
logger.info("ingestion_timestamp_utc = %s", INGESTION_TIMESTAMP.isoformat())
logger.info("source                  = %s", SOURCE_PATH)
logger.info("target                  = %s (delta, overwrite)", TARGET_TABLE)
logger.info("load_mode               = full_refresh (DECISION HV-05)")
logger.info("=" * 78)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4. DQ-01 - Schema conformity (pre-read gate)
# 
# **Rule.** The ingested dataset must expose exactly the 8 columns declared in the
# contract, with the exact declared names. No missing column, no extra column.
# 
# **Source.** STANDARD `data_quality.mandatory_checks.schema_conformity` + CONTRACT `schema`. Severity HIGH.
# 
# The header is validated **before** the typed read, for two reasons:
# 
# 1. the source file carries a UTF-8 BOM, which would otherwise corrupt the first column name;
# 2. supplying an explicit schema binds values **positionally** - a silent column
#    reorder would map the wrong values onto the right names and pass unnoticed.
# 
# **DECISION B-04.** On failure: report, then abort **before** writing `bronze_customers`.
# Aborting before the write destroys nothing and leaves the previous table content intact.

# CELL ********************

# =============================================================================
# DQ-01 - Schema conformity
# =============================================================================
try:
    header_rows = spark.read.text(SOURCE_PATH).head(1)
except Exception:
    # Technical failure (file absent, unreadable, permissions). Not a Data
    # Quality finding - it must abort the run.
    logger.exception("Technical failure while reading the source header at %s", SOURCE_PATH)
    raise

if not header_rows:
    raise SchemaConformityError(
        "Source file %s is empty - no header line found." % SOURCE_PATH
    )

raw_header = header_rows[0]["value"]
raw_header = raw_header.lstrip("\ufeff")  # strip the UTF-8 BOM
raw_header = raw_header.rstrip("\r")      # defensive: CRLF line terminators
observed_columns = raw_header.split(",")

missing_columns = [c for c in CONTRACT_COLUMNS if c not in observed_columns]
unexpected_columns = [c for c in observed_columns if c not in CONTRACT_COLUMNS]
order_mismatch = observed_columns != CONTRACT_COLUMNS

if missing_columns or unexpected_columns or order_mismatch:
    affected = len(missing_columns) + len(unexpected_columns)
    if affected == 0:
        affected = 1  # order mismatch only
    dq01_message = (
        "Header does not conform to the Data Contract. "
        "expected=%s observed=%s missing=%s unexpected=%s order_mismatch=%s. "
        "The schema must not be auto-aligned and the Data Contract must not be "
        "modified. A schema divergence invalidates every downstream control - "
        "escalate to a human."
        % (
            CONTRACT_COLUMNS,
            observed_columns,
            missing_columns,
            unexpected_columns,
            order_mismatch,
        )
    )
    record_dq("DQ-01", "HIGH", "FAIL", affected, dq01_message)
    logger.error(
        "ABORTING before writing %s - DECISION B-04. No data has been modified.",
        TARGET_TABLE,
    )
    raise SchemaConformityError(dq01_message)

record_dq(
    "DQ-01",
    "HIGH",
    "PASS",
    0,
    "8/8 contract columns present, exact names, exact order: %s." % observed_columns,
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. Source read - explicit all-string schema
# 
# STANDARD `bronze.preserve_source_schema: true`. A CSV file carries no types:
# every source value is text, so preserving the source schema means reading all
# 8 columns as `string`.
# 
# | Column | Bronze type | Why |
# |---|---|---|
# | `created_date` | **string** | The contract declares `date`, but casting is a **Silver** operation (STANDARD `silver.allowed_operations.cast`, control DQ-11). Casting here would silently turn a non-convertible value into NULL and destroy the raw value. |
# | `postal_code` | **string** | Leading zeros (`06000`, `29200`) must survive - control DQ-14. |
# | all others | string | Identical to the contract. |
# 
# `inferSchema` is disabled - DQ-14 classifies inference at read as a *pipeline
# configuration defect*.
# 
# All fields are declared **nullable at Spark level on purpose**. The contract's
# `nullable: false` on five columns is enforced by DQ-02, DQ-04, DQ-07, DQ-08,
# DQ-12 and DQ-13 as *reported* controls. Declaring them non-nullable in the
# reader would make Spark error on a null - a row rejection, which Bronze forbids.
# 
# `mode` is `PERMISSIVE`, never `DROPMALFORMED` or `FAILFAST`: dropping a row
# would violate `preserve_source_data`.


# CELL ********************

# =============================================================================
# Explicit source schema - all columns as string
# =============================================================================
SOURCE_SCHEMA = StructType(
    [StructField(name, StringType(), True) for name in CONTRACT_COLUMNS]
    + [StructField(CORRUPT_RECORD_COLUMN, StringType(), True)]
)

# Independent source row count, used by DQ-22. Counting the physical lines and
# subtracting the header gives a measurement that does not depend on the CSV
# parser, so DQ-22 genuinely reconciles two independent numbers.
try:
    source_line_count = spark.read.text(SOURCE_PATH).count()
except Exception:
    logger.exception("Technical failure while counting source lines at %s", SOURCE_PATH)
    raise

source_data_row_count = source_line_count - 1  # header excluded
logger.info(
    "Source measured | physical_lines=%d | header_lines=1 | data_rows=%d",
    source_line_count,
    source_data_row_count,
)

# =============================================================================
# Typed read
# =============================================================================
try:
    df_raw = (
        spark.read
        .schema(SOURCE_SCHEMA)
        .option("header", "true")
        .option("inferSchema", "false")
        .option("delimiter", ",")
        .option("encoding", "UTF-8")
        .option("quote", '"')
        .option("escape", '"')
        .option("multiLine", "false")
        .option("mode", "PERMISSIVE")
        .option("columnNameOfCorruptRecord", CORRUPT_RECORD_COLUMN)
        .csv(SOURCE_PATH)
        # _source_file is projected on the file scan itself, before any caching:
        # input_file_name() returns an empty string when evaluated on a cached
        # DataFrame. DQ-23 verifies the result is populated.
        .withColumn("_source_file", F.input_file_name())
    )

    # Materialise once: the DataFrame is traversed by every control below, and
    # Spark requires the corrupt-record column to be materialised before it can
    # be referenced in a filter.
    df_raw.cache()
    read_row_count = df_raw.count()
except Exception:
    logger.exception("Technical failure while reading %s", SOURCE_PATH)
    raise

logger.info("Rows read by the CSV parser = %d", read_row_count)

# Unparseable rows are REPORTED and KEPT - never dropped.
corrupt_count = df_raw.filter(F.col(CORRUPT_RECORD_COLUMN).isNotNull()).count()
if corrupt_count:
    logger.warning(
        "%d unparseable source row(s) captured. They are KEPT and written to "
        "Bronze - no row may be dropped at this layer.",
        corrupt_count,
    )
    show_df(
        df_raw.filter(F.col(CORRUPT_RECORD_COLUMN).isNotNull())
        .select(CORRUPT_RECORD_COLUMN)
        .limit(20)
    )
else:
    logger.info("No unparseable source row detected.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6. Bronze technical columns
# 
# STANDARD `bronze.technical_columns` - exactly three, names and types fixed.
# No fourth technical column may be added: the list is exhaustive, and inventing
# a hash, a surrogate key or a row number would be a transformation.
# 
# | Column | Type | Population |
# |---|---|---|
# | `_source_file` | string | `input_file_name()`, evaluated on the file scan |
# | `_ingestion_timestamp` | timestamp | Constant UTC instant - DECISION B-05 |
# | `_batch_id` | string | Constant UUID - DECISION B-01 |

# CELL ********************

# =============================================================================
# Bronze technical columns
# =============================================================================
df_bronze = (
    df_raw
    # The corrupt-record column is a reader artefact, not a Bronze technical
    # column. Its rows have already been reported and remain in the DataFrame.
    .drop(CORRUPT_RECORD_COLUMN)
    .withColumn(
        "_ingestion_timestamp", F.lit(INGESTION_TIMESTAMP).cast(TimestampType())
    )
    .withColumn("_batch_id", F.lit(BATCH_ID).cast(StringType()))
    # Deterministic column order: the 8 contract columns, then the 3 technical ones.
    .select(*CONTRACT_COLUMNS, *TECHNICAL_COLUMNS)
)

df_bronze.cache()
bronze_candidate_count = df_bronze.count()
df_raw.unpersist()

logger.info(
    "Bronze candidate DataFrame | rows=%d | columns=%d (%d contract + %d technical)",
    bronze_candidate_count,
    len(df_bronze.columns),
    len(CONTRACT_COLUMNS),
    len(TECHNICAL_COLUMNS),
)
logger.info("Bronze schema: %s", df_bronze.dtypes)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 7. Pre-write Data Quality controls
# 
# Controls whose evaluation layer includes **Bronze** in
# `generated/customers_data_quality.md`.
# 
# **DECISION B-04** - every control below reports, keeps the affected records and
# lets the run continue. None of them rejects, quarantines or corrects a row.
# 
# | Control | Subject | Severity | Bronze role |
# |---|---|---|---|
# | DQ-02 | `customer_id` not null | BLOCKING | Detection |
# | DQ-03 | `customer_id` uniqueness | BLOCKING | **Detection only** - survivorship is Silver |
# | DQ-04 | `customer_name` not null | HIGH | Detection |
# | DQ-05 | `customer_name` whitespace | MEDIUM | **Indicator only** - the trim is Silver |
# | DQ-07 | `customer_type` not null | HIGH | Detection |
# | DQ-08 | `country` not null | HIGH | Detection |
# | DQ-09 | `country` normalization | MEDIUM | **Indicator only** - `FR` to `France` is Silver |
# | DQ-12 | `created_date` not null | HIGH | Detection on the raw string |
# | DQ-13 | `postal_code` not null | HIGH | Detection |
# | DQ-14 | `postal_code` typing integrity | HIGH | At read |
# | DQ-16 | `region = Rhone Alpes` | HIGH | Detection + escalation, value preserved |
# | DQ-21 | Whitespace on `customer_id` / `postal_code` | LOW | Detection, no trim |
# 
# DQ-06, DQ-10, DQ-11, DQ-15, DQ-18, DQ-19, DQ-20, DQ-24 and DQ-26 are Silver
# controls and are **not** evaluated here. **DQ-17 is WITHDRAWN** and must not be
# implemented in any form.


# CELL ********************

# =============================================================================
# Pre-write Data Quality controls - detection and reporting only
# =============================================================================
def count_where(df, condition):
    """Count the rows matching a condition. Never modifies the DataFrame."""
    return df.filter(condition).count()


def has_outer_whitespace(column_name):
    """Condition: the value carries a leading or trailing space.

    NULL-safe: a NULL is not a whitespace violation.
    """
    col = F.col(column_name)
    return col.isNotNull() & (col != F.trim(col))


# --- DQ-02 - customer_id not null -------------------------------------------
# STANDARD data_quality.mandatory_checks.primary_key_null + CONTRACT nullable:false
dq02_rows = count_where(df_bronze, F.col("customer_id").isNull())
record_dq(
    "DQ-02",
    "BLOCKING",
    "PASS" if dq02_rows == 0 else "FAIL",
    dq02_rows,
    "No null customer_id."
    if dq02_rows == 0
    else "%d row(s) carry a null customer_id. Reported and KEPT in Bronze "
    "(record_handling: keep_in_target). A null key breaks the DQ-03 "
    "uniqueness evaluation and the Silver survivorship." % dq02_rows,
)

# --- DQ-03 - customer_id uniqueness (DETECTION ONLY at Bronze) ---------------
# STANDARD primary_key_uniqueness + CONTRACT quality.business_key.
# BR-CUSTOMER-001 survivorship is a SILVER step and must NOT run here:
# STANDARD bronze.transformations_allowed: false. No row is removed.
duplicate_keys_df = (
    df_bronze.groupBy("customer_id")
    .count()
    .filter(F.col("count") > 1)
    .orderBy("customer_id")
)
duplicate_key_rows = duplicate_keys_df.collect()
duplicate_key_count = len(duplicate_key_rows)
duplicate_row_count = sum(r["count"] for r in duplicate_key_rows)
duplicate_key_list = [r["customer_id"] for r in duplicate_key_rows]

record_dq(
    "DQ-03",
    "BLOCKING",
    "PASS" if duplicate_key_count == 0 else "FAIL",
    duplicate_row_count,
    "customer_id is unique across the batch."
    if duplicate_key_count == 0
    else "%d duplicate customer_id value(s) spanning %d row(s): %s. "
    "Bronze performs DETECTION ONLY - all rows are written unchanged. "
    "The BR-CUSTOMER-001 survivorship runs in Silver, after the "
    "BR-CUSTOMER-002 trim."
    % (duplicate_key_count, duplicate_row_count, duplicate_key_list),
)
if duplicate_key_count:
    show_df(duplicate_keys_df)

# --- DQ-04 - customer_name not null -----------------------------------------
dq04_rows = count_where(df_bronze, F.col("customer_name").isNull())
record_dq(
    "DQ-04",
    "HIGH",
    "PASS" if dq04_rows == 0 else "FAIL",
    dq04_rows,
    "No null customer_name."
    if dq04_rows == 0
    else "%d row(s) carry a null customer_name (CONTRACT nullable:false). "
    "Reported and KEPT." % dq04_rows,
)

# --- DQ-05 - customer_name whitespace (INDICATOR ONLY at Bronze) -------------
# BUSINESS RULE BR-CUSTOMER-002. The trim is a SILVER operation
# (STANDARD silver.allowed_operations.trim). Bronze must not trim.
dq05_rows = count_where(df_bronze, has_outer_whitespace("customer_name"))
record_dq(
    "DQ-05",
    "MEDIUM",
    "PASS" if dq05_rows == 0 else "FAIL",
    dq05_rows,
    "No leading or trailing whitespace on customer_name."
    if dq05_rows == 0
    else "%d row(s) carry leading or trailing whitespace on customer_name. "
    "Bronze is an INDICATOR: the value is preserved exactly as delivered. "
    "The BR-CUSTOMER-002 trim runs in Silver, and must run BEFORE the "
    "DQ-03 survivorship evaluation." % dq05_rows,
)

# --- DQ-07 - customer_type not null -----------------------------------------
dq07_rows = count_where(df_bronze, F.col("customer_type").isNull())
record_dq(
    "DQ-07",
    "HIGH",
    "PASS" if dq07_rows == 0 else "FAIL",
    dq07_rows,
    "No null customer_type."
    if dq07_rows == 0
    else "%d row(s) carry a null customer_type (CONTRACT nullable:false). "
    "Reported and KEPT." % dq07_rows,
)

# --- DQ-08 - country not null -----------------------------------------------
dq08_rows = count_where(df_bronze, F.col("country").isNull())
record_dq(
    "DQ-08",
    "HIGH",
    "PASS" if dq08_rows == 0 else "FAIL",
    dq08_rows,
    "No null country."
    if dq08_rows == 0
    else "%d row(s) carry a null country (CONTRACT nullable:false). "
    "Reported and KEPT." % dq08_rows,
)

# --- DQ-09 - country normalization (INDICATOR ONLY at Bronze) ----------------
# BUSINESS RULE BR-CUSTOMER-003: FR and France designate the same country, and
# the Silver standard value is France. The normalization is a SILVER operation.
# Bronze counts the rows that are not already at the Silver standard value and
# preserves every value unchanged.
country_distribution_df = (
    df_bronze.groupBy("country").count().orderBy(F.col("count").desc())
)
country_distribution = [
    (r["country"], r["count"]) for r in country_distribution_df.collect()
]
dq09_rows = count_where(
    df_bronze, F.col("country").isNotNull() & (F.col("country") != F.lit("France"))
)
record_dq(
    "DQ-09",
    "MEDIUM",
    "PASS" if dq09_rows == 0 else "FAIL",
    dq09_rows,
    "All country values already carry the Silver standard value. "
    "Distribution: %s." % country_distribution
    if dq09_rows == 0
    else "%d row(s) carry a country value that differs from the Silver "
    "standard value 'France'. Distribution: %s. Bronze is an INDICATOR: "
    "the source value is preserved. The BR-CUSTOMER-003 normalization "
    "runs in Silver." % (dq09_rows, country_distribution),
)

# --- DQ-12 - created_date not null ------------------------------------------
# Evaluated on the RAW STRING. The cast to date is a Silver step (DQ-11).
dq12_rows = count_where(df_bronze, F.col("created_date").isNull())
record_dq(
    "DQ-12",
    "HIGH",
    "PASS" if dq12_rows == 0 else "FAIL",
    dq12_rows,
    "No null created_date in the source."
    if dq12_rows == 0
    else "%d row(s) carry a null created_date (CONTRACT nullable:false). "
    "Reported and KEPT. Note: this count is measured on the raw string, "
    "so it cannot be confused with a NULL produced by a failed cast - "
    "that case is DQ-11, in Silver." % dq12_rows,
)

# --- DQ-13 - postal_code not null -------------------------------------------
dq13_rows = count_where(df_bronze, F.col("postal_code").isNull())
record_dq(
    "DQ-13",
    "HIGH",
    "PASS" if dq13_rows == 0 else "FAIL",
    dq13_rows,
    "No null postal_code."
    if dq13_rows == 0
    else "%d row(s) carry a null postal_code (CONTRACT nullable:false). "
    "Reported and KEPT." % dq13_rows,
)

# --- DQ-14 - postal_code typing integrity -----------------------------------
# CONTRACT postal_code.type: string + STANDARD bronze.preserve_source_schema.
# A failure here is a PIPELINE CONFIGURATION defect, not a source data defect:
# it would mean schema inference was applied instead of the declared schema.
actual_types = dict(df_bronze.dtypes)
non_string_columns = {
    name: actual_types[name]
    for name in CONTRACT_COLUMNS
    if actual_types.get(name) != "string"
}
leading_zero_rows = count_where(df_bronze, F.col("postal_code").startswith("0"))
record_dq(
    "DQ-14",
    "HIGH",
    "PASS" if not non_string_columns else "FAIL",
    len(non_string_columns),
    "All 8 contract columns are typed string. %d postal_code value(s) carry a "
    "leading zero and are intact." % leading_zero_rows
    if not non_string_columns
    else "Schema inference appears to have been applied: %s are not typed "
    "string. This is a pipeline configuration defect - leading zeros in "
    "postal_code may have been destroyed." % non_string_columns,
)

# --- DQ-16 - region value 'Rhone Alpes' -------------------------------------
# BUSINESS RULE BR-CUSTOMER-004 (Application section) + DECISION HV-02 / R-01.
# The value must be PRESERVED unchanged, reported, and submitted to human
# validation. The normalization to 'Auvergne-Rhone-Alpes' must NOT be applied
# automatically. The region must never be derived from city or postal_code, and
# no geographic reference dataset may be introduced (DQ-17 is WITHDRAWN).
dq16_df = df_bronze.filter(F.col("region") == F.lit("Rhone Alpes")).select(
    "customer_id", "city", "postal_code", "region"
)
dq16_rows = dq16_df.count()
record_dq(
    "DQ-16",
    "HIGH",
    "PASS" if dq16_rows == 0 else "FAIL",
    dq16_rows,
    "No occurrence of the non-referenced region value 'Rhone Alpes'."
    if dq16_rows == 0
    else "%d row(s) carry the non-referenced region value 'Rhone Alpes'. "
    "All occurrences are PRESERVED unchanged and require HUMAN "
    "VALIDATION for this batch (DECISION HV-02 / R-01). No automatic "
    "normalization is permitted." % dq16_rows,
)
if dq16_rows:
    logger.error(
        "HUMAN VALIDATION REQUIRED | batch_id=%s | DQ-16 | %d record(s)",
        BATCH_ID,
        dq16_rows,
    )
    show_df(dq16_df.orderBy("customer_id"))

# --- DQ-21 - columns outside the trim scope ---------------------------------
# OBSERVATION / drift monitoring. customer_id and postal_code are ABSENT from
# the BR-CUSTOMER-002 trim list - gap accepted and deferred by DECISION HV-06.
# REPORTING ONLY: no trim may be applied. Extending the trim would be an
# undocumented transformation, and whitespace on customer_id would additionally
# corrupt the DQ-03 key comparison.
dq21_customer_id = count_where(df_bronze, has_outer_whitespace("customer_id"))
dq21_postal_code = count_where(df_bronze, has_outer_whitespace("postal_code"))
dq21_rows = dq21_customer_id + dq21_postal_code
record_dq(
    "DQ-21",
    "LOW",
    "PASS" if dq21_rows == 0 else "FAIL",
    dq21_rows,
    "No whitespace on customer_id or postal_code."
    if dq21_rows == 0
    else "Whitespace detected on customer_id (%d row(s)) and postal_code "
    "(%d row(s)). REPORTING ONLY - no trim may be applied to these "
    "columns. Whitespace on customer_id corrupts the DQ-03 key "
    "comparison and must be escalated."
    % (dq21_customer_id, dq21_postal_code),
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 8. Write to `bronze_customers`
# 
# | Parameter | Value | Source |
# |---|---|---|
# | Format | Delta | STANDARD `bronze.storage_format` |
# | Mode | `overwrite` | DECISION HV-05 - `load_mode: full_refresh` |
# | Schema evolution | Disabled | A schema change must surface through DQ-01 and be escalated, not absorbed |
# | Partitioning | None | 508 rows, no partition key declared in the contract or the standards |
# | Append / MERGE | Forbidden | HV-05 - would produce more than one `_batch_id` and fail DQ-25 |
# 
# The overwrite replaces a **full snapshot** by the next full snapshot. This is
# the authorised full-refresh mechanism of HV-05; it is not a row-level deletion
# and therefore does not engage STANDARD `forbidden_actions.delete_data`.
# 
# At this point DQ-01 has passed. No other Data Quality finding blocks the write
# (DECISION B-04).

# CELL ********************

# =============================================================================
# Write - Delta, full refresh
# =============================================================================
logger.info(
    "Writing %d row(s) to %s | format=delta | mode=overwrite | batch_id=%s",
    bronze_candidate_count,
    TARGET_TABLE,
    BATCH_ID,
)

try:
    (
        df_bronze.write
        .format("delta")
        .mode("overwrite")
        # No mergeSchema and no overwriteSchema on purpose: a structural change
        # must be surfaced by DQ-01 and escalated, never silently absorbed.
        .saveAsTable(TARGET_TABLE)
    )
except Exception:
    # Technical failure - not a Data Quality finding. It must abort the run.
    logger.exception(
        "Technical failure while writing %s. batch_id=%s", TARGET_TABLE, BATCH_ID
    )
    raise

logger.info("Write completed for %s", TARGET_TABLE)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 9. Post-write Data Quality controls
# 
# | Control | Subject | Severity |
# |---|---|---|
# | DQ-22 | Bronze / source row count reconciliation | HIGH |
# | DQ-23 | Technical columns present, typed and populated | HIGH |
# | DQ-25 | Full refresh integrity - exactly one `_batch_id` | HIGH |
# 
# DQ-25 is **report only**: a residual batch must never be deleted from the table
# by this notebook (STANDARD `forbidden_actions.delete_data`).

# CELL ********************

# =============================================================================
# Post-write Data Quality controls - read back from the written table
# =============================================================================
try:
    df_written = spark.table(TARGET_TABLE)
    written_row_count = df_written.count()
except Exception:
    logger.exception("Technical failure while reading back %s", TARGET_TABLE)
    raise

# --- DQ-22 - Bronze / source row count reconciliation ------------------------
# STANDARD architecture.layers.bronze.preserve_source_data + DECISION HV-05.
row_count_delta = written_row_count - source_data_row_count
record_dq(
    "DQ-22",
    "HIGH",
    "PASS" if row_count_delta == 0 else "FAIL",
    abs(row_count_delta),
    "source_data_rows=%d written_rows=%d delta=0. No row added, filtered or "
    "carried over from a previous run."
    % (source_data_row_count, written_row_count)
    if row_count_delta == 0
    else "source_data_rows=%d written_rows=%d delta=%d. Bronze did not "
    "preserve the source data, or the full refresh did not replace the "
    "previous content. Every downstream control is invalidated."
    % (source_data_row_count, written_row_count, row_count_delta),
)

# --- DQ-23 - Bronze technical columns ---------------------------------------
# STANDARD bronze.technical_columns.
written_types = dict(df_written.dtypes)
expected_technical_types = {
    "_source_file": "string",
    "_ingestion_timestamp": "timestamp",
    "_batch_id": "string",
}

missing_technical = [c for c in TECHNICAL_COLUMNS if c not in written_types]
wrong_type_technical = {
    name: written_types[name]
    for name, expected in expected_technical_types.items()
    if name in written_types and written_types[name] != expected
}
null_technical = {}
for name in TECHNICAL_COLUMNS:
    if name in written_types:
        null_count = df_written.filter(F.col(name).isNull()).count()
        if null_count:
            null_technical[name] = null_count
# input_file_name() returns an empty string when it cannot be resolved.
empty_source_file = (
    df_written.filter(F.col("_source_file") == F.lit("")).count()
    if "_source_file" in written_types
    else 0
)

dq23_failed = bool(
    missing_technical or wrong_type_technical or null_technical or empty_source_file
)
record_dq(
    "DQ-23",
    "HIGH",
    "FAIL" if dq23_failed else "PASS",
    sum(null_technical.values()) + empty_source_file + len(missing_technical),
    "The 3 technical columns are present, correctly typed and populated on "
    "every row."
    if not dq23_failed
    else "Technical column defect | missing=%s wrong_type=%s null_counts=%s "
    "empty_source_file=%d. Without _batch_id no Data Quality report can "
    "be attributed to a batch and DQ-22 becomes unverifiable."
    % (
        missing_technical,
        wrong_type_technical,
        null_technical,
        empty_source_file,
    ),
)

# --- DQ-25 - Full refresh integrity -----------------------------------------
# DECISION HV-05. Report only: no batch may be deleted from the table
# (STANDARD forbidden_actions.delete_data).
distinct_batches = [
    r["_batch_id"] for r in df_written.select("_batch_id").distinct().collect()
]
dq25_ok = distinct_batches == [BATCH_ID]
record_dq(
    "DQ-25",
    "HIGH",
    "PASS" if dq25_ok else "FAIL",
    0 if dq25_ok else len(distinct_batches),
    "Exactly one _batch_id in %s: %s. The full refresh replaced the previous "
    "content entirely." % (TARGET_TABLE, BATCH_ID)
    if dq25_ok
    else "%d distinct _batch_id value(s) found in %s: %s. Expected exactly "
    "one (%s). A residual batch means the overwrite did not replace the "
    "previous content. REPORT ONLY - no batch is deleted by this "
    "notebook; escalate to a human."
    % (len(distinct_batches), TARGET_TABLE, distinct_batches, BATCH_ID),
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 10. Structured Data Quality report and batch reconciliation
# 
# DECISION B-03 - notebook output only. **No persistent Data Quality table is
# created.** Persistent Data Quality reporting is explicitly deferred.

# CELL ********************

# =============================================================================
# Structured Data Quality report (DECISION B-03 - notebook output only)
# =============================================================================
DQ_REPORT_SCHEMA = StructType(
    [
        StructField("batch_id", StringType(), False),
        StructField("control_id", StringType(), False),
        StructField("severity", StringType(), False),
        StructField("status", StringType(), False),
        StructField("affected_row_count", LongType(), False),
        StructField("message", StringType(), False),
    ]
)

dq_report_df = spark.createDataFrame(DQ_RESULTS, schema=DQ_REPORT_SCHEMA).orderBy(
    "control_id"
)

logger.info("Data Quality report | batch_id=%s | %d control(s)", BATCH_ID, len(DQ_RESULTS))
show_df(dq_report_df)

# =============================================================================
# Batch reconciliation
# =============================================================================
distinct_customer_id = df_written.select("customer_id").distinct().count()
rows_removed = source_data_row_count - written_row_count

logger.info("=" * 78)
logger.info("Bronze reconciliation | batch_id=%s", BATCH_ID)
logger.info("source physical lines            = %d", source_line_count)
logger.info("source data rows (header excl.)  = %d", source_data_row_count)
logger.info("rows written to %-16s = %d", TARGET_TABLE, written_row_count)
logger.info("rows removed                     = %d", rows_removed)
logger.info("distinct customer_id in Bronze   = %d", distinct_customer_id)
logger.info("duplicate keys preserved         = %d", duplicate_key_count)
logger.info("=" * 78)

# Informational comparison against the profiling baseline recorded in
# generated/customers_data_quality.md for the current source file.
# This is NOT an assertion: a future delivery may legitimately differ.
baseline_observed = {
    "source_data_rows": source_data_row_count,
    "bronze_rows": written_row_count,
    "distinct_customer_id": distinct_customer_id,
}
for key, expected_value in BASELINE.items():
    observed_value = baseline_observed[key]
    logger.info(
        "Baseline check (informational) | %-20s expected=%d observed=%d | %s",
        key,
        expected_value,
        observed_value,
        "match" if expected_value == observed_value else "DIFFERENT - verify the delivery",
    )

# =============================================================================
# Batch verdict
# =============================================================================
failed_controls = [r for r in DQ_RESULTS if r["status"] == "FAIL"]
human_validation_controls = [
    r for r in failed_controls if r["control_id"] in ("DQ-16",)
]

logger.info(
    "Batch verdict | controls=%d | passed=%d | failed=%d | "
    "human_validation_requests=%d",
    len(DQ_RESULTS),
    len(DQ_RESULTS) - len(failed_controls),
    len(failed_controls),
    len(human_validation_controls),
)
for result in failed_controls:
    logger.warning(
        "Reported finding | %s | %s | affected_rows=%d",
        result["control_id"],
        result["severity"],
        result["affected_row_count"],
    )

logger.info(
    "No row was rejected, quarantined or corrected at Bronze level "
    "(STANDARD data_quality.on_failure)."
)

df_bronze.unpersist()
logger.info("Bronze ingestion finished | batch_id=%s", BATCH_ID)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
