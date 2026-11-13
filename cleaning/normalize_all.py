"""
Normalize the cleaned Boston food / licensing / Michelin / 311 data into 3NF
tables with standardized join fields.

Usage:
    python normalize_all.py [input_dir] [output_dir]

Defaults: input_dir='cleaned_data', output_dir='normalized'

Inputs (found by base name; a suffix like '_1' is tolerated, newest wins):
    cleaned_data/food_violations/
        licenses, locations, license_categories, inspections,
        inspection_violations, violation_types   (ISD food inspections)
    cleaned_data/
        food_permits                             (ISD active permits)
    lb_licenses / licensing_board_licenses       (Licensing Board)
    michelin_restaurants
    311_service_requests

Standardization applied everywhere:
    * Addresses parsed by one parser into number / direction / name / USPS
      suffix / unit, and linked to a shared ADDRESSES table. The address key is
      'NUMBER DIR NAME|ZIP' without the suffix, because ISD permit addresses omit it.
    * ZIPs are 5-character strings, linked to a shared ZIP_CODES table.
    * Neighborhoods are title-cased, with slashed variants resolved.
    * Business names get one shared name_key for cross-source matching.
    * Phones are 10 digits; timestamps are 'YYYY-MM-DD HH:MM:SS' UTC; dates are 'YYYY-MM-DD'.
    * Coordinates are WGS84 lat/long, nulled if outside Boston.

3NF notes:
    * Derived columns (flags, keys built from other columns, 24h/raw hour
      duplicates, State Plane x/y) are dropped. The exceptions are name_key /
      business_name_key: they are derived but kept as indexed match keys.
    * Multi-valued cells are split into child tables (LB managers, Michelin facilities).
    * Lookups get their own tables (license types, awards, results, ...).
"""
from __future__ import annotations
import glob
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

IN_DIR = sys.argv[1] if len(sys.argv) > 1 else "cleaned_data"
FOOD_VIOLATIONS_DIR = "food_violations"  # subfolder of IN_DIR
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "normalized"

BOSTON_ZIPS = {
    "02132", "02116", "02163", "02135", "02134", "02114", "02133", "02122", "02205",
    "02199", "02118", "02110", "02128", "02125", "02124", "02126", "02113", "02129",
    "02136", "02109", "02108", "02210", "02203", "02111", "02120", "02131", "02115",
    "02130", "02467", "02215", "02127", "02119", "02121",
}
LAT_RANGE = (42.22, 42.41)
LON_RANGE = (-71.20, -70.98)


# ===========================================================================
# I/O helpers
# ===========================================================================

def find_input(*bases: str, subdir: str = "") -> str:
    """Return the newest file in IN_DIR/subdir matching base.csv or base_<n>.csv."""
    folder = os.path.join(IN_DIR, subdir)
    hits = []
    for base in bases:
        hits += glob.glob(os.path.join(folder, f"{base}.csv"))
        hits += [p for p in glob.glob(os.path.join(folder, f"{base}_*.csv"))
                 if re.fullmatch(rf"{re.escape(base)}_\d+\.csv", os.path.basename(p))]
    if not hits:
        raise FileNotFoundError(f"No input found for {bases} in {folder!r}")
    return max(hits, key=os.path.getmtime)


def read(*bases: str, subdir: str = "", **kw) -> pd.DataFrame:
    path = find_input(*bases, subdir=subdir)
    df = pd.read_csv(path, dtype=str, keep_default_na=False, **kw)
    df = df.apply(lambda s: s.str.strip()).replace("", pd.NA)
    print(f"  read {os.path.relpath(path, IN_DIR)}: {len(df):,} rows")
    return df


TABLES: dict[str, pd.DataFrame] = {}


def emit(name: str, df: pd.DataFrame, pk: list[str] | str | None = None):
    pk = [pk] if isinstance(pk, str) else pk
    if pk:
        dup = df.duplicated(subset=pk).sum()
        if dup:
            raise ValueError(f"{name}: primary key {pk} has {dup} duplicates")
        if df[pk].isna().any().any():
            raise ValueError(f"{name}: primary key {pk} has nulls")
    TABLES[name] = df.reset_index(drop=True)


# ===========================================================================
# Shared standardizers
# ===========================================================================

def std_zip(s: pd.Series) -> pd.Series:
    z = s.astype("string").str.extract(r"(\d{4,5})")[0]
    return z.str.zfill(5)


def std_phone(s: pd.Series) -> pd.Series:
    d = s.astype("string").str.replace(r"\D", "", regex=True)
    d = d.where(~((d.str.len() == 11) & d.str.startswith("1")), d.str[1:])
    return d.where(d.str.match(r"^[2-9]\d{2}[2-9]\d{6}$", na=False))


def std_ts(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s, utc=True, format="mixed", errors="coerce")
    return t.dt.strftime("%Y-%m-%d %H:%M:%S")


def std_date(s: pd.Series) -> pd.Series:
    t = pd.to_datetime(s, format="mixed", errors="coerce")
    return t.dt.strftime("%Y-%m-%d")


def std_bool(s: pd.Series) -> pd.Series:
    return s.astype("string").str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}).astype("boolean")


def std_coords(lat: pd.Series, lon: pd.Series):
    lat = pd.to_numeric(lat, errors="coerce")
    lon = pd.to_numeric(lon, errors="coerce")
    ok = lat.between(*LAT_RANGE) & lon.between(*LON_RANGE)
    return lat.where(ok).round(7), lon.where(ok).round(7)


NEIGHBORHOOD_FIXES = {"Dorchester Center": "Dorchester", "Roxbury Crossing": "Roxbury"}


def std_neighborhood(s: pd.Series) -> pd.Series:
    """'ROXBURY/BOSTON' -> 'Roxbury', 'BOSTON/WEST END' -> 'West End',
    'Brighton/' -> 'Brighton', 'DOWNTOWN/FINANCIAL DISTRICT' -> 'Financial District'."""
    def one(v):
        if pd.isna(v):
            return pd.NA
        parts = [p.strip() for p in str(v).split("/") if p.strip()]
        specific = [p for p in parts if p.upper() != "BOSTON"] or parts
        if not specific:
            return pd.NA
        out = specific[-1].title()
        return NEIGHBORHOOD_FIXES.get(out, out)
    return s.map(one).astype("string")


ENTITY_SUFFIXES = {"llc", "inc", "incorporated", "corp", "corporation", "co",
                   "company", "ltd", "llp", "lp", "pc", "dba"}


def name_key(name) -> str | None:
    """Lowercase, ASCII, '&'->'and', no punctuation, no leading 'the',
    no trailing LLC/Inc/etc. Same function for every source."""
    if pd.isna(name) or not str(name).strip():
        return None
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"['.]", "", s)
    toks = re.sub(r"[^a-z0-9]+", " ", s).split()
    while toks and toks[-1] in ENTITY_SUFFIXES:
        toks.pop()
    if len(toks) > 1 and toks[0] == "the":
        toks.pop(0)
    return " ".join(toks) or None


# ---------------------------------------------------------------------------
# Address parsing
# ---------------------------------------------------------------------------

SUFFIXES = {
    "ST": "ST", "STREET": "ST", "AV": "AVE", "AVE": "AVE", "AVENUE": "AVE",
    "BL": "BLVD", "BLVD": "BLVD", "BOULEVARD": "BLVD", "RD": "RD", "ROAD": "RD",
    "SQ": "SQ", "SQUARE": "SQ", "PL": "PL", "PLACE": "PL", "DR": "DR", "DRIVE": "DR",
    "PZ": "PLZ", "PLZ": "PLZ", "PLAZA": "PLZ", "HW": "HWY", "HWY": "HWY",
    "HIGHWAY": "HWY", "PW": "PKWY", "PKWY": "PKWY", "PARKWAY": "PKWY",
    "WY": "WAY", "WA": "WAY", "WAY": "WAY", "WH": "WHRF", "WHARF": "WHRF",
    "LN": "LN", "LANE": "LN", "PK": "PARK", "PARK": "PARK", "CT": "CT",
    "COURT": "CT", "RO": "ROW", "ROW": "ROW", "CIR": "CIR", "CIRCLE": "CIR",
    "AL": "ALY", "ALLEY": "ALY", "MALL": "MALL", "TER": "TER", "TERRACE": "TER",
    "TPKE": "TPKE", "TURNPIKE": "TPKE", "EXT": "EXT", "HTS": "HTS",
}
DIRECTIONS = {"N": "N", "S": "S", "E": "E", "W": "W",
              "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
UNIT_RE = re.compile(
    r"(?:#\s*|\b(?:UNIT|STE|SUITE|APT|FL|FLOOR|RM|ROOM|SPACE|BLDG)\b\.?\s*)([A-Z0-9-]+)\s*$")
# '122', '300A', '10HF' (half number), '50-58', '749A-755', '100-199-' (LB style)
NUMBER_RE = re.compile(
    r"^(?P<num>\d+[A-Z]{0,2})(?:\s*-\s*(?P<end>\d+[A-Z]{0,2})?)?-?\s+(?P<rest>.+)$")

EMPTY_ADDR = dict(street_number=None, street_number_end=None, street_direction=None,
                  street_name=None, street_suffix=None, unit=None)


def _parse_street(rest: str) -> tuple[str | None, str | None, str | None]:
    """'W BROADWAY' -> ('W', 'BROADWAY', None); 'E ST' -> (None, 'E', 'ST')."""
    toks = rest.split()
    direction = None
    if len(toks) >= 2 and toks[0] in DIRECTIONS:
        after = toks[1:]
        # 'E ST' / 'SOUTH ST' are street names, not directions
        if not (len(after) == 1 and after[0] in SUFFIXES):
            direction, toks = DIRECTIONS[toks[0]], after
    suffix = None
    if len(toks) >= 2 and toks[-1] in SUFFIXES:
        suffix, toks = SUFFIXES[toks[-1]], toks[:-1]
    return direction, " ".join(toks) or None, suffix


def parse_address(raw) -> dict:
    """Parse any source's street address into standardized parts."""
    if pd.isna(raw) or not str(raw).strip():
        return dict(EMPTY_ADDR)
    s = unicodedata.normalize("NFKD", str(raw)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"\([^)]*\)", " ", s)                 # drop '(FHMP)' etc.
    s = s.replace(".", " ").replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()

    # Intersections: 'A ST & B ST' -> name 'A ST & B ST' in sorted order
    if "&" in s:
        sides = []
        for side in s.split("&"):
            d, n, suf = _parse_street(side.strip())
            sides.append(" ".join(p for p in (d, n, suf) if p))
        out = dict(EMPTY_ADDR)
        out["street_name"] = " & ".join(sorted(sides))
        return out

    unit = None
    m = UNIT_RE.search(s)
    if m:
        unit, s = m.group(1), s[: m.start()].strip()

    s = re.sub(r"^-\s*", "", s)                      # LB style '- LOGAN AIRPORT'
    m = NUMBER_RE.match(s)
    if m:
        num, end, rest = m["num"], (m["end"] or None), m["rest"]
    else:
        num, end, rest = None, None, s
    direction, name, suffix = _parse_street(rest)
    return dict(street_number=num, street_number_end=end, street_direction=direction,
                street_name=name, street_suffix=suffix, unit=unit)


class AddressRegistry:
    """Collects parsed addresses from every source and assigns shared IDs."""

    def __init__(self):
        self.rows = []

    @staticmethod
    def key(p: dict, zip_code) -> str | None:
        core = " ".join(x for x in (p["street_number"], p["street_direction"], p["street_name"])
                        if isinstance(x, str) and x)
        if not core:
            return None
        return f"{core}|{zip_code if pd.notna(zip_code) else ''}"

    def link(self, raw: pd.Series, zips: pd.Series, source: str) -> pd.DataFrame:
        """Parse addresses; return per-row address_key, street_number_end, unit."""
        parsed = pd.DataFrame([parse_address(v) for v in raw], index=raw.index)
        parsed["zip_code"] = zips.values
        parsed["address_key"] = [self.key(p, z) for p, z in
                                 zip(parsed.to_dict("records"), parsed["zip_code"])]
        parsed["source"] = source
        self.rows.append(parsed[parsed["address_key"].notna()])
        return parsed[["address_key", "street_number_end", "unit"]]

    def build(self) -> pd.DataFrame:
        a = pd.concat(self.rows, ignore_index=True)
        # Suffix: most common non-null suffix seen for this key across sources
        suffix = (a.dropna(subset=["street_suffix"])
                   .groupby("address_key")["street_suffix"]
                   .agg(lambda s: s.value_counts().idxmax()))
        base = a.drop_duplicates("address_key")[
            ["address_key", "street_number", "street_direction", "street_name", "zip_code"]]
        base = base.merge(suffix.rename("street_suffix"), on="address_key", how="left")
        base = base.sort_values("address_key").reset_index(drop=True)
        base.insert(0, "address_id", np.arange(1, len(base) + 1))
        base["address_std"] = base.apply(
            lambda r: " ".join(x for x in (r.street_number, r.street_direction,
                                           r.street_name, r.street_suffix) if pd.notna(x) and x),
            axis=1)
        return base[["address_id", "address_key", "address_std", "street_number",
                     "street_direction", "street_name", "street_suffix", "zip_code"]]


ADDR = AddressRegistry()


def attach_address(df: pd.DataFrame, raw_col: str, zip_col: str, source: str) -> pd.DataFrame:
    parts = ADDR.link(df[raw_col], df[zip_col], source)
    df = df.copy()
    df["address_key"] = parts["address_key"]
    df["street_number_end"] = parts["street_number_end"]
    df["unit"] = parts["unit"]
    return df


def resolve_address_ids(addresses: pd.DataFrame):
    m = addresses.set_index("address_key")["address_id"]
    for name, t in TABLES.items():
        if "address_key" in t.columns:
            t.insert(t.columns.get_loc("address_key"), "address_id",
                     t["address_key"].map(m).astype("Int64"))
            TABLES[name] = t.drop(columns="address_key")


# ===========================================================================
# ISD food inspections (+ food permits)
# ===========================================================================

INSPECTION_RESULTS = {
    "HE_Pass": ("Pass", "pass"), "Pass": ("Pass", "pass"),
    "PassViol": ("Pass with violations", "pass"), "NoViol": ("No violations", "pass"),
    "HE_Fail": ("Fail", "fail"), "Fail": ("Fail", "fail"), "Failed": ("Fail", "fail"),
    "HE_FailExt": ("Fail - extension granted", "fail"),
    "HE_FAILNOR": ("Fail - no reinspection", "fail"),
    "HE_Filed": ("Filed", "administrative"), "HE_NotReq": ("Not required", "administrative"),
    "HE_Hearing": ("Hearing", "administrative"), "HE_Hold": ("Hold", "administrative"),
    "HE_Misc": ("Miscellaneous", "administrative"),
    "HE_OutBus": ("Out of business", "closure"), "HE_VolClos": ("Voluntary closure", "closure"),
    "HE_Closure": ("Closure", "closure"), "Closed": ("Closure", "closure"),
    "HE_TSOP": ("Temporary suspension of permit", "closure"),
    "DATAERR": ("Data error", "error"),
}
SEVERITY = {"*": ("Minor", 1), "**": ("Major", 2), "***": ("Critical", 3)}


def build_isd():
    print("ISD food inspections")
    cats = read("license_categories", subdir=FOOD_VIOLATIONS_DIR)
    locs = read("locations", subdir=FOOD_VIOLATIONS_DIR)
    lic = read("licenses", subdir=FOOD_VIOLATIONS_DIR)
    insp = read("inspections", subdir=FOOD_VIOLATIONS_DIR)
    vtypes = read("violation_types", subdir=FOOD_VIOLATIONS_DIR)
    iv = read("inspection_violations", subdir=FOOD_VIOLATIONS_DIR)
    permits = read("food_permits")

    emit("license_categories", cats.rename(columns={"description": "category_description"}),
         "category_code")

    # Locations
    locs["zip_code"] = std_zip(locs["zip"])
    locs["neighborhood"] = std_neighborhood(locs["city"])
    locs["latitude"], locs["longitude"] = std_coords(locs["latitude"], locs["longitude"])
    locs["property_id"] = pd.to_numeric(locs["property_id"], errors="coerce").astype("Int64")
    locs["location_id"] = locs["location_id"].astype(int)
    locs = attach_address(locs, "address", "zip_code", "isd_location")
    emit("isd_locations", locs[[
        "location_id", "address_key", "street_number_end", "unit", "neighborhood",
        "zip_code", "property_id", "latitude", "longitude"]], "location_id")

    # Licenses
    lic["issued_at"] = std_ts(lic["issued_at"])
    lic["expires_at"] = std_ts(lic["expires_at"])
    lic["location_id"] = lic["location_id"].astype("Int64")
    lic["name_key"] = lic["business_name"].map(name_key)

    # Food permits: match each permit to its ISD license, then carry the phone over
    permits["zip_code"] = std_zip(permits["zip_code"])
    permits["property_id"] = pd.to_numeric(permits["property_id"], errors="coerce").astype("Int64")
    permits["name_key"] = permits["business_name"].map(name_key)
    permits["phone"] = std_phone(permits["phone"])
    xref = match_permits(permits, lic, locs)
    phones = (permits[["record_id", "phone"]].merge(xref, on="record_id")
              .dropna(subset=["phone"]).drop_duplicates("licenseno").set_index("licenseno")["phone"])
    lic["phone"] = lic["licenseno"].map(phones)

    emit("isd_licenses", lic[[
        "licenseno", "business_name", "dba_name", "name_key", "legal_owner",
        "owner_last", "owner_first", "category_code", "license_status",
        "issued_at", "expires_at", "location_id", "phone"]], "licenseno")

    # Permits keep only what isn't already on the license (or the whole
    # record when unmatched, so nothing is lost).
    permits["permit_id"] = permits["record_id"].astype(int)
    permits["license_added_at"] = std_ts(permits["license_added"])
    permits["neighborhood"] = std_neighborhood(permits["city"])
    permits["latitude"], permits["longitude"] = std_coords(permits["latitude"], permits["longitude"])
    permits = attach_address(permits, "address", "zip_code", "food_permit")
    emit("food_permits", permits[[
        "permit_id", "business_name", "dba_name", "name_key", "license_category",
        "license_status", "license_added_at", "address_key", "street_number_end", "unit",
        "neighborhood", "zip_code", "property_id", "latitude", "longitude", "phone",
    ]].rename(columns={"license_category": "category_code"}), "permit_id")
    xref["permit_id"] = xref.pop("record_id").astype(int)
    emit("food_permit_licenses", xref[["permit_id", "licenseno", "match_method"]], "permit_id")

    # Inspection result lookup
    codes = sorted(insp["result"].dropna().unique())
    unknown = [c for c in codes if c not in INSPECTION_RESULTS]
    if unknown:
        print(f"  WARNING: unmapped inspection results: {unknown}")
    emit("inspection_results", pd.DataFrame({
        "result_code": codes,
        "result_label": [INSPECTION_RESULTS.get(c, (c, "other"))[0] for c in codes],
        "outcome": [INSPECTION_RESULTS.get(c, (c, "other"))[1] for c in codes],
    }), "result_code")

    insp["inspection_id"] = insp["inspection_id"].astype(int)
    insp["inspected_at"] = std_ts(insp["inspected_at"])
    emit("inspections", insp.rename(columns={"result": "result_code"})[
        ["inspection_id", "licenseno", "inspected_at", "result_code"]], "inspection_id")

    # Violation types + severity lookup
    emit("severity_levels", pd.DataFrame(
        [(k, *v) for k, v in SEVERITY.items()],
        columns=["severity_level", "severity_label", "severity_rank"]), "severity_level")
    vtypes.loc[~vtypes["severity_level"].isin(SEVERITY.keys()), "severity_level"] = pd.NA
    emit("violation_types", vtypes, "violation_code")

    iv["violation_id"] = iv["violation_id"].astype(int)
    iv["inspection_id"] = iv["inspection_id"].astype(int)
    iv["violation_at"] = std_ts(iv["violation_at"])
    iv["status_changed_at"] = std_ts(iv["status_changed_at"])
    emit("inspection_violations", iv[[
        "violation_id", "inspection_id", "violation_code", "violation_status",
        "violation_at", "status_changed_at", "comments"]], "violation_id")


def match_permits(permits: pd.DataFrame, lic: pd.DataFrame, locs: pd.DataFrame) -> pd.DataFrame:
    """Link each active permit to one ISD license. Tries, in order:
      1. name_key + property_id + category (unique candidate)
      2. property_id + category, when only one active license fits
      3. name_key + address_key + category (unique candidate)
    Ties at a step are broken by the license issued closest to the permit date."""
    cand = lic.merge(locs[["location_id", "property_id", "address_key"]], on="location_id", how="left")
    cand = cand[cand["license_status"].eq("Active")]
    p = permits.copy()
    p["address_key"] = [AddressRegistry.key(parse_address(a), z)
                        for a, z in zip(p["address"], p["zip_code"])]
    p["added"] = pd.to_datetime(p["license_added"], utc=True, errors="coerce")
    cand = cand.assign(issued=pd.to_datetime(cand["issued_at"], utc=True, errors="coerce"))

    steps = [
        ("name+property", ["name_key", "property_id", "license_category"]),
        ("property", ["property_id", "license_category"]),
        ("name+address", ["name_key", "address_key", "license_category"]),
    ]
    cand = cand.rename(columns={"category_code": "license_category"})
    matched, used = [], set()
    remaining = p
    for label, keys in steps:
        c = cand[~cand["licenseno"].isin(used)].dropna(subset=keys)
        r = remaining.dropna(subset=keys)
        if label == "property":  # only when the property has exactly one candidate
            c = c[~c.duplicated(subset=keys, keep=False)]
        m = r[["record_id", "added"] + keys].merge(c[["licenseno", "issued"] + keys], on=keys)
        m["gap"] = (m["issued"] - m["added"]).abs()
        m = m.sort_values("gap").drop_duplicates("record_id").drop_duplicates("licenseno")
        m["match_method"] = label
        matched.append(m[["record_id", "licenseno", "match_method"]])
        used |= set(m["licenseno"])
        remaining = remaining[~remaining["record_id"].isin(m["record_id"])]
    out = pd.concat(matched)
    out = permits[["record_id"]].merge(out, on="record_id", how="left")
    out["match_method"] = out["match_method"].fillna("unmatched")
    print(f"  permit -> license matches: {out['match_method'].value_counts().to_dict()}")
    return out


# ===========================================================================
# Licensing Board
# ===========================================================================

def build_lb():
    print("Licensing Board")
    lb = read("lb_licenses")

    # License types + alcohol lookup
    alcohol = pd.DataFrame({
        "alcohol_type": ["none", "byob", "beer_wine", "beer_wine_cordials", "all_alcohol"],
        "serves_alcohol": [False, False, True, True, True],
    })
    emit("lb_alcohol_types", alcohol, "alcohol_type")
    types = lb[["license_type", "license_category", "alcohol_type"]].drop_duplicates()
    emit("lb_license_types", types.sort_values("license_type"), "license_type")

    # Managers: one row per (license, manager)
    mgr = (lb[["license_num", "manager"]].dropna()
           .assign(manager=lambda d: d["manager"].str.split(r"\s*;\s*"))
           .explode("manager").dropna().drop_duplicates())
    emit("lb_license_managers", mgr, ["license_num", "manager"])

    lb["zip_code"] = std_zip(lb["zip"])
    lb["neighborhood"] = std_neighborhood(lb["city"])
    lb["latitude"], lb["longitude"] = std_coords(lb["latitude"], lb["longitude"])
    lb["issued_date"] = std_date(lb["issued"])
    lb["expires_date"] = std_date(lb["expires"])
    lb["capacity"] = pd.to_numeric(lb["capacity"], errors="coerce").astype("Int64")
    lb["open_24_hours"] = std_bool(lb["open_24_hours"])
    lb["name_key"] = lb["dba_name"].fillna(lb["business_name"]).map(name_key)
    lb["business_name_key"] = lb["business_name"].map(name_key)

    # Hours: keep parsed 24h values; keep raw text only where it couldn't be parsed
    notes = []
    for raw, parsed in [("opening", "opening_24h"), ("closing", "closing_24h"),
                        ("patronsout", "patronsout_24h")]:
        bad = lb[raw].notna() & lb[parsed].isna() & ~lb["open_24_hours"].fillna(False)
        notes.append(np.where(bad, raw + ": " + lb[raw].fillna(""), None))
    lb["hours_note"] = ["; ".join(x for x in row if x) or None for row in zip(*notes)]

    # Phones: prefer the already-cleaned digits; re-validate
    for col in ["day_phone", "evening_phone"]:
        lb[col] = std_phone(lb[f"{col}_clean"])
        lb[f"{col}_ext"] = lb[f"{col}_ext"].where(lb[col].notna())

    lb = attach_address(lb, "address", "zip_code", "licensing_board")
    emit("lb_licenses", lb[[
        "license_num", "historicallicensenum", "status", "license_type",
        "issued_date", "expires_date", "business_name", "dba_name", "name_key",
        "business_name_key", "applicant", "opening_24h", "closing_24h", "patronsout_24h",
        "open_24_hours", "hours_note", "capacity", "comments", "location_comments",
        "descpremadd", "day_phone", "day_phone_ext", "evening_phone", "evening_phone_ext",
        "address_key", "street_number_end", "unit", "neighborhood", "zip_code",
        "latitude", "longitude",
    ]].rename(columns={
        "historicallicensenum": "historical_license_num",
        "opening_24h": "opening_time", "closing_24h": "closing_time",
        "patronsout_24h": "patrons_out_time", "descpremadd": "premises_description",
    }), "license_num")


# ===========================================================================
# Michelin
# ===========================================================================

def build_michelin():
    print("Michelin")
    mi = read("michelin_restaurants")

    awards = mi[["award", "stars", "is_bib_gourmand"]].drop_duplicates()
    awards["stars"] = awards["stars"].astype(int)
    awards["is_bib_gourmand"] = std_bool(awards["is_bib_gourmand"])
    emit("michelin_awards", awards.sort_values("stars", ascending=False), "award")

    fac = (mi[["michelin_id", "facilities"]].dropna()
           .assign(facility=lambda d: d["facilities"].str.split(r"\s*;\s*"))
           .explode("facility")[["michelin_id", "facility"]].dropna().drop_duplicates())
    emit("michelin_facilities", fac, ["michelin_id", "facility"])

    mi["zip_code"] = std_zip(mi["zip_code"])
    mi["latitude"], mi["longitude"] = std_coords(mi["latitude"], mi["longitude"])
    mi["phone"] = std_phone(mi["phone"])
    mi["green_star"] = std_bool(mi["green_star"])
    mi["name_key"] = mi["name"].map(name_key)
    mi = attach_address(mi, "street_address", "zip_code", "michelin")
    emit("michelin_restaurants", mi[[
        "michelin_id", "name", "name_key", "cuisine", "price", "award", "green_star",
        "address_key", "street_number_end", "unit", "zip_code", "latitude", "longitude",
        "phone", "website_url", "michelin_url", "description",
    ]], "michelin_id")


# ===========================================================================
# 311
# ===========================================================================

def build_311():
    print("311 service requests")
    s = read("311_service_requests")

    def lookup(values: pd.Series, id_col: str, name_col: str) -> pd.DataFrame:
        v = sorted(values.dropna().unique())
        return pd.DataFrame({id_col: np.arange(1, len(v) + 1), name_col: v})

    dept = lookup(s["assigned_department"], "department_id", "department_name")
    emit("departments", dept, "department_id")

    team = s[["assigned_team", "assigned_department"]].dropna().drop_duplicates()
    if team["assigned_team"].duplicated().any():
        raise ValueError("a 311 team maps to more than one department")
    team = (team.merge(dept, left_on="assigned_department", right_on="department_name")
                .sort_values("assigned_team").reset_index(drop=True))
    team.insert(0, "team_id", np.arange(1, len(team) + 1))
    team = team.rename(columns={"assigned_team": "team_name"})[["team_id", "team_name", "department_id"]]
    emit("teams", team, "team_id")

    st = s[["service_name", "case_topic"]].dropna(subset=["service_name"]).drop_duplicates("service_name")
    st = st.sort_values("service_name").reset_index(drop=True)
    st.insert(0, "service_type_id", np.arange(1, len(st) + 1))
    emit("service_types", st, "service_type_id")

    c = (s.merge(st[["service_type_id", "service_name"]], on="service_name", how="left")
          .merge(team[["team_id", "team_name"]], left_on="assigned_team", right_on="team_name", how="left"))
    for col in ["open_date", "target_close_date", "close_date"]:
        c[col] = std_ts(c[col])
    c["service_type_id"] = c["service_type_id"].astype("Int64")
    c["team_id"] = c["team_id"].astype("Int64")
    emit("service_cases", c[[
        "case_id", "service_type_id", "team_id", "case_status", "open_date",
        "target_close_date", "close_date", "on_time", "closure_reason",
        "closure_comments", "report_source"]], "case_id")

    # Locations: street part of full_address, else number + name
    street = s["full_address"].str.split(",").str[0]
    fallback = (s["street_number"].fillna("") + " " + s["street_name"].fillna("")).str.strip()
    s["street_raw"] = street.fillna(fallback.replace("", pd.NA))
    s["zip_code"] = std_zip(s["zip_code"])
    s["latitude"], s["longitude"] = std_coords(s["latitude"], s["longitude"])
    s["neighborhood"] = std_neighborhood(s["neighborhood"])
    for col in ["ward", "precinct"]:
        s[col] = s[col].str.extract(r"(\d+)")[0].str.zfill(2)
    for col in ["city_council_district", "fire_district"]:
        s[col] = pd.to_numeric(s[col], errors="coerce").astype("Int64")
    loc_cols = ["street_raw", "zip_code", "neighborhood", "public_works_district",
                "city_council_district", "fire_district", "police_district", "ward",
                "precinct", "latitude", "longitude"]
    loc = s[["case_id"] + loc_cols]
    loc = loc[loc[loc_cols].notna().any(axis=1)]
    loc = attach_address(loc, "street_raw", "zip_code", "311")
    emit("case_locations", loc[[
        "case_id", "address_key", "street_number_end", "unit", "neighborhood", "zip_code",
        "public_works_district", "city_council_district", "fire_district",
        "police_district", "ward", "precinct", "latitude", "longitude"]], "case_id")


# ===========================================================================
# Shared dimensions, FK checks, output
# ===========================================================================

FOREIGN_KEYS = [
    # (table, column, ref_table, ref_column)
    ("isd_locations", "address_id", "addresses", "address_id"),
    ("isd_locations", "zip_code", "zip_codes", "zip_code"),
    ("isd_licenses", "category_code", "license_categories", "category_code"),
    ("isd_licenses", "location_id", "isd_locations", "location_id"),
    ("food_permits", "category_code", "license_categories", "category_code"),
    ("food_permits", "address_id", "addresses", "address_id"),
    ("food_permits", "zip_code", "zip_codes", "zip_code"),
    ("food_permit_licenses", "permit_id", "food_permits", "permit_id"),
    ("food_permit_licenses", "licenseno", "isd_licenses", "licenseno"),
    ("inspections", "licenseno", "isd_licenses", "licenseno"),
    ("inspections", "result_code", "inspection_results", "result_code"),
    ("inspection_violations", "inspection_id", "inspections", "inspection_id"),
    ("inspection_violations", "violation_code", "violation_types", "violation_code"),
    ("violation_types", "severity_level", "severity_levels", "severity_level"),
    ("lb_license_types", "alcohol_type", "lb_alcohol_types", "alcohol_type"),
    ("lb_licenses", "license_type", "lb_license_types", "license_type"),
    ("lb_licenses", "address_id", "addresses", "address_id"),
    ("lb_licenses", "zip_code", "zip_codes", "zip_code"),
    ("lb_license_managers", "license_num", "lb_licenses", "license_num"),
    ("michelin_restaurants", "award", "michelin_awards", "award"),
    ("michelin_restaurants", "address_id", "addresses", "address_id"),
    ("michelin_restaurants", "zip_code", "zip_codes", "zip_code"),
    ("michelin_facilities", "michelin_id", "michelin_restaurants", "michelin_id"),
    ("teams", "department_id", "departments", "department_id"),
    ("service_cases", "service_type_id", "service_types", "service_type_id"),
    ("service_cases", "team_id", "teams", "team_id"),
    ("case_locations", "case_id", "service_cases", "case_id"),
    ("case_locations", "address_id", "addresses", "address_id"),
    ("case_locations", "zip_code", "zip_codes", "zip_code"),
    ("addresses", "zip_code", "zip_codes", "zip_code"),
]


def build_shared():
    addresses = ADDR.build()
    resolve_address_ids(addresses)  # swap address_key for address_id in source tables
    emit("addresses", addresses, "address_id")

    zips = set()
    for t in TABLES.values():
        if "zip_code" in t.columns:
            zips |= set(t["zip_code"].dropna())
    z = pd.DataFrame({"zip_code": sorted(zips)})
    z["in_boston"] = z["zip_code"].isin(BOSTON_ZIPS)
    emit("zip_codes", z, "zip_code")


def check_fks():
    print("Foreign key check")
    bad = 0
    for t, col, ref, ref_col in FOREIGN_KEYS:
        vals = TABLES[t][col].dropna()
        missing = ~vals.isin(set(TABLES[ref][ref_col]))
        if missing.any():
            bad += 1
            print(f"  FAIL {t}.{col} -> {ref}.{ref_col}: {missing.sum():,} orphans, "
                  f"e.g. {vals[missing].unique()[:3].tolist()}")
    print("  all foreign keys valid" if not bad else f"  {bad} foreign key(s) with orphans")


SQL_TYPES = {"Int64": "INTEGER", "int64": "INTEGER", "float64": "REAL",
             "boolean": "BOOLEAN", "bool": "BOOLEAN"}
PKS = {}


def write_outputs():
    os.makedirs(OUT_DIR, exist_ok=True)
    ddl = ["-- Generated by normalize_all.py\n"]
    order = ["zip_codes", "addresses", "license_categories", "isd_locations", "isd_licenses",
             "food_permits", "food_permit_licenses", "inspection_results", "inspections",
             "severity_levels", "violation_types", "inspection_violations",
             "lb_alcohol_types", "lb_license_types", "lb_licenses", "lb_license_managers",
             "michelin_awards", "michelin_restaurants", "michelin_facilities",
             "departments", "teams", "service_types", "service_cases", "case_locations"]
    for name in order:
        t = TABLES[name]
        t.to_csv(os.path.join(OUT_DIR, f"{name}.csv"), index=False)
        print(f"  {name}.csv: {len(t):,} rows x {t.shape[1]} cols")
        cols = [f"    {c} {SQL_TYPES.get(str(t[c].dtype), 'TEXT')}" for c in t.columns]
        cols.append(f"    PRIMARY KEY ({', '.join(PKS[name])})")
        for tt, col, ref, ref_col in FOREIGN_KEYS:
            if tt == name:
                cols.append(f"    FOREIGN KEY ({col}) REFERENCES {ref}({ref_col})")
        ddl.append(f"CREATE TABLE {name} (\n" + ",\n".join(cols) + "\n);\n")
    with open(os.path.join(OUT_DIR, "schema.sql"), "w") as f:
        f.write("\n".join(ddl))
    print("  schema.sql")


def main():
    build_isd()
    build_lb()
    build_michelin()
    build_311()
    build_shared()

    # record primary keys for the DDL
    PKS.update({
        "zip_codes": ["zip_code"], "addresses": ["address_id"],
        "license_categories": ["category_code"], "isd_locations": ["location_id"],
        "isd_licenses": ["licenseno"], "food_permits": ["permit_id"],
        "food_permit_licenses": ["permit_id"], "inspection_results": ["result_code"],
        "inspections": ["inspection_id"], "severity_levels": ["severity_level"],
        "violation_types": ["violation_code"], "inspection_violations": ["violation_id"],
        "lb_alcohol_types": ["alcohol_type"], "lb_license_types": ["license_type"],
        "lb_licenses": ["license_num"], "lb_license_managers": ["license_num", "manager"],
        "michelin_awards": ["award"], "michelin_restaurants": ["michelin_id"],
        "michelin_facilities": ["michelin_id", "facility"], "departments": ["department_id"],
        "teams": ["team_id"], "service_types": ["service_type_id"],
        "service_cases": ["case_id"], "case_locations": ["case_id"],
    })
    check_fks()
    print(f"Writing to {OUT_DIR}/")
    write_outputs()


if __name__ == "__main__":
    main()