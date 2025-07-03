-- Building
INSERT INTO brick_entities VALUES
('building_main', 'building', 'brick:Building', 'Main Office Building', NULL, '{}');

-- Floors
INSERT INTO brick_entities VALUES
('floor_1', 'floor', 'brick:Floor', 'Floor 1', 'building_main', '{}'),
('floor_2', 'floor', 'brick:Floor', 'Floor 2', 'building_main', '{}');

-- Zones (5 per floor)
INSERT INTO brick_entities VALUES
('zone_1_1', 'zone', 'brick:HVAC_Zone', 'Zone 1-1', 'floor_1', '{}'),
('zone_1_2', 'zone', 'brick:HVAC_Zone', 'Zone 1-2', 'floor_1', '{}'),
('zone_1_3', 'zone', 'brick:HVAC_Zone', 'Zone 1-3', 'floor_1', '{}'),
('zone_1_4', 'zone', 'brick:HVAC_Zone', 'Zone 1-4', 'floor_1', '{}'),
('zone_1_5', 'zone', 'brick:HVAC_Zone', 'Zone 1-5', 'floor_1', '{}'),
('zone_2_1', 'zone', 'brick:HVAC_Zone', 'Zone 2-1', 'floor_2', '{}'),
('zone_2_2', 'zone', 'brick:HVAC_Zone', 'Zone 2-2', 'floor_2', '{}'),
('zone_2_3', 'zone', 'brick:HVAC_Zone', 'Zone 2-3', 'floor_2', '{}'),
('zone_2_4', 'zone', 'brick:HVAC_Zone', 'Zone 2-4', 'floor_2', '{}'),
('zone_2_5', 'zone', 'brick:HVAC_Zone', 'Zone 2-5', 'floor_2', '{}');

-- IAQ Sensors (1 per zone)
INSERT INTO brick_entities VALUES
('iaq_001', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 001', NULL, '{"zone": "zone_1_1"}'),
('iaq_002', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 002', NULL, '{"zone": "zone_1_2"}'),
('iaq_003', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 003', NULL, '{"zone": "zone_1_3"}'),
('iaq_004', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 004', NULL, '{"zone": "zone_1_4"}'),
('iaq_005', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 005', NULL, '{"zone": "zone_1_5"}'),
('iaq_006', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 006', NULL, '{"zone": "zone_2_1"}'),
('iaq_007', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 007', NULL, '{"zone": "zone_2_2"}'),
('iaq_008', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 008', NULL, '{"zone": "zone_2_3"}'),
('iaq_009', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 009', NULL, '{"zone": "zone_2_4"}'),
('iaq_010', 'sensor', 'brick:Air_Quality_Sensor', 'IAQ Sensor 010', NULL, '{"zone": "zone_2_5"}');

-- Power Meters
INSERT INTO brick_entities VALUES
('pm_001', 'meter', 'brick:Electrical_Meter', 'Power Meter Floor 1', NULL, '{"feeds": "floor_1"}'),
('pm_002', 'meter', 'brick:Electrical_Meter', 'Power Meter Floor 2', NULL, '{"feeds": "floor_2"}'),
('pm_003', 'meter', 'brick:Electrical_Meter', 'Power Meter Main', NULL, '{"feeds": "building_main"}'),
('pm_004', 'meter', 'brick:Electrical_Meter', 'Power Meter Chiller', NULL, '{"feeds": "chiller"}'),
('pm_005', 'meter', 'brick:Electrical_Meter', 'Power Meter Elevator', NULL, '{"feeds": "elevator"}');

-- Relationships: Sensors located in zones
INSERT INTO brick_relationships VALUES
('iaq_001', 'brick:hasLocation', 'zone_1_1'),
('iaq_002', 'brick:hasLocation', 'zone_1_2'),
('iaq_003', 'brick:hasLocation', 'zone_1_3'),
('iaq_004', 'brick:hasLocation', 'zone_1_4'),
('iaq_005', 'brick:hasLocation', 'zone_1_5'),
('iaq_006', 'brick:hasLocation', 'zone_2_1'),
('iaq_007', 'brick:hasLocation', 'zone_2_2'),
('iaq_008', 'brick:hasLocation', 'zone_2_3'),
('iaq_009', 'brick:hasLocation', 'zone_2_4'),
('iaq_010', 'brick:hasLocation', 'zone_2_5');

-- Power meters feed floors/building
INSERT INTO brick_relationships VALUES
('pm_001', 'brick:feeds', 'floor_1'),
('pm_002', 'brick:feeds', 'floor_2'),
('pm_003', 'brick:feeds', 'building_main'),
('pm_004', 'brick:feeds', 'chiller'),
('pm_005', 'brick:feeds', 'elevator');

-- Zone/floor/building hierarchy
INSERT INTO brick_relationships VALUES
('zone_1_1', 'brick:isPartOf', 'floor_1'),
('zone_1_2', 'brick:isPartOf', 'floor_1'),
('zone_1_3', 'brick:isPartOf', 'floor_1'),
('zone_1_4', 'brick:isPartOf', 'floor_1'),
('zone_1_5', 'brick:isPartOf', 'floor_1'),
('zone_2_1', 'brick:isPartOf', 'floor_2'),
('zone_2_2', 'brick:isPartOf', 'floor_2'),
('zone_2_3', 'brick:isPartOf', 'floor_2'),
('zone_2_4', 'brick:isPartOf', 'floor_2'),
('zone_2_5', 'brick:isPartOf', 'floor_2'),
('floor_1', 'brick:isPartOf', 'building_main'),
('floor_2', 'brick:isPartOf', 'building_main');

-- Measurement Points for IAQ Sensors
INSERT INTO brick_points VALUES
('iaq_001_co2', 'iaq_001', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_001_temp', 'iaq_001', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_001_humid', 'iaq_001', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_002_co2', 'iaq_002', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_002_temp', 'iaq_002', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_002_humid', 'iaq_002', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_003_co2', 'iaq_003', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_003_temp', 'iaq_003', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_003_humid', 'iaq_003', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_004_co2', 'iaq_004', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_004_temp', 'iaq_004', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_004_humid', 'iaq_004', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_005_co2', 'iaq_005', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_005_temp', 'iaq_005', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_005_humid', 'iaq_005', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_006_co2', 'iaq_006', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_006_temp', 'iaq_006', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_006_humid', 'iaq_006', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_007_co2', 'iaq_007', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_007_temp', 'iaq_007', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_007_humid', 'iaq_007', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_008_co2', 'iaq_008', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_008_temp', 'iaq_008', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_008_humid', 'iaq_008', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_009_co2', 'iaq_009', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_009_temp', 'iaq_009', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_009_humid', 'iaq_009', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80),
('iaq_010_co2', 'iaq_010', 'co2', 'brick:Carbon_Dioxide_Concentration', 'ppm', 400, 5000),
('iaq_010_temp', 'iaq_010', 'temperature', 'brick:Air_Temperature', 'degreesCelsius', 15, 35),
('iaq_010_humid', 'iaq_010', 'humidity', 'brick:Relative_Humidity', 'percent', 20, 80);

-- Measurement Points for Power Meters (repeat for all 5)
INSERT INTO brick_points VALUES
('pm_001_power', 'pm_001', 'power', 'brick:Electric_Power', 'kilowatt', 0, 100),
('pm_002_power', 'pm_002', 'power', 'brick:Electric_Power', 'kilowatt', 0, 100),
('pm_003_power', 'pm_003', 'power', 'brick:Electric_Power', 'kilowatt', 0, 100),
('pm_004_power', 'pm_004', 'power', 'brick:Electric_Power', 'kilowatt', 0, 100),
('pm_005_power', 'pm_005', 'power', 'brick:Electric_Power', 'kilowatt', 0, 100);