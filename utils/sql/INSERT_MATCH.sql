BEGIN TRANSACTION;

INSERT INTO matches(match_id, start_time, game_mode) values
    (:match_id, :start_time, :game_mode);

UPDATE ab_players
SET last_played = :start_time
WHERE player_id = :played_id and last_played < :start_time;

END;
