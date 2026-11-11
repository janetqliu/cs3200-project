# CS3200 Project | Janet, Layla, Alexis, Ricky

This project contains six data files: four Boston city datasets (licensing, food inspections, 311), one global Michelin Guide dataset, and two data dictionaries. Profiled November 2026.
- `cleaning_scripts/` contains python scripts for cleaning the raw data files.
- `cleaned_data.zip` contains the cleaned datasets:

| File | Rows | Cols | Grain (one row =) | Coverage |
|---|---|---|---|---|
| `service_requests.csv` | 79,999 | 36 | one 311 case | 2025-08-01 → 2026-10-30 |


---

## service_requests.csv
Boston 311 service requests from the **new 311 system** (`BCS-` case IDs), cleaned from the raw `service_requests.csv` export. The PDF dictionary defines the original columns, and the derived columns are described below. The row count of exactly 79,999 suggests the raw export was capped or sampled, so this is not the full dataset.

**Columns (in file order):**
- **Status:** `case_id` (unique), `case_status`, `is_closed`.
- **Timing:** `open_date`, `target_close_date`, `close_date` (ISO 8601, UTC); `open_date_local`, `open_year_month`, `open_weekday`, `open_hour_local` (Boston time); `sla_hours` (target minus open); `hours_to_close` (close minus open, closed cases only).
- **Outcome:** `on_time` (raw flag), `on_time_final` (same flag, but only for closed cases), `closure_reason`, `closure_comments`.
- **What/who:** `case_topic`, `service_name`, `assigned_department`, `assigned_team`, `report_source` (BOS311 app, Call, Email).
- **Where:** `full_address`, `street_number`, `street_name`, `is_intersection`, `zip_code`, `zip_in_boston`, `neighborhood`, `public_works_district`, `city_council_district`, `fire_district`, `police_district`, `ward`, `precinct`, `latitude`, `longitude`.

**Important:**
- Read `zip_code`, `ward`, and `precinct` as strings, or the leading zeros will be removed: `pd.read_csv(path, dtype={"zip_code": str, "ward": str, "precinct": str}, parse_dates=["open_date", "close_date", "target_close_date"])`.
- For open cases, raw `on_time` = "ONTIME" only means "not overdue as of export". Use `on_time_final` for SLA analysis.
- 17 closed cases have an `on_time` value that disagrees with their dates. These were left as-is.
- `case_status` includes values not in the dictionary (Needs Reallocation, Create, Submit, Error). Filter on `is_closed` or `case_status` as needed.
- `zip_in_boston` is False for 56 rows and blank for 507 rows with no ZIP.
- Location fields are per case: the same address can carry different coordinates, ZIPs, or wards across cases, so don't treat address as a key.

**Relationships (see ERD):** (Work in progress)

---

## Joining across files
- Work in progress