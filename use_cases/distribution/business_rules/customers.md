# Customers - Business Rules

## Purpose

This document defines the business transformation rules applicable
to the Customers entity when building the Silver layer.

---

## BR-CUSTOMER-001 - Customer uniqueness

A customer must be uniquely identified by `customer_id`.

If duplicate `customer_id` values are detected, they must be reported.

### Survivorship

Survivorship is evaluated AFTER the text normalization defined in
BR-CUSTOMER-002.

The comparison covers the business attributes only:

- customer_name
- customer_type
- city
- postal_code
- region
- country
- created_date

Technical columns are excluded from the comparison.

Two missing values are considered identical.

Rule:

- If all records sharing the same `customer_id` are strictly identical
  across all business attributes, only one record must be kept.
  The removal must still be reported as a Data Quality issue.

- If records sharing the same `customer_id` contain at least one
  conflicting business value, no survivor may be selected automatically.
  The records must be kept, reported, and submitted to human validation.

The agent must never decide which record survives when a conflict exists.

---

## BR-CUSTOMER-002 - Text normalization

Leading and trailing spaces must be removed from text fields.

This rule applies to:

- customer_name
- customer_type
- city
- region
- country

---

## BR-CUSTOMER-003 - Country normalization

The following values represent the same country:

- `FR`
- `France`

The standard Silver value must be:

`France`

---

## BR-CUSTOMER-004 - Region normalization

The value:

`Rhone Alpes`

corresponds to:

`Auvergne-Rhône-Alpes`

### Application

This normalization must NOT be applied automatically.

Every occurrence of `Rhone Alpes` must be:

- left unchanged - the source `region` value is preserved;
- reported as a Data Quality issue;
- submitted to human validation.

The correct region must never be derived automatically from `city`
or `postal_code`.

No geographic validation must be performed and no geographic
reference dataset must be introduced.

Missing region values must remain NULL.

---

## BR-CUSTOMER-005 - City

Missing city values must remain NULL.

No value must be invented to replace a missing city.

---

## BR-CUSTOMER-006 - Customer type

`customer_type` must contain one of the following values:

- B2B
- B2C

Any other value must be reported as a Data Quality issue.

---

## BR-CUSTOMER-007 - Creation date

`created_date` must be converted to a valid date.

If the value cannot be converted, the record must be reported
as a Data Quality issue.

No invalid date correction may be invented by the agent.

---

## BR-CUSTOMER-008 - City casing

The casing of `city` must not be normalized automatically.

Casing inconsistencies - several distinct representations of the
same city - must be reported as a Data Quality issue.

No `city` value must be modified beyond the trim defined in
BR-CUSTOMER-002.