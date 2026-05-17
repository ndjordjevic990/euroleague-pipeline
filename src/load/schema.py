"""Database schema for the Euroleague data warehouse."""

SCHEMA_SQL = """

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_teams (
    team_code       VARCHAR PRIMARY KEY,
    team_name       VARCHAR         -- Most recent name
);

CREATE TABLE IF NOT EXISTS dim_players (
    player_id       VARCHAR PRIMARY KEY,
    player_name     VARCHAR,
    position        VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_games (
    game_key        VARCHAR PRIMARY KEY,  -- e.g. 'E2024_001'
    season_code     VARCHAR NOT NULL,
    game_code       INTEGER NOT NULL,
    date            DATE,
    hour            VARCHAR,
    stadium         VARCHAR,
    capacity        INTEGER,
    team_a_code     VARCHAR REFERENCES dim_teams(team_code),
    team_b_code     VARCHAR REFERENCES dim_teams(team_code),
    team_a_name     VARCHAR,
    team_b_name     VARCHAR,
    score_a         INTEGER,
    score_b         INTEGER,
    score_q1_a      INTEGER,
    score_q1_b      INTEGER,
    score_q2_a      INTEGER,
    score_q2_b      INTEGER,
    score_q3_a      INTEGER,
    score_q3_b      INTEGER,
    score_q4_a      INTEGER,
    score_q4_b      INTEGER,
    score_ot_a      INTEGER,
    score_ot_b      INTEGER,
    coach_a         VARCHAR,
    coach_b         VARCHAR,
    referee_1       VARCHAR,
    referee_2       VARCHAR,
    referee_3       VARCHAR,
    phase           VARCHAR,
    round           VARCHAR,
    fouls_a         INTEGER,
    fouls_b         INTEGER,
    timeouts_a      INTEGER,
    timeouts_b      INTEGER,
    attendance      INTEGER,
    UNIQUE(season_code, game_code)
);

-- ============================================================
-- FACT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_events (
    game_key        VARCHAR NOT NULL REFERENCES dim_games(game_key),
    event_id        INTEGER NOT NULL,
    quarter         INTEGER,
    game_clock      VARCHAR,
    utc             VARCHAR,
    team_code       VARCHAR,
    player_id       VARCHAR,
    player_name     VARCHAR,
    jersey_number   VARCHAR,
    play_type       VARCHAR NOT NULL,
    play_info       VARCHAR,
    -- Parsed fields
    made            INTEGER,        -- shot: made count
    attempted       INTEGER,        -- shot: attempted count
    player_total_points INTEGER,    -- shot: player's cumulative points
    cumulative_count INTEGER,       -- non-shot: cumulative stat count
    -- Score state
    score_a         INTEGER,
    score_b         INTEGER,
    -- Shot data (from Points API merge)
    coord_x         INTEGER,
    coord_y         INTEGER,
    zone            VARCHAR,
    is_fastbreak    BOOLEAN DEFAULT FALSE,
    is_second_chance BOOLEAN DEFAULT FALSE,
    is_off_turnover BOOLEAN DEFAULT FALSE,
    -- Lineup state
    lineup_a        VARCHAR[],      -- Array of player_ids
    lineup_b        VARCHAR[],
    PRIMARY KEY (game_key, event_id)
);

CREATE TABLE IF NOT EXISTS fact_boxscore (
    game_key        VARCHAR NOT NULL REFERENCES dim_games(game_key),
    player_id       VARCHAR NOT NULL,
    team_code       VARCHAR,
    player_name     VARCHAR,
    is_starter      BOOLEAN,
    minutes_seconds INTEGER,        -- NULL = DNP
    points          INTEGER DEFAULT 0,
    fg2m            INTEGER DEFAULT 0,
    fg2a            INTEGER DEFAULT 0,
    fg3m            INTEGER DEFAULT 0,
    fg3a            INTEGER DEFAULT 0,
    ftm             INTEGER DEFAULT 0,
    fta             INTEGER DEFAULT 0,
    off_rebounds     INTEGER DEFAULT 0,
    def_rebounds     INTEGER DEFAULT 0,
    total_rebounds   INTEGER DEFAULT 0,
    assists         INTEGER DEFAULT 0,
    steals          INTEGER DEFAULT 0,
    turnovers       INTEGER DEFAULT 0,
    blocks_made     INTEGER DEFAULT 0,
    blocks_against  INTEGER DEFAULT 0,
    fouls_committed INTEGER DEFAULT 0,
    fouls_drawn     INTEGER DEFAULT 0,
    pir             INTEGER DEFAULT 0,
    plus_minus      INTEGER DEFAULT 0,
    PRIMARY KEY (game_key, player_id)
);

CREATE TABLE IF NOT EXISTS fact_score_evolution (
    game_key        VARCHAR NOT NULL REFERENCES dim_games(game_key),
    minute          INTEGER NOT NULL,
    score_a         INTEGER,
    score_b         INTEGER,
    PRIMARY KEY (game_key, minute)
);

CREATE TABLE IF NOT EXISTS fact_shooting (
    game_key            VARCHAR NOT NULL PRIMARY KEY REFERENCES dim_games(game_key),
    fastbreak_points_a  INTEGER DEFAULT 0,
    fastbreak_points_b  INTEGER DEFAULT 0,
    turnover_points_a   INTEGER DEFAULT 0,
    turnover_points_b   INTEGER DEFAULT 0,
    second_chance_points_a INTEGER DEFAULT 0,
    second_chance_points_b INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fact_comparison (
    game_key            VARCHAR NOT NULL PRIMARY KEY REFERENCES dim_games(game_key),
    off_rebounds_a      INTEGER,
    off_rebounds_b      INTEGER,
    def_rebounds_a      INTEGER,
    def_rebounds_b      INTEGER,
    points_starters_a   INTEGER,
    points_bench_a      INTEGER,
    points_starters_b   INTEGER,
    points_bench_b      INTEGER,
    assists_starters_a  INTEGER,
    assists_bench_a     INTEGER,
    assists_starters_b  INTEGER,
    assists_bench_b     INTEGER,
    steals_starters_a   INTEGER,
    steals_bench_a      INTEGER,
    steals_starters_b   INTEGER,
    steals_bench_b      INTEGER,
    turnovers_starters_a INTEGER,
    turnovers_bench_a   INTEGER,
    turnovers_starters_b INTEGER,
    turnovers_bench_b   INTEGER,
    max_lead_a          INTEGER,
    max_lead_b          INTEGER,
    max_run_a           INTEGER,
    max_run_b           INTEGER
);

"""