# ScoreManager.gd
# Tracks individual player scores: kills, deaths, score
extends Node
class_name ScoreManager

var player_scores: Dictionary = {}  # player_index → {kills, deaths, score}

signal score_updated(player_index: int, kills: int, deaths: int, score: int)

func register_player(player_index: int) -> void:
	if not player_index in player_scores:
		player_scores[player_index] = {
			"kills": 0,
			"deaths": 0,
			"score": 0
		}

func add_kill(player_index: int, as_infected: bool = false) -> void:
	if not player_index in player_scores:
		register_player(player_index)

	var s = player_scores[player_index]
	s["kills"] += 1
	s["score"] += 1
	score_updated.emit(player_index, s["kills"], s["deaths"], s["score"])

func add_death(player_index: int) -> void:
	if not player_index in player_scores:
		register_player(player_index)

	var s = player_scores[player_index]
	s["deaths"] += 1
	score_updated.emit(player_index, s["kills"], s["deaths"], s["score"])

func get_score(player_index: int) -> int:
	if player_index in player_scores:
		return player_scores[player_index]["score"]
	return 0

func get_kills(player_index: int) -> int:
	if player_index in player_scores:
		return player_scores[player_index]["kills"]
	return 0

func get_deaths(player_index: int) -> int:
	if player_index in player_scores:
		return player_scores[player_index]["deaths"]
	return 0

func get_lowest_scoring_player() -> int:
	var lowest_idx = -1
	var lowest_score = INF
	for idx in player_scores:
		if player_scores[idx]["score"] < lowest_score:
			lowest_score = player_scores[idx]["score"]
			lowest_idx = idx
	return lowest_idx

func reset() -> void:
	player_scores.clear()