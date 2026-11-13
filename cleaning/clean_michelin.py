"""
Clean the Michelin Guide data and keep only restaurants in Boston, MA.

Usage:
    python clean_michelin_boston.py [input.csv] [output.csv]
"""

import re
import sys
import pandas as pd

IN_PATH = sys.argv[1] if len(sys.argv) > 1 else "michelin_my_maps.csv"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "boston_michelin_restaurants.csv"

# Boston zip codes, from the 311 data dictionary
BOSTON_ZIPS = {
    "02132", "02116", "02163", "02135", "02134", "02114", "02133", "02122", "02205",
    "02199", "02118", "02110", "02128", "02125", "02124", "02126", "02113", "02129",
    "02136", "02109", "02108", "02210", "02203", "02111", "02120", "02131", "02115",
    "02130", "02467", "02215", "02127", "02119", "02121",
}
LAT_RANGE = (42.22, 42.41)
LON_RANGE = (-71.20, -70.98)

STARS = {"1 Star": 1, "2 Stars": 2, "3 Stars": 3}


def to_snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def split_address(addr):
    """'605 Tremont St., Boston, MA, 02118, USA' -> ('605 Tremont St.', '02118')"""
    parts = [p.strip() for p in str(addr).split(",")]
    zip_code = next((p for p in parts if re.fullmatch(r"\d{5}", p)), None)
    # Street is everything before the city ("Boston"), e.g. '63 Salem St., #1'
    street = ", ".join(parts[: parts.index("Boston")]) if "Boston" in parts else parts[0]
    return street, zip_code


def format_phone(p):
    """'+16175364300' -> '(617) 536-4300'"""
    digits = re.sub(r"\D", "", str(p))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return pd.NA
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def main():
    # dtype=str keeps phone numbers intact (otherwise they load as floats)
    df = pd.read_csv(IN_PATH, dtype=str)
    print(f"Loaded {len(df):,} rows from {IN_PATH}")

    df.columns = [to_snake(c) for c in df.columns]
    df = df.apply(lambda s: s.str.strip()).replace("", pd.NA)

    # ---------- Filter to Boston, MA ----------
    loc = df["location"].str.split(",", expand=True).apply(lambda s: s.str.strip())
    df["city"], df["state"], df["country"] = loc[0], loc[1], loc[2]
    df = df[(df["city"] == "Boston") & (df["state"] == "MA") & (df["country"] == "USA")].copy()
    print(f"  kept {len(df)} Boston, MA restaurants")

    # ---------- Address ----------
    parsed = df["address"].apply(split_address)
    df["street_address"] = parsed.str[0]
    df["zip_code"] = parsed.str[1]

    # ---------- Numeric / categorical fields ----------
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["price_level"] = df["price"].str.count(r"\$").astype("Int64")  # $ -> 1 ... $$$$ -> 4
    df["stars"] = df["award"].map(STARS).fillna(0).astype(int)
    df["is_bib_gourmand"] = df["award"].eq("Bib Gourmand")
    df["green_star"] = df["green_star"].eq("1")
    df["phone"] = df["phone_number"].apply(format_phone)

    # Facilities: comma list -> '; ' list (commas are ambiguous inside CSV cells)
    df["facilities"] = (
        df["facilities_and_services"].str.split(",")
        .apply(lambda xs: "; ".join(x.strip() for x in xs) if isinstance(xs, list) else pd.NA)
    )

    # Michelin slug, handy as a stable ID
    df["michelin_id"] = df["url"].str.extract(r"/restaurant/([^/?#]+)")[0]

    # ---------- Validation ----------
    assert df["michelin_id"].is_unique, "duplicate Michelin restaurant IDs"
    bad_zip = ~df["zip_code"].isin(BOSTON_ZIPS)
    bad_xy = ~(df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE))
    if bad_zip.any():
        print(f"  WARNING: {bad_zip.sum()} rows with a non-Boston ZIP: {df.loc[bad_zip, 'name'].tolist()}")
    if bad_xy.any():
        print(f"  WARNING: {bad_xy.sum()} rows with coordinates outside Boston: {df.loc[bad_xy, 'name'].tolist()}")

    # ---------- Export ----------
    out = df[[
        "michelin_id", "name", "street_address", "city", "state", "zip_code",
        "latitude", "longitude", "cuisine", "price", "price_level",
        "award", "stars", "is_bib_gourmand", "green_star",
        "facilities", "phone", "website_url", "url", "description",
    ]].rename(columns={"url": "michelin_url"})
    out = out.sort_values(["stars", "is_bib_gourmand", "name"], ascending=[False, False, True])

    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows x {out.shape[1]} cols to {OUT_PATH}")


if __name__ == "__main__":
    main()