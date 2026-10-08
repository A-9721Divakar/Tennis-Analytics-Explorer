-- Game Analytics: Unlocking Tennis Data with the Sportradar API
-- All analysis queries (PostgreSQL syntax; parameters shown with their default values)
-- 'rank' is quoted because it is a reserved word in MySQL 8: use `rank` there.


-- ======================================================================
-- COMPETITIONS
-- ======================================================================

-- C1. List all competitions with their category name
-- Joins competitions to categories.
SELECT c.competition_id, c.competition_name, c.type, c.gender, cat.category_name
FROM competitions c
LEFT JOIN categories cat ON cat.category_id = c.category_id
ORDER BY cat.category_name, c.competition_name;

-- C2. Count the number of competitions in each category
-- Aggregates competitions per category (categories with zero competitions included).
SELECT cat.category_name, COUNT(c.competition_id) AS total_competitions
FROM categories cat
LEFT JOIN competitions c ON c.category_id = cat.category_id
GROUP BY cat.category_id, cat.category_name
ORDER BY total_competitions DESC, cat.category_name;

-- C3. Find all competitions of type 'doubles'
-- Filters by competition type (default: doubles).
SELECT c.competition_id, c.competition_name, c.gender, cat.category_name
FROM competitions c
LEFT JOIN categories cat ON cat.category_id = c.category_id
WHERE LOWER(c.type) = LOWER('doubles')
ORDER BY cat.category_name, c.competition_name;

-- C4. Get competitions that belong to a specific category (e.g. ITF Men)
-- Filters competitions by category name.
SELECT c.competition_id, c.competition_name, c.type, c.gender
FROM competitions c
JOIN categories cat ON cat.category_id = c.category_id
WHERE LOWER(cat.category_name) = LOWER('ITF Men')
ORDER BY c.competition_name;

-- C5. Identify parent competitions and their sub-competitions
-- Self-join on parent_id links every sub-competition to its parent.
SELECT p.competition_id AS parent_id, p.competition_name AS parent_competition,
       c.competition_id AS sub_competition_id, c.competition_name AS sub_competition,
       c.type, c.gender
FROM competitions c
JOIN competitions p ON p.competition_id = c.parent_id
ORDER BY p.competition_name, c.competition_name;

-- C6. Analyze the distribution of competition types by category
-- Cross-tab of category x type with counts.
SELECT cat.category_name, c.type, COUNT(*) AS total_competitions
FROM competitions c
LEFT JOIN categories cat ON cat.category_id = c.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, total_competitions DESC;

-- C7. List all competitions with no parent (top-level competitions)
-- Top of every competition hierarchy (parent_id IS NULL).
SELECT c.competition_id, c.competition_name, c.type, c.gender, cat.category_name
FROM competitions c
LEFT JOIN categories cat ON cat.category_id = c.category_id
WHERE c.parent_id IS NULL
ORDER BY cat.category_name, c.competition_name;


-- ======================================================================
-- VENUES & COMPLEXES
-- ======================================================================

-- V1. List all venues along with their associated complex name
-- Joins venues to complexes.
SELECT v.venue_id, v.venue_name, v.city_name, v.country_name, cx.complex_name
FROM venues v
LEFT JOIN complexes cx ON cx.complex_id = v.complex_id
ORDER BY cx.complex_name, v.venue_name;

-- V2. Count the number of venues in each complex
-- Aggregates venues per complex.
SELECT cx.complex_id, cx.complex_name, COUNT(v.venue_id) AS total_venues
FROM complexes cx
LEFT JOIN venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
ORDER BY total_venues DESC, cx.complex_name;

-- V3. Get details of venues in a specific country (e.g. Chile)
-- Filters venues by country name.
SELECT v.venue_id, v.venue_name, v.city_name, v.country_name, v.country_code,
       v.timezone, cx.complex_name
FROM venues v
LEFT JOIN complexes cx ON cx.complex_id = v.complex_id
WHERE LOWER(v.country_name) = LOWER('Chile')
ORDER BY v.city_name, v.venue_name;

-- V4. Identify all venues and their timezones
-- Venue name, city and timezone.
SELECT v.venue_name, v.city_name, v.country_name, v.timezone
FROM venues v
ORDER BY v.timezone, v.venue_name;

-- V5. Find complexes that have more than one venue
-- GROUP BY + HAVING on venue count.
SELECT cx.complex_id, cx.complex_name, COUNT(v.venue_id) AS total_venues
FROM complexes cx
JOIN venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
HAVING COUNT(v.venue_id) > 1
ORDER BY total_venues DESC, cx.complex_name;

-- V6. List venues grouped by country
-- Venues ordered so that each country's venues appear together, with counts per country.
SELECT v.country_name, v.country_code, v.city_name, v.venue_name,
       COUNT(*) OVER (PARTITION BY v.country_name) AS venues_in_country
FROM venues v
ORDER BY v.country_name, v.city_name, v.venue_name;

-- V7. Find all venues for a specific complex (e.g. Nacional)
-- Case-insensitive search on complex name.
SELECT cx.complex_name, v.venue_id, v.venue_name, v.city_name, v.country_name
FROM venues v
JOIN complexes cx ON cx.complex_id = v.complex_id
WHERE LOWER(cx.complex_name) LIKE LOWER('%Nacional%')
ORDER BY cx.complex_name, v.venue_name;


-- ======================================================================
-- COMPETITOR RANKINGS
-- ======================================================================

-- R1. Get all competitors with their rank and points
-- Current-week snapshot joined to competitor details.
SELECT c.competitor_id, c.name, c.country, lr."rank" AS rank_pos, lr.points,
       lr.movement, lr.competitions_played, lr.gender
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
ORDER BY lr.gender, lr."rank";

-- R2. Find competitors ranked in the top 5
-- Rank <= 5 in the current snapshot (per gender).
SELECT c.name, c.country, lr."rank" AS rank_pos, lr.points, lr.gender
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
WHERE lr."rank" <= 5
ORDER BY lr.gender, lr."rank";

-- R3. List competitors with no rank movement (stable rank)
-- movement = 0 in the current snapshot.
SELECT c.name, c.country, lr."rank" AS rank_pos, lr.points, lr.gender
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
WHERE lr.movement = 0
ORDER BY lr.gender, lr."rank";

-- R4. Get the total points of competitors from a specific country (e.g. Croatia)
-- Sum of current-week points for one country.
SELECT c.country, COUNT(*) AS competitors, SUM(lr.points) AS total_points,
       ROUND(AVG(lr.points), 1) AS average_points
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
WHERE LOWER(c.country) = LOWER('Croatia')
GROUP BY c.country;

-- R5. Count the number of competitors per country
-- Competitors in the current snapshot grouped by country.
SELECT c.country, c.country_code, COUNT(DISTINCT c.competitor_id) AS total_competitors
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
GROUP BY c.country, c.country_code
ORDER BY total_competitors DESC, c.country;

-- R6. Find competitors with the highest points in the current week
-- Ordered by points, highest first (current snapshot).
SELECT c.name, c.country, lr.points, lr."rank" AS rank_pos, lr.gender,
       lr.ranking_year, lr.ranking_week
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
ORDER BY lr.points DESC, lr."rank";


-- ======================================================================
-- BONUS (ADVANCED)
-- ======================================================================

-- B1. Sub-competition count per parent competition
-- Which tournaments have the most sub-events?
SELECT p.competition_name AS parent_competition, COUNT(c.competition_id) AS sub_competitions
FROM competitions p
JOIN competitions c ON c.parent_id = p.competition_id
GROUP BY p.competition_id, p.competition_name
ORDER BY sub_competitions DESC, parent_competition;

-- B2. Best-ranked competitor from each country (window function)
-- ROW_NUMBER() over each country ordered by points.
SELECT country, name, rank_pos, points
FROM (
    SELECT c.country, c.name, lr."rank" AS rank_pos, lr.points,
           ROW_NUMBER() OVER (PARTITION BY c.country
                              ORDER BY lr.points DESC, lr."rank") AS country_position
    FROM vw_latest_rankings lr
    JOIN competitors c ON c.competitor_id = lr.competitor_id
) ranked
WHERE country_position = 1
ORDER BY points DESC;

-- B3. Biggest rank climbers this week
-- Positive movement = moved up the rankings.
SELECT c.name, c.country, lr."rank" AS rank_pos, lr.movement, lr.points, lr.gender
FROM vw_latest_rankings lr
JOIN competitors c ON c.competitor_id = lr.competitor_id
WHERE lr.movement > 0
ORDER BY lr.movement DESC, lr."rank";

-- B4. Venue count per timezone
-- Geographic spread of venues by timezone.
SELECT v.timezone, COUNT(*) AS total_venues, COUNT(DISTINCT v.country_name) AS countries
FROM venues v
GROUP BY v.timezone
ORDER BY total_venues DESC, v.timezone;
