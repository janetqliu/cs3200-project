"""
Clean Boston 311 service request data (new system, BCS- case IDs).

Usage:
    python clean_service_requests.py [input.csv] [output.csv]

Defaults: service_requests.csv -> boston_311_service_requests_clean.csv
"""

import sys
import numpy as np
import pandas as pd

IN_PATH = sys.argv[1] if len(sys.argv) > 1 else "service_requests.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "boston_311_service_requests_clean.csv"

# Boston zip codes, from the 311 data dictionary
BOSTON_ZIPS = {
    "02132", "02116", "02163", "02135", "02134", "02114", "02133", "02122", "02205",
    "02199", "02118", "02110", "02128", "02125", "02124", "02126", "02113", "02129",
    "02136", "02109", "02108", "02210", "02203", "02111", "02120", "02131", "02115",
    "02130", "02467", "02215", "02127", "02119", "02121",
}

# Generous bounding box around the City of Boston
LAT_RANGE = (42.22, 42.41)
LON_RANGE = (-71.20, -70.98)

DATE_COLS = ["open_date", "close_date", "target_close_date"]


def log(msg):
    print(f"  - {msg}")


def main():
    # ---------- Load ----------
    # Read everything as text so zips/wards/precincts keep leading zeros.
    df = pd.read_csv(IN_PATH, dtype=str, keep_default_na=False)
    print(f"Loaded {len(df):,} rows x {df.shape[1]} cols from {IN_PATH}")

    # ---------- Basic tidying ----------
    df = df.apply(lambda s: s.str.strip())
    df = df.replace("", pd.NA)

    dupes = df.duplicated(subset="case_id").sum()
    df = df.drop_duplicates(subset="case_id")
    log(f"dropped {dupes} duplicate case_ids")

    empty_cols = [c for c in df.columns if df[c].isna().all()]
    df = df.drop(columns=empty_cols)
    log(f"dropped all-empty columns: {empty_cols}")

    # ---------- Dates ----------
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601", errors="coerce")
    bad_order = (df["close_date"] < df["open_date"]).sum()
    if bad_order:
        df.loc[df["close_date"] < df["open_date"], "close_date"] = pd.NaT
    log(f"close_date before open_date (nulled): {bad_order}")

    # ---------- Categorical cleanup ----------
    # 'Resolved successfully' is a duplicate label for 'Resolved'
    n = (df["closure_reason"] == "Resolved successfully").sum()
    df["closure_reason"] = df["closure_reason"].replace("Resolved successfully", "Resolved")
    log(f"closure_reason 'Resolved successfully' -> 'Resolved': {n}")

    # service_name is missing in a couple rows where case_topic is present
    n = (df["service_name"].isna() & df["case_topic"].notna()).sum()
    df["service_name"] = df["service_name"].fillna(df["case_topic"])
    log(f"service_name filled from case_topic: {n}")

    # ---------- Geographic codes ----------
    n = (df["zip_code"].str.len() == 4).sum()
    df["zip_code"] = df["zip_code"].str.zfill(5)
    log(f"zip_code restored leading zero: {n}")
    df["zip_in_boston"] = df["zip_code"].isin(BOSTON_ZIPS).astype("boolean")
    df.loc[df["zip_code"].isna(), "zip_in_boston"] = pd.NA

    for c in ["ward", "precinct"]:
        df[c] = df[c].str.zfill(2)
    for c in ["city_council_district", "fire_district"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # ---------- Coordinates ----------
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    out_of_bounds = (
        df["latitude"].notna()
        & ~(df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE))
    )
    df.loc[out_of_bounds, ["latitude", "longitude"]] = np.nan
    log(f"coordinates outside Boston (nulled): {out_of_bounds.sum()}")

    # ---------- Derived fields ----------
    df["is_closed"] = df["case_status"].eq("Closed")
    df["is_intersection"] = df["street_name"].str.contains("&", na=False)

    df["hours_to_close"] = (
        (df["close_date"] - df["open_date"]).dt.total_seconds() / 3600
    ).round(2)
    df["sla_hours"] = (
        (df["target_close_date"] - df["open_date"]).dt.total_seconds() / 3600
    ).round(2)

    # on_time is a live flag for open cases ("not overdue yet" as of export),
    # so only trust it as a final outcome for closed cases.
    df["on_time_final"] = df["on_time"].where(df["is_closed"])

    # Sanity check: does on_time agree with close vs. target dates for closed cases?
    closed = df[df["is_closed"] & df["target_close_date"].notna()]
    recomputed = np.where(closed["close_date"] <= closed["target_close_date"], "ONTIME", "OVERDUE")
    mismatch = (recomputed != closed["on_time"]).sum()
    log(f"closed cases where on_time disagrees with dates: {mismatch:,} (left as-is)")

    local = df["open_date"].dt.tz_convert("America/New_York")
    df["open_date_local"] = local.dt.tz_localize(None)
    df["open_year_month"] = local.dt.strftime("%Y-%m")
    df["open_weekday"] = local.dt.day_name()
    df["open_hour_local"] = local.dt.hour

    # ---------- Order & export ----------
    order = [
        "case_id", "case_status", "is_closed",
        "open_date", "open_date_local", "open_year_month", "open_weekday", "open_hour_local",
        "target_close_date", "close_date", "sla_hours", "hours_to_close",
        "on_time", "on_time_final", "closure_reason", "closure_comments",
        "case_topic", "service_name", "assigned_department", "assigned_team", "report_source",
        "full_address", "street_number", "street_name", "is_intersection",
        "zip_code", "zip_in_boston", "neighborhood", "public_works_district",
        "city_council_district", "fire_district", "police_district", "ward", "precinct",
        "latitude", "longitude",
    ]
    df = df[order + [c for c in df.columns if c not in order]]
    df = df.sort_values("open_date").reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False, date_format="%Y-%m-%dT%H:%M:%S%z")
    print(f"Wrote {len(df):,} rows x {df.shape[1]} cols to {OUT_PATH}")


if __name__ == "__main__":
    main()