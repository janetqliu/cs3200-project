import pandas as pd

michelin = pd.read_csv("michelin_my_maps.csv", dtype="string")
licenses = pd.read_csv("LAB7_subqueries_START.sql.csv", dtype="string")

for df in [michelin, licenses]:
    for column in df.columns:
        df[column] = df[column].str.strip()

licenses["city"] = licenses["city"].str.rstrip("/").str.title()
licenses["state"] = licenses["state"].str.upper()

greater_boston = [
    "Boston", "Cambridge", "Brookline", "Lynn",
    "Newton", "Newton Centre", "Chestnut Hill",
    "Allston", "Brighton", "Charlestown", "Dorchester",
    "East Boston", "Hyde Park", "Jamaica Plain", "Mattapan",
    "Mission Hill", "Roslindale", "Roxbury", "South Boston",
    "West Roxbury", "Financial District",
    "Downtown/Financial District"
]

michelin_locations = [city + ", MA, USA" for city in greater_boston]

michelin = michelin[michelin["Location"].isin(michelin_locations)].copy()

licenses = licenses[licenses["city"].isin(greater_boston) & (licenses["state"] == "MA")].copy()

licenses["dayphn_cleaned"] = licenses["dayphn_cleaned"].replace("0", pd.NA)

for column in ["Latitude", "Longitude"]:
    michelin[column] = pd.to_numeric(michelin[column])

for column in ["latitude", "longitude"]:
    licenses[column] = pd.to_numeric(licenses[column])

licenses["license_add_dt_tm"] = pd.to_datetime(licenses["license_add_dt_tm"], format="mixed", utc=True)

michelin.to_csv("michelin_greater_boston.csv", index=False)
licenses.to_csv("food_licenses_greater_boston.csv", index=False)

print("Michelin rows remaining:", len(michelin))
print("License rows remaining:", len(licenses))
