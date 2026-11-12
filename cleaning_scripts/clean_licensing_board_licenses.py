"""Cleans the Licensing Board Licenses CSV
Only kept rows with the License 'Common Victualler' which refers to food service 
"""

import re
import sys
import unicodedata
 
import numpy as np
import pandas as pd

FOOD_CATEGORIES = {"Common Victualler"}


def tidy_text(df: pd.DataFrame) -> pd.DataFrame:
    quotes = r'["\u201c\u201d\u2018\u2019]'  # straight and curly double/single quotes
    for col in df.columns:
        df[col] = (
            df[col]
            .str.strip().str.strip('"\u201c\u201d') #remove quotations around entire value
            .str.replace(r"\s+", " ", regex=True)   #remove double space
            .str.strip()                            # remove leading/trailing whitespace
        )
    return df


PLACEHOLDERS = {".", "-", "n/a", "na", "none", "null", "unknown", "tbd"}
 
 
def blank_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df.loc[df[col].str.lower().isin(PLACEHOLDERS), col] = ""
    # A capacity of 0 or coordinates of 0 are nulled.
    df.loc[df["capacity"] == "0", "capacity"] = ""
    no_gps = (pd.to_numeric(df["gpsx"], errors="coerce").fillna(0) == 0) | (
        pd.to_numeric(df["gpsy"], errors="coerce").fillna(0) == 0
    )
    df.loc[no_gps, ["gpsx", "gpsy"]] = ""
    return df

#fixes business names
ENTITY_SUFFIXES = {"llc", "inc", "incorporated", "corp", "corporation", "co",
                   "company", "ltd", "llp", "lp", "pc", "dba"}
 
 
def name_key(name: str) -> str:
    """Normalized name for matching: lowercase, no accents/punctuation,
    '&' -> 'and', no leading 'the', no trailing LLC/Inc/Corp etc."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"['.]", "", s)           
    s = re.sub(r"[^a-z0-9]+", " ", s).split()
    while s and s[-1] in ENTITY_SUFFIXES:
        s.pop()
    if len(s) > 1 and s[0] == "the":
        s.pop(0)
    return " ".join(s)

def clean_phone(series: pd.Series) -> pd.DataFrame:
    parts = series.str.split(r"\s*(?:x|ext\.?)\s*", n=1, regex=True, expand=True)
    parts = parts.reindex(columns=[0, 1]).fillna("")
    digits = parts[0].str.replace(r"\D", "", regex=True)
    digits = digits.where(~((digits.str.len() == 11) & digits.str.startswith("1")),
                          digits.str[1:])
    # Anything that isn't a full 10-digit number is blanked 
    digits = digits.where(digits.str.len() == 10, "")
    ext = parts[1].str.replace(r"\D", "", regex=True).where(digits != "", "")
    return pd.DataFrame({"phone": digits, "ext": ext})

# For liquor licenses
def alcohol_type(license_type: str) -> str:
    t = license_type.upper()
    if "BYOB" in t:
        return "byob"
    if "ALL ALC" in t or "ALL-ALC" in t or "CV7ALN" in t:
        return "all_alcohol"
    if "MALT WINE LIQ" in t or "CV7MWLN" in t:
        return "beer_wine_cordials"   
    if "MALT WINE" in t or "MALT & WINE" in t or "CV7MWN" in t:
        return "beer_wine"
    return "none"

# Maps Boston's abbreviations to USPS standards.
SUFFIXES = {
    "ST": "ST", "STREET": "ST",
    "AV": "AVE", "AVE": "AVE", "AVENUE": "AVE",
    "BL": "BLVD", "BLVD": "BLVD", "BOULEVARD": "BLVD",
    "RD": "RD", "ROAD": "RD",
    "SQ": "SQ", "SQUARE": "SQ",
    "PL": "PL", "PLACE": "PL",
    "DR": "DR", "DRIVE": "DR",
    "PZ": "PLZ", "PLZ": "PLZ", "PLAZA": "PLZ",
    "HW": "HWY", "HWY": "HWY", "HIGHWAY": "HWY",
    "PW": "PKWY", "PKWY": "PKWY", "PARKWAY": "PKWY",
    "WY": "WAY", "WA": "WAY", "WAY": "WAY",
    "WH": "WHRF", "WHARF": "WHRF",
    "LN": "LN", "LANE": "LN",
    "PK": "PARK", "PARK": "PARK",
    "CT": "CT", "COURT": "CT",
    "RO": "ROW", "ROW": "ROW",
    "CIR": "CIR", "CIRCLE": "CIR",
    "AL": "ALY", "ALLEY": "ALY",
    "MA": "MALL", "MALL": "MALL",
    "TER": "TER", "TERRACE": "TER",
}
 
DIRECTIONS = {"N": "N", "S": "S", "E": "E", "W": "W",
              "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
 
 
def standardize_suffix(token: str) -> str:
    return SUFFIXES.get(token.upper().rstrip("."), "")
 
 
# Standardizes addresses 
ADDRESS_RE = re.compile(
    r"^(?P<start>[^\s-]*)-(?P<end>\S*)\s+(?:(?P<dir>[NSEW])\s+)?(?P<rest>.*)$"
)
 
 
def split_address(addr: str) -> dict:
    out = {"street_number": "", "street_number_end": "", "street_direction": "",
           "street_name": "", "street_suffix": "", "address_clean": ""}
    if not addr:
        return out
    m = ADDRESS_RE.match(addr)
    if m:
        start, end = m["start"], m["end"].strip("-")
        direction, rest = m["dir"] or "", m["rest"]
    else:  
        m2 = re.match(r"^(\d+[A-Za-z]?)\s+(.*)$", addr)
        start, end, direction, rest = (m2[1], "", "", m2[2]) if m2 else ("", "", "", addr)
 
    tokens = re.sub(r"\s+", " ", rest).strip().split(" ")
    suffix = standardize_suffix(tokens[-1]) if len(tokens) > 1 else ""
    name_tokens = tokens[:-1] if suffix else tokens
    name = " ".join(name_tokens)
 
    out.update(
        street_number=start.upper(),
        street_number_end=end.upper(),
        street_direction=direction,
        street_name=name,
        street_suffix=suffix,
    )
    out["address_clean"] = " ".join(
        p for p in [start.upper(), direction, name, suffix] if p
    )
    return out





def clean(input_path: str, output_path: str) -> pd.DataFrame:
    # Read everything as text so ZIP codes keep their leading zeros.
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    n_in = len(df)
 
    df = tidy_text(df)
    df = df[df["license_category"].isin(FOOD_CATEGORIES)].drop_duplicates().copy()
    df = blank_placeholders(df)
 
    addr = pd.DataFrame(df["address"].map(split_address).tolist(), index=df.index)
    df = pd.concat([df, addr], axis=1)
 
    for col in ["day_phone", "evening_phone"]:
        ph = clean_phone(df[col])
        df[f"{col}_clean"] = ph["phone"]
        df[f"{col}_ext"] = ph["ext"]
 
    df["display_name"] = df["dba_name"].where(df["dba_name"] != "", df["business_name"])
    df["name_key"] = df["display_name"].map(name_key)
    df["business_name_key"] = df["business_name"].map(name_key)
 
 
    df["alcohol_type"] = df["license_type"].map(alcohol_type)
    df["serves_alcohol"] = df["alcohol_type"].isin(
        ["all_alcohol", "beer_wine", "beer_wine_cordials"])
 
    df.to_csv(output_path, index=False)
 
    #print(f"Input rows:  {n_in:,}")
    #print(f"Output rows: {len(df):,}")
    #print(f"Blank capacity:        {(df['capacity'] == '').sum():,}")
    #print(f"Missing lat/lon:       {df['latitude'].isna().sum():,}")
    #print(f"Addresses w/o suffix:  {(df['street_suffix'] == '').sum():,}")
    #print(f"Unusable day phones:   {((df['day_phone'] != '') & (df['day_phone_clean'] == '')).sum():,}")
    #print("\nAlcohol type:")
    #print(df["alcohol_type"].value_counts().to_string())
    return df
 
 
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python clean_food_service.py input.csv [output.csv]")
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "food_service_only.csv"
    clean(in_path, out_path)
 