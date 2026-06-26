# TeamManager.gd
# Tracks team assignments, player counts, and score per team
extends Node
class_name TeamManager

var team_humans: Array = []
var team_infected: Array = []
var team_scores: Dictionary = {"humans": 0, "infected": 0}

signal team_changed(player, old_team: String, new_team: String)

func register_player(player) -> void:
	if not player in team_humans and not player in team_infected:
		var team = player.get_team()
		if team == "human":
			team_humans.append(player)
		else:
			team_infected.append(player)

func unregister_player(player) -> void:
	team_humans.erase(player)
	team_infected.erase(player)

func set_player_team(player, new_team: String) -> void:
	var old_team = player.get_team()
	unregister_player(player)
	if new_team == "human":
		team_humans.append(player)
	else:
		team_infected.append(player)
	player.set_team(new_team)
	team_changed.emit(player, old_team, new_team)

func get_human_count() -> int:
	return team_humans.size()

func get_infected_count() -> int:
	return team_infected.size()

func get_humans() -> Array:
	return team_humans.duplicate()

func get_infected() -> Array:
	return team_infected.duplicate()

func add_score(team: String, points: int) -> void:
	if team in team_scores:
		team_scores[team] += points

func get_score(team: String) -> int:
	return team_scores.get(team, 0)

func reset() -> void:
	team_humans.clear()
	team_infected.clear()
	team_scores = {"humans": 0, "infected": 0}