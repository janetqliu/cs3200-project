# Preliminary Research Questions

Questions the normalized database can answer, with the tables each one uses.

## Food safety

1. **Which neighborhoods have the highest share of failed inspections, and has that changed over 2006–2026?**
   `inspections` → `inspection_results` → `isd_licenses` → `isd_locations`
2. **Which violation types are cited most often, and which critical (`***`) violations are most likely to turn a pass into a fail?**
   `inspection_violations` → `violation_types` → `severity_levels`
3. **Do takeout licenses (FT) fail inspections more often than sit-down ones (FS)?**
   `isd_licenses` → `license_categories`, `inspections`
4. **Are some businesses repeat offenders, failing several inspections in a row? How long do they take to pass again?**
   `inspections` (ordered by `inspected_at` per `licenseno`)

## Licensing & alcohol

5. **Do restaurants with alcohol licenses have different inspection outcomes from those without?**
   `lb_licenses` → `lb_license_types` → `lb_alcohol_types`; joined to inspections via `addresses` → `isd_locations`
6. **Are places that stay open late (closing after 1 AM, or open 24 hours) cited more for sanitation?**
   `lb_licenses.closing_time`, `open_24_hours` → `addresses` → inspections
7. **Does seating capacity relate to violation counts?**
   `lb_licenses.capacity` → `addresses` → `inspection_violations`

## Michelin

8. **Do Michelin-listed restaurants have cleaner inspection records than other restaurants in the same ZIP code?**
   `michelin_restaurants` → `addresses` → `isd_locations` → `inspections`
9. **What do the most-cited violations at Michelin restaurants look like, compared with citywide?**
   `michelin_restaurants` → … → `inspection_violations` → `violation_types`

## 311 & neighborhood conditions

10. **Do ZIP codes or neighborhoods with more trash-related 311 complaints have more food-safety violations?**
    Relevant complaint types include Improper Trash Storage, Overflowing Trash, Illegal Dumping, and Litter & Debris.
    `service_cases` → `service_types`, `case_locations` ↔ `zip_codes` ↔ `isd_locations`
11. **Do areas with more restaurants get more trash complaints, or do they get them resolved more slowly?**
    `isd_locations` / `lb_licenses` counts by ZIP vs. `service_cases` close times
12. **Which city departments miss their 311 deadlines most often, and does that vary by neighborhood?**
    `service_cases.on_time` → `teams` → `departments`, `case_locations.neighborhood`

## Limitations to plan around

- **311 time window:** the 311 data only covers August 2025 to October 2026. Questions comparing 311 complaints with inspections should use inspections from the same period.
- **No pest data in 311:** the 311 service types include no rodent or pest category, so rats can't be studied directly.
- **Cross-source matching:** linking records across sources depends on matching addresses. About 81% of Licensing Board licenses and 96% of permits match an ISD location, so every cross-source analysis should mention that coverage.
- **Michelin sample size:** with only 15 restaurants, Michelin questions are case studies, not statistical comparisons.