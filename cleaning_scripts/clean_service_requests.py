"""Cleans the Boston food inspection CSV and splits it into six linked tables.

Usage: python clean_normalize.py [input.csv] [output_dir]
"""
 
import re
import sys
from pathlib import Path
 
import numpy as np
import pandas as pd
 
INPUT_CSV = "/mnt/user-data/uploads/tmpmkgr2m95.csv"
OUTPUT_DIR = "/mnt/user-data/outputs/normalized"
 
 

def tidy_text(s: pd.Series) -> pd.Series:
    """Collapse repeated whitespace, trim ends, and turn empty strings into NaN."""
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s.replace("", np.nan)
 
 
def make_name_key(s: pd.Series) -> pd.Series:
    """Lowercase, letters/numbers only. Handy for grouping 'Dunkin Donuts' / "DUNKIN' DONUTS"."""
    return s.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
 
 
def clean_zip(s: pd.Series) -> pd.Series:
    """Return a 5-digit zip string. Fixes '2108' -> '02108' and '02108-1234' -> '02108'."""
    z = s.str.extract(r"^(\d{4,5})")[0]
    return z.str.zfill(5)
 
 
def clean_city(s: pd.Series) -> pd.Series:
    """Remove stray trailing slashes ('ROXBURY/' -> 'ROXBURY') and fix one truncated value."""
    s = s.str.upper().str.replace(r"[/\s]+$", "", regex=True)
    return s.replace({"ROXBURY CROSSIN": "ROXBURY CROSSING"})
 
# main function
def main(input_csv: str, output_dir: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
 
    # Read everything as text first so nothing gets silently altered
    # (e.g. a zip code '02108' would otherwise become the number 2108).
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    print(f"Loaded {len(df):,} rows, {df.shape[1]} columns")
    log = {}
 
    for col in df.columns:
        df[col] = tidy_text(df[col])
 
    is_test = df["licstatus"].eq("Deleted")
    log["test/deleted-license rows dropped"] = int(is_test.sum())
    df = df[~is_test].copy()
 
    df["state"] = df["state"].str.upper()
    df["zip"] = clean_zip(df["zip"])
    df["city"] = clean_city(df["city"])
 
    df["property_id"] = df["property_id"].replace("0", np.nan)
 
    bad_level = ~df["viol_level"].isin(["*", "**", "***"]) & df["viol_level"].notna()
    log["invalid viol_level values set to missing"] = int(bad_level.sum())
    df.loc[bad_level, "viol_level"] = np.nan
 
    for col in ["issdttm", "expdttm", "resultdttm", "violdttm", "status_date"]:
        df[col] = pd.to_datetime(df[col], utc=True, format="ISO8601", errors="coerce")
 
    coords = df["location"].str.extract(r"\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")
    df["latitude"] = pd.to_numeric(coords[0])
    df["longitude"] = pd.to_numeric(coords[1])
  
    license_categories = (
        df[["licensecat", "descript"]]
        .drop_duplicates()
        .rename(columns={"licensecat": "category_code", "descript": "description"})
        .sort_values("category_code")
        .reset_index(drop=True)
    )
 
    loc_cols = ["address", "city", "state", "zip", "property_id", "latitude", "longitude"]
    locations = df[loc_cols].drop_duplicates().reset_index(drop=True)
    locations.insert(0, "location_id", np.arange(1, len(locations) + 1))
    df = df.merge(locations, on=loc_cols, how="left")  # attach location_id (NaN keys match)
 
    licenses = (
        df[["licenseno", "businessname", "dbaname", "legalowner", "namelast", "namefirst",
            "issdttm", "expdttm", "licstatus", "licensecat", "location_id"]]
        .drop_duplicates(subset="licenseno")
        .rename(columns={
            "businessname": "business_name",
            "dbaname": "dba_name",
            "legalowner": "legal_owner",
            "namelast": "owner_last",
            "namefirst": "owner_first",
            "issdttm": "issued_at",
            "expdttm": "expires_at",
            "licstatus": "license_status",
            "licensecat": "category_code",
        })
        .reset_index(drop=True)
    )
    licenses["business_name_key"] = make_name_key(licenses["business_name"])
 
    insp_keys = ["licenseno", "resultdttm", "result"]
    df["inspection_id"] = df.groupby(insp_keys, dropna=False).ngroup() + 1
    inspections = (
        df[["inspection_id"] + insp_keys]
        .drop_duplicates("inspection_id")
        .rename(columns={"resultdttm": "inspected_at"})
        .sort_values("inspection_id")
        .reset_index(drop=True)
    )
 
    has_viol = df["violation"].notna()
    violation_types = (
        df.loc[has_viol, ["violation", "viol_level", "violdesc"]]
        .drop_duplicates(subset="violation")
        .rename(columns={"violation": "violation_code", "viol_level": "severity_level",
                         "violdesc": "description"})
        .sort_values("violation_code")
        .reset_index(drop=True)
    )
 
    iv_cols = ["inspection_id", "violation", "viol_status", "violdttm", "status_date", "comments"]
    inspection_violations = (
        df.loc[has_viol, iv_cols]
        .rename(columns={"violation": "violation_code", "viol_status": "violation_status",
                         "violdttm": "violation_at", "status_date": "status_changed_at"})
    )
    before = len(inspection_violations)
    inspection_violations = inspection_violations.drop_duplicates().reset_index(drop=True)
    log["exact duplicate violation rows removed"] = before - len(inspection_violations)
    inspection_violations.insert(0, "violation_id", np.arange(1, len(inspection_violations) + 1))
 
    assert licenses["licenseno"].is_unique
    assert inspections["licenseno"].isin(licenses["licenseno"]).all()
    assert inspection_violations["inspection_id"].isin(inspections["inspection_id"]).all()
    assert inspection_violations["violation_code"].isin(violation_types["violation_code"]).all()
    assert licenses["category_code"].isin(license_categories["category_code"]).all()
    assert licenses["location_id"].isin(locations["location_id"]).all()
 
    tables = {
        "license_categories": license_categories,
        "locations": locations,
        "licenses": licenses,
        "inspections": inspections,
        "violation_types": violation_types,
        "inspection_violations": inspection_violations,
    }
    print()
    for name, t in tables.items():
        t.to_csv(out / f"{name}.csv", index=False)
        print(f"  {name:<22} {len(t):>9,} rows  x {t.shape[1]} cols")
 
    print("\nCleaning log:")
    for k, v in log.items():
        print(f"  - {k}: {v:,}")
    print(f"\nSaved to: {out}")
 
 
if __name__ == "__main__":
    in_path = sys.argv[1] if len(sys.argv) > 1 else INPUT_CSV
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_DIR
    main(in_path, out_path)
 