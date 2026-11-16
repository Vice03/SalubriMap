-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Runs once, on the first start of an empty volume.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE DATABASE salubri_test OWNER salubri;
\connect salubri_test
CREATE EXTENSION IF NOT EXISTS postgis;
