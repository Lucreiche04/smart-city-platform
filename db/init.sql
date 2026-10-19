-- Schéma de la plateforme Smart City
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Points de mesure : stations officielles (API) et capteurs IoT virtuels.
-- RGPD : position arrondie au centre du quartier, jamais d'adresse précise.
CREATE TABLE stations (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    zone        TEXT NOT NULL,
    lat         DOUBLE PRECISION NOT NULL,
    lon         DOUBLE PRECISION NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('api', 'iot'))
);

-- Mesures au format "long" : une ligne = un polluant à un instant.
-- Permet de filtrer par polluant (US-005) sans changer le schéma si on ajoute un polluant.
CREATE TABLE measurements (
    time          TIMESTAMPTZ NOT NULL,
    station_id    INT NOT NULL REFERENCES stations(id),
    pollutant     TEXT NOT NULL,          -- pm25, pm10, no2, o3, so2, temperature, humidity
    value         DOUBLE PRECISION NOT NULL,
    source        TEXT NOT NULL,          -- aqicn | iot | csv
    is_anomaly    BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_score DOUBLE PRECISION,
    PRIMARY KEY (time, station_id, pollutant)
);
SELECT create_hypertable('measurements', 'time');
CREATE INDEX ON measurements (pollutant, time DESC);

CREATE TABLE weather (
    time         TIMESTAMPTZ PRIMARY KEY,
    temperature  DOUBLE PRECISION,
    humidity     DOUBLE PRECISION,
    wind_speed   DOUBLE PRECISION,
    pressure     DOUBLE PRECISION
);
SELECT create_hypertable('weather', 'time');

CREATE TABLE mobility (
    time              TIMESTAMPTZ PRIMARY KEY,
    traffic_index     DOUBLE PRECISION,   -- 0-100 (simulé si pas d'API)
    transit_ridership INT
);
SELECT create_hypertable('mobility', 'time');

CREATE TABLE predictions (
    id           SERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    target_date  DATE NOT NULL,
    pollutant    TEXT NOT NULL DEFAULT 'pm25',
    value        DOUBLE PRECISION NOT NULL,
    lower_bound  DOUBLE PRECISION,
    upper_bound  DOUBLE PRECISION,
    model        TEXT NOT NULL,
    reliability  DOUBLE PRECISION          -- 1 - MAPE mesurée sur le jeu de test
);

-- Seuils paramétrables (critère final "seuil paramétrable")
CREATE TABLE thresholds (
    pollutant TEXT PRIMARY KEY,
    value     DOUBLE PRECISION NOT NULL
);
INSERT INTO thresholds VALUES ('pm25', 50), ('pm10', 80), ('no2', 200);

CREATE TABLE alerts (
    id          SERIAL PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL DEFAULT now(),
    station_id  INT REFERENCES stations(id),
    pollutant   TEXT NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    threshold   DOUBLE PRECISION NOT NULL,
    email_sent  BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin'
);

-- Abonnés citoyens aux alertes : seule donnée personnelle (email).
-- Droit à l'oubli : DELETE /api/subscribers/{email}
CREATE TABLE subscribers (
    id         SERIAL PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Journal de sécurité (traçabilité des accès et actions sensibles)
CREATE TABLE audit_logs (
    id       SERIAL PRIMARY KEY,
    time     TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor    TEXT NOT NULL,
    action   TEXT NOT NULL,
    ip       TEXT,
    details  TEXT
);

-- Rétention : on garde 1 an de mesures brutes
SELECT add_retention_policy('measurements', INTERVAL '365 days');

-- Stations de Paris : 1 station "API" + 3 capteurs IoT virtuels
INSERT INTO stations (code, name, zone, lat, lon, kind) VALUES
 ('aqicn-paris', 'Station AQICN Paris', 'Paris centre', 48.857, 2.352, 'api'),
 ('iot-01', 'Capteur Nord', 'Paris 18e', 48.892, 2.348, 'iot'),
 ('iot-02', 'Capteur Est',  'Paris 11e', 48.859, 2.380, 'iot'),
 ('iot-03', 'Capteur Sud',  'Paris 14e', 48.829, 2.323, 'iot');
