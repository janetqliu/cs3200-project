"""Clean the Boston Licensing Board licenses CSV.

Keeps only 'Common Victualler' licenses (food service, including CV7 alcohol
variants). Inn, Club, General on Premise and Misc licenses are dropped on
purpose, even though some of those places also serve food.

Usage:
    python clean_licensing_board.py input.csv [output.csv]

Default output: licensing_board_licenses.csv
"""

import math
import re
import sys
import unicodedata

import numpy as np
import pandas as pd

FOOD_CATEGORIES = {"Common Victualler"}
TODAY = pd.Timestamp.today().normalize()


# ---------------------------------------------------------------------------
# Text tidying
# ---------------------------------------------------------------------------

QUOTE_CHARS = "\"'\u201c\u201d\u2018\u2019"  # straight and curly, double and single


def tidy_text(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df[col] = (
            df[col]
            .str.strip()
            .str.strip(QUOTE_CHARS)                 # quotes wrapped around the whole value
            .str.replace(r"\s+", " ", regex=True)   # collapse repeated whitespace
            .str.strip()
        )
    return df


PLACEHOLDERS = {".", "-", "n/a", "na", "none", "null", "unknown", "tbd"}


def blank_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        df.loc[df[col].str.lower().isin(PLACEHOLDERS), col] = ""
    # A capacity of 0 or coordinates of 0 mean "not recorded".
    df.loc[df["capacity"] == "0", "capacity"] = ""
    no_gps = (pd.to_numeric(df["gpsx"], errors="coerce").fillna(0) == 0) | (
        pd.to_numeric(df["gpsy"], errors="coerce").fillna(0) == 0
    )
    df.loc[no_gps, ["gpsx", "gpsy"]] = ""
    return df


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Phones
# ---------------------------------------------------------------------------

# Valid US (NANP) number: area code and exchange can't start with 0 or 1.
NANP_RE = r"^[2-9]\d{2}[2-9]\d{6}$"


def clean_phone(series: pd.Series) -> pd.DataFrame:
    parts = series.str.split(r"(?i)\s*(?:x|ext\.?)\s*", n=1, regex=True, expand=True)
    parts = parts.reindex(columns=[0, 1]).fillna("")
    digits = parts[0].str.replace(r"\D", "", regex=True)
    digits = digits.where(~((digits.str.len() == 11) & digits.str.startswith("1")),
                          digits.str[1:])
    # Anything that isn't a valid 10-digit US number is blanked
    digits = digits.where(digits.str.match(NANP_RE), "")
    ext = parts[1].str.replace(r"\D", "", regex=True).where(digits != "", "")
    return pd.DataFrame({"phone": digits, "ext": ext})


# ---------------------------------------------------------------------------
# Hours and dates
# ---------------------------------------------------------------------------

TIME_RE = re.compile(
    r"(?P<h>\d{1,2})(?:\s*[:.;]\s*(?P<m>\d{2})|(?P<m2>\d{2}))?\s*(?P<ap>[AP])\.?\s*M\.?",
    re.IGNORECASE,
)


def parse_time(value: str) -> str:
    """Pull the first clock time out of free text and return 24-hour 'HH:MM'.

    Handles '2:00 AM', '2 AM', '4:00 A M', '500 AM', '10.00 AM', '11;00 PM',
    'To: 2:00 AM', 'MIDNIGHT', 'NOON'. Times without AM/PM ('4:00') are
    ambiguous and return ''. '13:30 PM' is read as 13:30.
    """
    v = value.upper()
    if "MIDNIGHT" in v:
        return "00:00"
    if "NOON" in v:
        return "12:00"
    m = TIME_RE.search(v)
    if not m:
        return ""
    h, mins = int(m["h"]), int(m["m"] or m["m2"] or 0)
    if h > 23 or mins > 59:
        return ""
    if h <= 12:  # 12-hour clock
        h = h % 12 + (12 if m["ap"].upper() == "P" else 0)
    return f"{h:02d}:{mins:02d}"


def is_24_hours(value: str) -> bool:
    return bool(re.search(r"24\s*(?:HOURS?|HRS?)", value, re.IGNORECASE))


def to_date(s: pd.Series) -> pd.Series:
    """Parse to ISO 'YYYY-MM-DD'; unparseable -> ''."""
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m-%d").fillna("")


# ---------------------------------------------------------------------------
# Alcohol
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

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


def standardize_suffix(token: str) -> str:
    return SUFFIXES.get(token.upper().rstrip("."), "")


ADDRESS_RE = re.compile(
    r"^(?P<start>[^\s-]*)-(?P<end>\S*)\s+(?:(?P<dir>[NSEW])\s+)?(?P<rest>.*)$"
)


def split_address(addr: str) -> dict:
    out = {"street_number": "", "street_number_end": "", "street_direction": "",
           "street_name": "", "street_suffix": "", "address_clean": ""}
    if not addr:
        return out

    # 'Logan Airport, Terminal B' and 'Logan Airport Terminal B' should match
    addr = re.sub(r"\s*,\s*", " ", addr).strip()

    m = ADDRESS_RE.match(addr)
    if m:
        start, end = m["start"], m["end"].strip("-")
        direction, rest = m["dir"] or "", m["rest"]
        # A lone letter followed by just a suffix is a street name, not a
        # direction: '87- E ST' is E Street, not East <blank> Street.
        if direction and len(rest.split()) < 2:
            rest = f"{direction} {rest}"
            direction = ""
    else:
        m2 = re.match(r"^(\d+[A-Za-z]?)\s+(.*)$", addr)
        start, end, direction, rest = (m2[1], "", "", m2[2]) if m2 else ("", "", "", addr)

    tokens = rest.split()
    suffix = standardize_suffix(tokens[-1]) if len(tokens) > 1 else ""
    name = " ".join(tokens[:-1] if suffix else tokens)

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


# ---------------------------------------------------------------------------
# Coordinates: MA State Plane (EPSG:2249, US survey feet) -> WGS84 lat/long
# ---------------------------------------------------------------------------

def state_plane_to_latlon(x_ft: pd.Series, y_ft: pd.Series):
    """Inverse Lambert Conformal Conic (2SP) for NAD83 / Massachusetts Mainland.

    Uses pyproj if installed; otherwise the closed-form projection math below
    (accurate to well under a meter; NAD83 and WGS84 differ by ~1 m here).
    """
    x = pd.to_numeric(x_ft, errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(y_ft, errors="coerce").to_numpy(dtype=float)

    try:
        from pyproj import Transformer
        lon, lat = Transformer.from_crs("EPSG:2249", "EPSG:4326", always_xy=True).transform(x, y)
        return np.asarray(lat), np.asarray(lon)
    except ImportError:
        pass

    # GRS80 ellipsoid and EPSG:2249 projection parameters
    a = 6378137.0
    f = 1 / 298.257222101
    e = math.sqrt(2 * f - f * f)
    lat1, lat2 = math.radians(42 + 41 / 60), math.radians(41 + 43 / 60)
    lat0, lon0 = math.radians(41.0), math.radians(-71.5)
    fe, fn = 200000.0, 750000.0           # false easting / northing, meters
    us_ft = 1200 / 3937                   # US survey foot in meters

    def m(phi):
        return math.cos(phi) / math.sqrt(1 - (e * math.sin(phi)) ** 2)

    def t(phi):
        return math.tan(math.pi / 4 - phi / 2) / (
            ((1 - e * math.sin(phi)) / (1 + e * math.sin(phi))) ** (e / 2))

    n = (math.log(m(lat1)) - math.log(m(lat2))) / (math.log(t(lat1)) - math.log(t(lat2)))
    F = m(lat1) / (n * t(lat1) ** n)
    rho0 = a * F * t(lat0) ** n

    dx = x * us_ft - fe
    dy = rho0 - (y * us_ft - fn)
    rho = np.sign(n) * np.sqrt(dx ** 2 + dy ** 2)
    theta = np.arctan2(dx, dy)
    tt = (rho / (a * F)) ** (1 / n)

    lon = theta / n + lon0
    lat = np.pi / 2 - 2 * np.arctan(tt)
    for _ in range(6):  # iterate to convergence
        es = e * np.sin(lat)
        lat = np.pi / 2 - 2 * np.arctan(tt * ((1 - es) / (1 + es)) ** (e / 2))

    return np.degrees(lat), np.degrees(lon)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def clean(input_path: str, output_path: str) -> pd.DataFrame:
    # Read everything as text so ZIP codes keep their leading zeros.
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    n_in = len(df)

    df = tidy_text(df)
    df = df[df["license_category"].isin(FOOD_CATEGORIES)].copy()
    df = blank_placeholders(df)

    # Basic field standardization
    df["state"] = df["state"].str.upper()
    df["zip"] = df["zip"].where(df["zip"] == "", df["zip"].str.zfill(5))
    # Hours: keep the raw text and add parsed 24-hour versions alongside it.
    df["open_24_hours"] = df["opening"].map(is_24_hours) | df["closing"].map(is_24_hours)
    for col in ["opening", "closing", "patronsout"]:
        df[f"{col}_24h"] = df[col].map(parse_time)
    for col in ["issued", "expires"]:
        df[col] = to_date(df[col])

    # De-duplicate only after cleaning, so 'n/a' vs '' etc. don't hide dupes.
    df = df.drop_duplicates()

    # Some licenses appear once per manager; collapse to one row per license.
    others = [c for c in df.columns if c != "manager"]
    df = (
        df.groupby(others, dropna=False, sort=False)["manager"]
          .agg(lambda s: "; ".join(sorted({v for v in s if v})))
          .reset_index()
    )[list(df.columns)]
    dupes = df["license_num"][df["license_num"].duplicated()].unique()
    if len(dupes):
        raise ValueError(f"license_num still duplicated after cleaning: {list(dupes)[:10]}")

    # Address parts
    addr = pd.DataFrame(df["address"].map(split_address).tolist(), index=df.index)
    df = pd.concat([df, addr], axis=1)

    # Coordinates
    lat, lon = state_plane_to_latlon(df["gpsx"], df["gpsy"])
    df["latitude"] = np.round(lat, 7)
    df["longitude"] = np.round(lon, 7)

    # Phones
    for col in ["day_phone", "evening_phone"]:
        ph = clean_phone(df[col])
        df[f"{col}_clean"] = ph["phone"]
        df[f"{col}_ext"] = ph["ext"]

    # Names
    df["display_name"] = df["dba_name"].where(df["dba_name"] != "", df["business_name"])
    df["name_key"] = df["display_name"].map(name_key)
    df["business_name_key"] = df["business_name"].map(name_key)

    # Alcohol
    df["alcohol_type"] = df["license_type"].map(alcohol_type)
    df["serves_alcohol"] = df["alcohol_type"].isin(
        ["all_alcohol", "beer_wine", "beer_wine_cordials"])
    unmapped = df.loc[(df["alcohol_type"] == "none")
                      & ~df["license_type"].eq("Common Victualler"), "license_type"].unique()
    if len(unmapped):
        print(f"WARNING: license types not mapped to an alcohol type: {list(unmapped)}")

    # Status check: 'Active' licenses whose expiry date has passed
    expires = pd.to_datetime(df["expires"], errors="coerce")
    df["is_expired"] = expires < TODAY

    df.to_csv(output_path, index=False)

    print(f"Input rows:              {n_in:,}")
    print(f"Output rows:             {len(df):,}")
    print(f"Multi-manager licenses:  {df['manager'].str.contains(';').sum():,}")
    print(f"Blank capacity:          {(df['capacity'] == '').sum():,}")
    print(f"Missing lat/lon:         {df['latitude'].isna().sum():,}")
    print(f"Addresses w/o suffix:    {(df['street_suffix'] == '').sum():,}")
    print(f"Unusable day phones:     {((df['day_phone'] != '') & (df['day_phone_clean'] == '')).sum():,}")
    unparsed = (df["closing"] != "") & (df["closing_24h"] == "") & ~df["open_24_hours"]
    print(f"Open 24 hours:           {df['open_24_hours'].sum():,}")
    print(f"Unparsed closing times:  {unparsed.sum():,}")
    print(f"Expired but listed:      {df['is_expired'].sum():,}")
    print("\nAlcohol type:")
    print(df["alcohol_type"].value_counts().to_string())
    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python clean_licensing_board.py input.csv [output.csv]")
    in_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "licensing_board_licenses.csv"
    clean(in_path, out_path)