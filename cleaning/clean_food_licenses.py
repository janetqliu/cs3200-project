"""
Clean Boston ISD active food establishment licenses.

Usage:
    python clean_food_licenses.py [input.csv] [output.csv]

Defaults: food_establishment_licenses.csv -> food_establishment_licenses_clean.csv
"""

import re
import sys
import numpy as np
import pandas as pd

IN_PATH = sys.argv[1] if len(sys.argv) > 1 else "food_establishment_licenses.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "food_establishment_licenses_clean.csv"

# Boston zip codes, from the 311 data dictionary
BOSTON_ZIPS = {
    "02132", "02116", "02163", "02135", "02134", "02114", "02133", "02122", "02205",
    "02199", "02118", "02110", "02128", "02125", "02124", "02126", "02113", "02129",
    "02136", "02109", "02108", "02210", "02203", "02111", "02120", "02131", "02115",
    "02130", "02467", "02215", "02127", "02119", "02121",
}
LAT_RANGE = (42.22, 42.41)
LON_RANGE = (-71.20, -70.98)

CITY_FIXES = {
    "Downtown/Financial District": "Financial District",
}


def log(msg):
    print(f"  - {msg}")


def key(s):
    """Uppercase, alphanumerics only, single spaces: for fuzzy joins to other files."""
    return (
        s.fillna("").str.upper()
         .str.replace(r"[^A-Z0-9 ]", " ", regex=True)
         .str.replace(r"\s+", " ", regex=True).str.strip()
         .replace("", pd.NA)
    )


def format_phone(p):
    if pd.isna(p) or len(p) != 10:
        return pd.NA
    return f"({p[:3]}) {p[3:6]}-{p[6:]}"


def main():
    # Read as text so ZIPs keep leading zeros and phones/IDs don't become floats
    df = pd.read_csv(IN_PATH, dtype=str, keep_default_na=False)
    print(f"Loaded {len(df):,} rows x {df.shape[1]} cols from {IN_PATH}")

    # ---------- Basic tidying ----------
    df = df.apply(lambda s: s.str.strip().str.replace(r"\s{2,}", " ", regex=True))
    df = df.replace("", pd.NA)

    exact_dupes = df.duplicated().sum()
    df = df.drop_duplicates()
    log(f"exact duplicate rows dropped: {exact_dupes}")

    df = df.rename(columns={
        "businessname": "business_name",
        "dbaname": "dba_name",
        "licstatus": "license_status",
        "licensecat": "license_category",
        "descript": "license_description",
        "license_add_dt_tm": "license_added",
        "dayphn_cleaned": "phone_raw",
        "zip": "zip_code",
    })

    # ---------- Neighborhood (city column) ----------
    # Mixed case ("BOSTON" vs "Boston") and stray trailing slashes ("Brighton/")
    before = df["city"].nunique()
    df["city"] = df["city"].str.rstrip("/").str.strip().str.title().replace(CITY_FIXES)
    log(f"city values standardized: {before} -> {df['city'].nunique()} distinct")

    # ---------- Address ----------
    # ISD addresses have no street suffix ("1321 Boylston"); split number from street.
    parts = df["address"].str.extract(r"^(?P<street_number>\d+(?:-\d+)?[A-Z]?)\s+(?P<street_name>.+)$")
    df["street_number"] = parts["street_number"]
    df["street_name"] = parts["street_name"].str.title()
    log(f"missing address: {df['address'].isna().sum()}")

    # ---------- ZIP ----------
    df["zip_code"] = df["zip_code"].str.zfill(5)
    df["zip_in_boston"] = df["zip_code"].isin(BOSTON_ZIPS).astype("boolean")
    df.loc[df["zip_code"].isna(), "zip_in_boston"] = pd.NA
    log(f"ZIPs not on Boston list: {(df['zip_in_boston'] == False).sum()}, missing: {df['zip_code'].isna().sum()}")

    # ---------- Phone ----------
    valid = df["phone_raw"].str.fullmatch(r"\d{10}", na=False)
    log(f"phones nulled (placeholder '0', 7-digit without area code, etc.): {(df['phone_raw'].notna() & ~valid).sum()}")
    df["phone"] = df["phone_raw"].where(valid).apply(format_phone)

    # ---------- Dates ----------
    df["license_added"] = pd.to_datetime(df["license_added"], utc=True, format="ISO8601", errors="coerce")
    df["license_added_year"] = df["license_added"].dt.year.astype("Int64")

    # ---------- Coordinates ----------
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    oob = df["latitude"].notna() & ~(
        df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE)
    )
    df.loc[oob, ["latitude", "longitude"]] = np.nan
    log(f"coordinates outside Boston nulled: {oob.sum()}, missing overall: {df['latitude'].isna().sum()}")

    # ---------- Keys & flags ----------
    df["property_id"] = pd.to_numeric(df["property_id"], errors="coerce").astype("Int64")
    df["is_takeout"] = df["license_category"].eq("FT")
    # NOTE: in this file business_name is the public-facing name and dba_name is
    # usually the owning entity (e.g., 'HSI MCA BOS FB LLC', 'Aramark Corporation'),
    # the reverse of the Licensing Board file. So match on business_name.
    df["name_key"] = key(df["business_name"])
    df["address_key"] = key(df["address"])

    # No license number in this file, so give each row a stable surrogate ID.
    df = df.sort_values(["business_name", "address", "license_added"]).reset_index(drop=True)
    df.insert(0, "record_id", range(1, len(df) + 1))

    # Same business at the same address with more than one license
    # (e.g., an FS and an FT, or a renewal issued under a new record)
    grp = df.groupby(["name_key", "address_key"], dropna=False)["record_id"].transform("size")
    df["licenses_at_site"] = grp
    log(f"rows sharing business + address with another license: {(grp > 1).sum()}")

    # ---------- Export ----------
    cols = [
        "record_id", "business_name", "dba_name", "license_status", "license_category",
        "license_description", "is_takeout", "license_added", "license_added_year",
        "address", "street_number", "street_name", "city", "state", "zip_code", "zip_in_boston",
        "property_id", "latitude", "longitude", "phone", "phone_raw",
        "name_key", "address_key", "licenses_at_site",
    ]
    df = df[cols]
    df.to_csv(OUT_PATH, index=False, date_format="%Y-%m-%d %H:%M:%S")
    print(f"Wrote {len(df):,} rows x {df.shape[1]} cols to {OUT_PATH}")


if __name__ == "__main__":
    main()