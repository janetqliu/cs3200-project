SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS addresses_std;
DROP TABLE IF EXISTS case_locations;
DROP TABLE IF EXISTS service_cases;
DROP TABLE IF EXISTS service_types;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS michelin_facilities;
DROP TABLE IF EXISTS michelin_restaurants;
DROP TABLE IF EXISTS michelin_awards;
DROP TABLE IF EXISTS lb_license_managers;
DROP TABLE IF EXISTS lb_licenses;
DROP TABLE IF EXISTS lb_license_types;
DROP TABLE IF EXISTS lb_alcohol_types;
DROP TABLE IF EXISTS inspection_violations;
DROP TABLE IF EXISTS violation_types;
DROP TABLE IF EXISTS severity_levels;
DROP TABLE IF EXISTS inspections;
DROP TABLE IF EXISTS inspection_results;
DROP TABLE IF EXISTS result_labels;
DROP TABLE IF EXISTS food_permit_licenses;
DROP TABLE IF EXISTS food_permits;
DROP TABLE IF EXISTS isd_licenses;
DROP TABLE IF EXISTS isd_locations;
DROP TABLE IF EXISTS license_categories;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS zip_codes;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE zip_codes (
    zip_code VARCHAR(255),
    in_boston BOOLEAN,
    PRIMARY KEY (zip_code)
);

CREATE TABLE addresses (
    address_id INT,
    address_key TEXT,
    street_number TEXT,
    street_direction TEXT,
    street_name TEXT,
    street_suffix TEXT,
    zip_code VARCHAR(255),
    PRIMARY KEY (address_id),
    FOREIGN KEY (zip_code) REFERENCES zip_codes(zip_code)
);

CREATE TABLE license_categories (
    category_code VARCHAR(255),
    category_description TEXT,
    PRIMARY KEY (category_code)
);

CREATE TABLE isd_locations (
    location_id INT,
    address_id INT,
    street_number_end TEXT,
    neighborhood TEXT,
    property_id INT,
    latitude DOUBLE,
    longitude DOUBLE,
    PRIMARY KEY (location_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE TABLE isd_licenses (
    licenseno VARCHAR(255),
    business_name TEXT,
    dba_name TEXT,
    name_key TEXT,
    legal_owner TEXT,
    owner_last TEXT,
    owner_first TEXT,
    category_code VARCHAR(255),
    license_status TEXT,
    issued_at TEXT,
    expires_at TEXT,
    location_id INT,
    phone TEXT,
    PRIMARY KEY (licenseno),
    FOREIGN KEY (category_code) REFERENCES license_categories(category_code),
    FOREIGN KEY (location_id) REFERENCES isd_locations(location_id)
);

CREATE TABLE food_permits (
    permit_id INT,
    business_name TEXT,
    dba_name TEXT,
    name_key TEXT,
    category_code VARCHAR(255),
    license_status TEXT,
    license_added_at TEXT,
    address_id INT,
    street_number_end TEXT,
    neighborhood TEXT,
    property_id INT,
    latitude DOUBLE,
    longitude DOUBLE,
    phone TEXT,
    PRIMARY KEY (permit_id),
    FOREIGN KEY (category_code) REFERENCES license_categories(category_code),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE TABLE food_permit_licenses (
    permit_id INT,
    licenseno VARCHAR(255),
    match_method TEXT,
    PRIMARY KEY (permit_id),
    FOREIGN KEY (permit_id) REFERENCES food_permits(permit_id),
    FOREIGN KEY (licenseno) REFERENCES isd_licenses(licenseno)
);

CREATE TABLE result_labels (
    result_label VARCHAR(255),
    outcome TEXT,
    PRIMARY KEY (result_label)
);

CREATE TABLE inspection_results (
    result_code VARCHAR(255),
    result_label VARCHAR(255),
    PRIMARY KEY (result_code),
    FOREIGN KEY (result_label) REFERENCES result_labels(result_label)
);

CREATE TABLE inspections (
    inspection_id INT,
    licenseno VARCHAR(255),
    inspected_at TEXT,
    result_code VARCHAR(255),
    PRIMARY KEY (inspection_id),
    FOREIGN KEY (licenseno) REFERENCES isd_licenses(licenseno),
    FOREIGN KEY (result_code) REFERENCES inspection_results(result_code)
);

CREATE TABLE severity_levels (
    severity_level VARCHAR(255),
    severity_label TEXT,
    severity_rank INT,
    PRIMARY KEY (severity_level)
);

CREATE TABLE violation_types (
    violation_code VARCHAR(255),
    severity_level VARCHAR(255),
    description TEXT,
    PRIMARY KEY (violation_code),
    FOREIGN KEY (severity_level) REFERENCES severity_levels(severity_level)
);

CREATE TABLE inspection_violations (
    violation_id INT,
    inspection_id INT,
    violation_code VARCHAR(255),
    violation_status TEXT,
    violation_at TEXT,
    status_changed_at TEXT,
    comments TEXT,
    PRIMARY KEY (violation_id),
    FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id),
    FOREIGN KEY (violation_code) REFERENCES violation_types(violation_code)
);

CREATE TABLE lb_alcohol_types (
    alcohol_type VARCHAR(255),
    serves_alcohol BOOLEAN,
    PRIMARY KEY (alcohol_type)
);

CREATE TABLE lb_license_types (
    license_type VARCHAR(255),
    license_category TEXT,
    alcohol_type VARCHAR(255),
    PRIMARY KEY (license_type),
    FOREIGN KEY (alcohol_type) REFERENCES lb_alcohol_types(alcohol_type)
);

CREATE TABLE lb_licenses (
    license_num VARCHAR(255),
    historical_license_num TEXT,
    status TEXT,
    license_type VARCHAR(255),
    issued_date TEXT,
    expires_date TEXT,
    business_name TEXT,
    dba_name TEXT,
    name_key TEXT,
    business_name_key TEXT,
    applicant TEXT,
    opening_time TEXT,
    closing_time TEXT,
    patrons_out_time TEXT,
    open_24_hours BOOLEAN,
    hours_note TEXT,
    capacity INT,
    comments TEXT,
    location_comments TEXT,
    premises_description TEXT,
    day_phone TEXT,
    day_phone_ext TEXT,
    evening_phone TEXT,
    address_id INT,
    street_number_end TEXT,
    neighborhood TEXT,
    latitude DOUBLE,
    longitude DOUBLE,
    PRIMARY KEY (license_num),
    FOREIGN KEY (license_type) REFERENCES lb_license_types(license_type),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE TABLE lb_license_managers (
    license_num VARCHAR(255),
    manager VARCHAR(255),
    PRIMARY KEY (license_num, manager),
    FOREIGN KEY (license_num) REFERENCES lb_licenses(license_num)
);

CREATE TABLE michelin_awards (
    award VARCHAR(255),
    stars INT,
    is_bib_gourmand BOOLEAN,
    PRIMARY KEY (award)
);

CREATE TABLE michelin_restaurants (
    michelin_id VARCHAR(255),
    name TEXT,
    name_key TEXT,
    cuisine TEXT,
    price TEXT,
    award VARCHAR(255),
    green_star BOOLEAN,
    address_id INT,
    unit TEXT,
    latitude DOUBLE,
    longitude DOUBLE,
    website_url TEXT,
    michelin_url TEXT,
    description TEXT,
    PRIMARY KEY (michelin_id),
    FOREIGN KEY (award) REFERENCES michelin_awards(award),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE TABLE michelin_facilities (
    michelin_id VARCHAR(255),
    facility VARCHAR(255),
    PRIMARY KEY (michelin_id, facility),
    FOREIGN KEY (michelin_id) REFERENCES michelin_restaurants(michelin_id)
);

CREATE TABLE departments (
    department_id INT,
    department_name TEXT,
    PRIMARY KEY (department_id)
);

CREATE TABLE teams (
    team_id INT,
    team_name TEXT,
    department_id INT,
    PRIMARY KEY (team_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE service_types (
    service_type_id INT,
    service_name TEXT,
    PRIMARY KEY (service_type_id)
);

CREATE TABLE service_cases (
    case_id VARCHAR(255),
    service_type_id INT,
    team_id INT,
    case_status TEXT,
    open_date TEXT,
    target_close_date TEXT,
    close_date TEXT,
    on_time TEXT,
    closure_reason TEXT,
    closure_comments TEXT,
    report_source TEXT,
    PRIMARY KEY (case_id),
    FOREIGN KEY (service_type_id) REFERENCES service_types(service_type_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

CREATE TABLE case_locations (
    case_id VARCHAR(255),
    address_id INT,
    street_number_end TEXT,
    unit TEXT,
    neighborhood TEXT,
    public_works_district TEXT,
    city_council_district INT,
    fire_district INT,
    police_district TEXT,
    ward TEXT,
    precinct TEXT,
    latitude DOUBLE,
    longitude DOUBLE,
    PRIMARY KEY (case_id),
    FOREIGN KEY (case_id) REFERENCES service_cases(case_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

-- Display form of an address, derived from its parts (kept out of the base table for 3NF)
CREATE VIEW addresses_std AS
SELECT a.*,
       CONCAT_WS(' ', street_number, street_direction, street_name, street_suffix) AS address_std
FROM addresses a;