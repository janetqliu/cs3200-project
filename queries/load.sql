LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/zip_codes.csv'
INTO TABLE zip_codes
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@zip_code, @in_boston)
SET
    zip_code = NULLIF(@zip_code, ''),
    in_boston = CASE WHEN LOWER(@in_boston) IN ('true', '1', 't', 'yes') THEN 1 WHEN LOWER(@in_boston) IN ('false', '0', 'f', 'no') THEN 0 ELSE NULL END;

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/addresses.csv'
INTO TABLE addresses
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@address_id, @address_key, @street_number, @street_direction, @street_name, @street_suffix, @zip_code)
SET
    address_id = NULLIF(@address_id, '') + 0,
    address_key = NULLIF(@address_key, ''),
    street_number = NULLIF(@street_number, ''),
    street_direction = NULLIF(@street_direction, ''),
    street_name = NULLIF(@street_name, ''),
    street_suffix = NULLIF(@street_suffix, ''),
    zip_code = NULLIF(@zip_code, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/license_categories.csv'
INTO TABLE license_categories
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@category_code, @category_description)
SET
    category_code = NULLIF(@category_code, ''),
    category_description = NULLIF(@category_description, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/isd_locations.csv'
INTO TABLE isd_locations
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@location_id, @address_id, @street_number_end, @neighborhood, @property_id, @latitude, @longitude)
SET
    location_id = NULLIF(@location_id, '') + 0,
    address_id = NULLIF(@address_id, '') + 0,
    street_number_end = NULLIF(@street_number_end, ''),
    neighborhood = NULLIF(@neighborhood, ''),
    property_id = NULLIF(@property_id, '') + 0,
    latitude = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/isd_licenses.csv'
INTO TABLE isd_licenses
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@licenseno, @business_name, @dba_name, @name_key, @legal_owner, @owner_last, @owner_first, @category_code, @license_status, @issued_at, @expires_at, @location_id, @phone)
SET
    licenseno = NULLIF(@licenseno, ''),
    business_name = NULLIF(@business_name, ''),
    dba_name = NULLIF(@dba_name, ''),
    name_key = NULLIF(@name_key, ''),
    legal_owner = NULLIF(@legal_owner, ''),
    owner_last = NULLIF(@owner_last, ''),
    owner_first = NULLIF(@owner_first, ''),
    category_code = NULLIF(@category_code, ''),
    license_status = NULLIF(@license_status, ''),
    issued_at = NULLIF(@issued_at, ''),
    expires_at = NULLIF(@expires_at, ''),
    location_id = NULLIF(@location_id, '') + 0,
    phone = NULLIF(@phone, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/food_permits.csv'
INTO TABLE food_permits
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@permit_id, @business_name, @dba_name, @name_key, @category_code, @license_status, @license_added_at, @address_id, @street_number_end, @neighborhood, @property_id, @latitude, @longitude, @phone)
SET
    permit_id = NULLIF(@permit_id, '') + 0,
    business_name = NULLIF(@business_name, ''),
    dba_name = NULLIF(@dba_name, ''),
    name_key = NULLIF(@name_key, ''),
    category_code = NULLIF(@category_code, ''),
    license_status = NULLIF(@license_status, ''),
    license_added_at = NULLIF(@license_added_at, ''),
    address_id = NULLIF(@address_id, '') + 0,
    street_number_end = NULLIF(@street_number_end, ''),
    neighborhood = NULLIF(@neighborhood, ''),
    property_id = NULLIF(@property_id, '') + 0,
    latitude = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, ''),
    phone = NULLIF(@phone, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/food_permit_licenses.csv'
INTO TABLE food_permit_licenses
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@permit_id, @licenseno, @match_method)
SET
    permit_id = NULLIF(@permit_id, '') + 0,
    licenseno = NULLIF(@licenseno, ''),
    match_method = NULLIF(@match_method, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/result_labels.csv'
INTO TABLE result_labels
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@result_label, @outcome)
SET
    result_label = NULLIF(@result_label, ''),
    outcome = NULLIF(@outcome, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/inspection_results.csv'
INTO TABLE inspection_results
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@result_code, @result_label)
SET
    result_code = NULLIF(@result_code, ''),
    result_label = NULLIF(@result_label, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/inspections.csv'
INTO TABLE inspections
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@inspection_id, @licenseno, @inspected_at, @result_code)
SET
    inspection_id = NULLIF(@inspection_id, '') + 0,
    licenseno = NULLIF(@licenseno, ''),
    inspected_at = NULLIF(@inspected_at, ''),
    result_code = NULLIF(@result_code, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/severity_levels.csv'
INTO TABLE severity_levels
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@severity_level, @severity_label, @severity_rank)
SET
    severity_level = NULLIF(@severity_level, ''),
    severity_label = NULLIF(@severity_label, ''),
    severity_rank = NULLIF(@severity_rank, '') + 0;

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/violation_types.csv'
INTO TABLE violation_types
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@violation_code, @severity_level, @description)
SET
    violation_code = NULLIF(@violation_code, ''),
    severity_level = NULLIF(@severity_level, ''),
    description = NULLIF(@description, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/inspection_violations.csv'
INTO TABLE inspection_violations
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@violation_id, @inspection_id, @violation_code, @violation_status, @violation_at, @status_changed_at, @comments)
SET
    violation_id = NULLIF(@violation_id, '') + 0,
    inspection_id = NULLIF(@inspection_id, '') + 0,
    violation_code = NULLIF(@violation_code, ''),
    violation_status = NULLIF(@violation_status, ''),
    violation_at = NULLIF(@violation_at, ''),
    status_changed_at = NULLIF(@status_changed_at, ''),
    comments = NULLIF(@comments, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/lb_alcohol_types.csv'
INTO TABLE lb_alcohol_types
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@alcohol_type, @serves_alcohol)
SET
    alcohol_type = NULLIF(@alcohol_type, ''),
    serves_alcohol = CASE WHEN LOWER(@serves_alcohol) IN ('true', '1', 't', 'yes') THEN 1 WHEN LOWER(@serves_alcohol) IN ('false', '0', 'f', 'no') THEN 0 ELSE NULL END;

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/lb_license_types.csv'
INTO TABLE lb_license_types
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@license_type, @license_category, @alcohol_type)
SET
    license_type = NULLIF(@license_type, ''),
    license_category = NULLIF(@license_category, ''),
    alcohol_type = NULLIF(@alcohol_type, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/lb_licenses.csv'
INTO TABLE lb_licenses
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@license_num, @historical_license_num, @status, @license_type, @issued_date, @expires_date, @business_name, @dba_name, @name_key, @business_name_key, @applicant, @opening_time, @closing_time, @patrons_out_time, @open_24_hours, @hours_note, @capacity, @comments, @location_comments, @premises_description, @day_phone, @day_phone_ext, @evening_phone, @address_id, @street_number_end, @neighborhood, @latitude, @longitude)
SET
    license_num = NULLIF(@license_num, ''),
    historical_license_num = NULLIF(@historical_license_num, ''),
    status = NULLIF(@status, ''),
    license_type = NULLIF(@license_type, ''),
    issued_date = NULLIF(@issued_date, ''),
    expires_date = NULLIF(@expires_date, ''),
    business_name = NULLIF(@business_name, ''),
    dba_name = NULLIF(@dba_name, ''),
    name_key = NULLIF(@name_key, ''),
    business_name_key = NULLIF(@business_name_key, ''),
    applicant = NULLIF(@applicant, ''),
    opening_time = NULLIF(@opening_time, ''),
    closing_time = NULLIF(@closing_time, ''),
    patrons_out_time = NULLIF(@patrons_out_time, ''),
    open_24_hours = CASE WHEN LOWER(@open_24_hours) IN ('true', '1', 't', 'yes') THEN 1 WHEN LOWER(@open_24_hours) IN ('false', '0', 'f', 'no') THEN 0 ELSE NULL END,
    hours_note = NULLIF(@hours_note, ''),
    capacity = NULLIF(@capacity, '') + 0,
    comments = NULLIF(@comments, ''),
    location_comments = NULLIF(@location_comments, ''),
    premises_description = NULLIF(@premises_description, ''),
    day_phone = NULLIF(@day_phone, ''),
    day_phone_ext = NULLIF(@day_phone_ext, ''),
    evening_phone = NULLIF(@evening_phone, ''),
    address_id = NULLIF(@address_id, '') + 0,
    street_number_end = NULLIF(@street_number_end, ''),
    neighborhood = NULLIF(@neighborhood, ''),
    latitude = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/lb_license_managers.csv'
INTO TABLE lb_license_managers
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@license_num, @manager)
SET
    license_num = NULLIF(@license_num, ''),
    manager = NULLIF(@manager, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/michelin_awards.csv'
INTO TABLE michelin_awards
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@award, @stars, @is_bib_gourmand)
SET
    award = NULLIF(@award, ''),
    stars = NULLIF(@stars, '') + 0,
    is_bib_gourmand = CASE WHEN LOWER(@is_bib_gourmand) IN ('true', '1', 't', 'yes') THEN 1 WHEN LOWER(@is_bib_gourmand) IN ('false', '0', 'f', 'no') THEN 0 ELSE NULL END;

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/michelin_restaurants.csv'
INTO TABLE michelin_restaurants
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@michelin_id, @name, @name_key, @cuisine, @price, @award, @green_star, @address_id, @unit, @latitude, @longitude, @website_url, @michelin_url, @description)
SET
    michelin_id = NULLIF(@michelin_id, ''),
    name = NULLIF(@name, ''),
    name_key = NULLIF(@name_key, ''),
    cuisine = NULLIF(@cuisine, ''),
    price = NULLIF(@price, ''),
    award = NULLIF(@award, ''),
    green_star = CASE WHEN LOWER(@green_star) IN ('true', '1', 't', 'yes') THEN 1 WHEN LOWER(@green_star) IN ('false', '0', 'f', 'no') THEN 0 ELSE NULL END,
    address_id = NULLIF(@address_id, '') + 0,
    unit = NULLIF(@unit, ''),
    latitude = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, ''),
    website_url = NULLIF(@website_url, ''),
    michelin_url = NULLIF(@michelin_url, ''),
    description = NULLIF(@description, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/michelin_facilities.csv'
INTO TABLE michelin_facilities
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@michelin_id, @facility)
SET
    michelin_id = NULLIF(@michelin_id, ''),
    facility = NULLIF(@facility, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/departments.csv'
INTO TABLE departments
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@department_id, @department_name)
SET
    department_id = NULLIF(@department_id, '') + 0,
    department_name = NULLIF(@department_name, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/teams.csv'
INTO TABLE teams
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@team_id, @team_name, @department_id)
SET
    team_id = NULLIF(@team_id, '') + 0,
    team_name = NULLIF(@team_name, ''),
    department_id = NULLIF(@department_id, '') + 0;

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/service_types.csv'
INTO TABLE service_types
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@service_type_id, @service_name)
SET
    service_type_id = NULLIF(@service_type_id, '') + 0,
    service_name = NULLIF(@service_name, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/service_cases.csv'
INTO TABLE service_cases
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@case_id, @service_type_id, @team_id, @case_status, @open_date, @target_close_date, @close_date, @on_time, @closure_reason, @closure_comments, @report_source)
SET
    case_id = NULLIF(@case_id, ''),
    service_type_id = NULLIF(@service_type_id, '') + 0,
    team_id = NULLIF(@team_id, '') + 0,
    case_status = NULLIF(@case_status, ''),
    open_date = NULLIF(@open_date, ''),
    target_close_date = NULLIF(@target_close_date, ''),
    close_date = NULLIF(@close_date, ''),
    on_time = NULLIF(@on_time, ''),
    closure_reason = NULLIF(@closure_reason, ''),
    closure_comments = NULLIF(@closure_comments, ''),
    report_source = NULLIF(@report_source, '');

LOAD DATA LOCAL INFILE '/Users/janet/Downloads/CS3200/cs3200-project/normalized/case_locations.csv'
INTO TABLE case_locations
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(@case_id, @address_id, @street_number_end, @unit, @neighborhood, @public_works_district, @city_council_district, @fire_district, @police_district, @ward, @precinct, @latitude, @longitude)
SET
    case_id = NULLIF(@case_id, ''),
    address_id = NULLIF(@address_id, '') + 0,
    street_number_end = NULLIF(@street_number_end, ''),
    unit = NULLIF(@unit, ''),
    neighborhood = NULLIF(@neighborhood, ''),
    public_works_district = NULLIF(@public_works_district, ''),
    city_council_district = NULLIF(@city_council_district, '') + 0,
    fire_district = NULLIF(@fire_district, '') + 0,
    police_district = NULLIF(@police_district, ''),
    ward = NULLIF(@ward, ''),
    precinct = NULLIF(@precinct, ''),
    latitude = NULLIF(@latitude, ''),
    longitude = NULLIF(@longitude, '');

-- Row counts: compare with the counts normalize_all.py prints / the README
SELECT 'zip_codes' AS table_name, COUNT(*) AS row_count FROM zip_codes
UNION ALL
SELECT 'addresses' AS table_name, COUNT(*) AS row_count FROM addresses
UNION ALL
SELECT 'license_categories' AS table_name, COUNT(*) AS row_count FROM license_categories
UNION ALL
SELECT 'isd_locations' AS table_name, COUNT(*) AS row_count FROM isd_locations
UNION ALL
SELECT 'isd_licenses' AS table_name, COUNT(*) AS row_count FROM isd_licenses
UNION ALL
SELECT 'food_permits' AS table_name, COUNT(*) AS row_count FROM food_permits
UNION ALL
SELECT 'food_permit_licenses' AS table_name, COUNT(*) AS row_count FROM food_permit_licenses
UNION ALL
SELECT 'result_labels' AS table_name, COUNT(*) AS row_count FROM result_labels
UNION ALL
SELECT 'inspection_results' AS table_name, COUNT(*) AS row_count FROM inspection_results
UNION ALL
SELECT 'inspections' AS table_name, COUNT(*) AS row_count FROM inspections
UNION ALL
SELECT 'severity_levels' AS table_name, COUNT(*) AS row_count FROM severity_levels
UNION ALL
SELECT 'violation_types' AS table_name, COUNT(*) AS row_count FROM violation_types
UNION ALL
SELECT 'inspection_violations' AS table_name, COUNT(*) AS row_count FROM inspection_violations
UNION ALL
SELECT 'lb_alcohol_types' AS table_name, COUNT(*) AS row_count FROM lb_alcohol_types
UNION ALL
SELECT 'lb_license_types' AS table_name, COUNT(*) AS row_count FROM lb_license_types
UNION ALL
SELECT 'lb_licenses' AS table_name, COUNT(*) AS row_count FROM lb_licenses
UNION ALL
SELECT 'lb_license_managers' AS table_name, COUNT(*) AS row_count FROM lb_license_managers
UNION ALL
SELECT 'michelin_awards' AS table_name, COUNT(*) AS row_count FROM michelin_awards
UNION ALL
SELECT 'michelin_restaurants' AS table_name, COUNT(*) AS row_count FROM michelin_restaurants
UNION ALL
SELECT 'michelin_facilities' AS table_name, COUNT(*) AS row_count FROM michelin_facilities
UNION ALL
SELECT 'departments' AS table_name, COUNT(*) AS row_count FROM departments
UNION ALL
SELECT 'teams' AS table_name, COUNT(*) AS row_count FROM teams
UNION ALL
SELECT 'service_types' AS table_name, COUNT(*) AS row_count FROM service_types
UNION ALL
SELECT 'service_cases' AS table_name, COUNT(*) AS row_count FROM service_cases
UNION ALL
SELECT 'case_locations' AS table_name, COUNT(*) AS row_count FROM case_locations;