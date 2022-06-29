CREATE TABLE IF NOT EXISTS matches (
    match_id INT PRIMARY KEY,
    start_time INT,
    game_mode INT,
    leaver_status INT,
    duration INT,
);

CREATE TABLE IF NOT EXISTS match_players (
    match_id INT PRIMARY KEY,
    player_id INT,
    position INT,
    hero_id INT
);

/* A list of Ability Draft players used, to find matches */
CREATE TABLE IF NOT EXISTS ab_players (
    player_id INT PRIMARY KEY,
    last_searched INT,
    last_played INT
)

CREATE TABLE IF NOT EXISTS match_details (

)
