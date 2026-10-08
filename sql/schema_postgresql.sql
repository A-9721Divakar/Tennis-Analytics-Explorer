-- Game Analytics: Unlocking Tennis Data with the Sportradar API
-- PostgreSQL schema

CREATE TABLE categories (
    category_id VARCHAR(50) NOT NULL, 
    category_name VARCHAR(100) NOT NULL, 
    PRIMARY KEY (category_id)
);

CREATE TABLE competitors (
    competitor_id VARCHAR(50) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    country VARCHAR(100) NOT NULL, 
    country_code CHAR(3) NOT NULL, 
    abbreviation VARCHAR(10) NOT NULL, 
    PRIMARY KEY (competitor_id)
);
CREATE INDEX ix_competitors_country ON competitors (country);

CREATE TABLE complexes (
    complex_id VARCHAR(50) NOT NULL, 
    complex_name VARCHAR(100) NOT NULL, 
    PRIMARY KEY (complex_id)
);

CREATE TABLE etl_runs (
    run_id SERIAL NOT NULL, 
    run_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    dataset VARCHAR(30) NOT NULL, 
    source VARCHAR(20) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    rows_loaded INTEGER DEFAULT '0' NOT NULL, 
    message VARCHAR(500), 
    PRIMARY KEY (run_id)
);

CREATE TABLE competitions (
    competition_id VARCHAR(50) NOT NULL, 
    competition_name VARCHAR(100) NOT NULL, 
    parent_id VARCHAR(50), 
    type VARCHAR(20) NOT NULL, 
    gender VARCHAR(10) NOT NULL, 
    category_id VARCHAR(50), 
    PRIMARY KEY (competition_id), 
    FOREIGN KEY(category_id) REFERENCES categories (category_id)
);
CREATE INDEX ix_competitions_category_id ON competitions (category_id);
CREATE INDEX ix_competitions_parent_id ON competitions (parent_id);
CREATE INDEX ix_competitions_type_gender ON competitions (type, gender);

CREATE TABLE competitor_rankings (
    rank_id SERIAL NOT NULL, 
    rank INTEGER NOT NULL, 
    movement INTEGER NOT NULL, 
    points INTEGER NOT NULL, 
    competitions_played INTEGER NOT NULL, 
    competitor_id VARCHAR(50) NOT NULL, 
    ranking_name VARCHAR(50) DEFAULT 'doubles' NOT NULL, 
    ranking_year INTEGER NOT NULL, 
    ranking_week INTEGER NOT NULL, 
    gender VARCHAR(10) NOT NULL, 
    PRIMARY KEY (rank_id), 
    FOREIGN KEY(competitor_id) REFERENCES competitors (competitor_id)
);
CREATE INDEX ix_rankings_competitor ON competitor_rankings (competitor_id);
CREATE INDEX ix_rankings_rank ON competitor_rankings (rank);
CREATE INDEX ix_rankings_snapshot ON competitor_rankings (ranking_year, ranking_week, gender);

CREATE TABLE venues (
    venue_id VARCHAR(50) NOT NULL, 
    venue_name VARCHAR(100) NOT NULL, 
    city_name VARCHAR(100) NOT NULL, 
    country_name VARCHAR(100) NOT NULL, 
    country_code CHAR(3) NOT NULL, 
    timezone VARCHAR(100) NOT NULL, 
    complex_id VARCHAR(50), 
    PRIMARY KEY (venue_id), 
    FOREIGN KEY(complex_id) REFERENCES complexes (complex_id)
);
CREATE INDEX ix_venues_complex_id ON venues (complex_id);
CREATE INDEX ix_venues_country_name ON venues (country_name);

CREATE VIEW vw_latest_rankings AS
    SELECT cr.rank_id, cr.rank AS rank, cr.movement, cr.points,
           cr.competitions_played, cr.competitor_id, cr.ranking_name,
           cr.ranking_year, cr.ranking_week, cr.gender
    FROM competitor_rankings cr
    WHERE (cr.ranking_year * 100 + cr.ranking_week) = (
        SELECT MAX(x.ranking_year * 100 + x.ranking_week)
        FROM competitor_rankings x
        WHERE x.gender = cr.gender
    );
