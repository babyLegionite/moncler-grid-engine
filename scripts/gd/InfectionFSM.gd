# InfectionFSM.gd
# Halo Reach Infection game mode — full state machine
# Pre-round → Active → Last Man Standing → Round End → Match End
extends Node
class_name InfectionFSM

enum State { PRE_ROUND, ACTIVE, LAST_MAN_STANDING, ROUND_END, MATCH_END }

var current_state: State = State.PRE_ROUND
var players: Array = []
var humans: Array = []
var infected: Array = []
var alpha_zombie = null
var last_man = null

var round_number: int = 0
var max_rounds: int = 3
var round_timer: float = 180.0  # 3 minutes default
var state_timer: float = 0.0
var intermission_time: float = 5.0

var human_wins: int = 0
var infected_wins: int = 0

signal round_started(round_number: int)
signal player_infected(player)
signal last_man_standing(player)
signal round_end(winner: String, round_number: int)
signal match_end(winner: String)
signal timer_tick(minutes: int, seconds: int)

func _ready() -> void:
	connect_players()

func _process(delta: float) -> void:
	match current_state:
		State.PRE_ROUND:
			process_pre_round(delta)
		State.ACTIVE:
			process_active(delta)
		State.LAST_MAN_STANDING:
			process_last_man(delta)
		State.ROUND_END:
			process_round_end(delta)
		State.MATCH_END:
			pass  # Wait for restart or scene change

func start_match() -> void:
	human_wins = 0
	infected_wins = 0
	round_number = 0
	current_state = State.PRE_ROUND

func start_round() -> void:
	round_number += 1
	humans.clear()
	infected.clear()

	# Select alpha zombie (lowest score, or random first round)
	alpha_zombie = select_alpha_zombie()

	# Assign teams
	for p in players:
		if p == alpha_zombie:
			p.set_team("infected")
			infected.append(p)
		else:
			p.set_team("human")
			humans.append(p)

	# Spawn players
	var human_spawns = get_spawn_points("human")
	var infected_spawns = get_spawn_points("infected")

	alpha_zombie.respawn(get_random_spawn(infected_spawns), "infected")
	for h in humans:
		h.respawn(get_random_spawn(human_spawns), "human")

	round_timer = 180.0
	current_state = State.ACTIVE
	round_started.emit(round_number)

func process_pre_round(delta: float) -> void:
	state_timer += delta
	if state_timer >= intermission_time:
		state_timer = 0.0
		start_round()

func process_active(delta: float) -> void:
	round_timer -= delta

	# Emit timer for HUD
	var mins = int(round_timer) / 60
	var secs = int(round_timer) % 60
	timer_tick.emit(mins, secs)

	# Check conversion (handled by signals on player death — see _on_player_died)

	# Win conditions
	if humans.size() == 1 and current_state != State.LAST_MAN_STANDING:
		last_man = humans[0]
		current_state = State.LAST_MAN_STANDING
		last_man.apply_bonus("speed", 1.5)
		last_man.apply_bonus("damage", 2.0)
		last_man.apply_bonus("shield", 2.0)
		last_man_standing.emit(last_man)
		print("[Infection] Last Man Standing: Player %d" % last_man.PlayerIndex)

	if humans.size() == 0:
		end_round("infected")

	if round_timer <= 0:
		end_round("humans")

func process_last_man(delta: float) -> void:
	round_timer -= delta
	var mins = int(round_timer) / 60
	var secs = int(round_timer) % 60
	timer_tick.emit(mins, secs)

	if last_man == null or last_man.is_dead():
		end_round("infected")

	if round_timer <= 0:
		end_round("humans")

func end_round(winner: String) -> void:
	if winner == "infected":
		infected_wins += 1
	else:
		human_wins += 1

	round_end.emit(winner, round_number)
	current_state = State.ROUND_END
	state_timer = 0.0
	print("[Infection] Round %d ends — Winner: %s" % [round_number, winner])

func process_round_end(delta: float) -> void:
	state_timer += delta
	if state_timer >= intermission_time:
		state_timer = 0.0
		if round_number >= max_rounds:
			current_state = State.MATCH_END
			var winner = "humans" if human_wins > infected_wins else "infected"
			if human_wins == infected_wins:
				winner = "draw"
			match_end.emit(winner)
			print("[Infection] Match over — Winner: %s (%d-%d)" % [winner, human_wins, infected_wins])
		else:
			current_state = State.PRE_ROUND
			# Reset all players
			for p in players:
				p.reset()

func _on_player_died(player, killer_idx: int) -> void:
	if current_state not in [State.ACTIVE, State.LAST_MAN_STANDING]:
		return

	# If a human was killed by an infected
	if player.get_team() == "human":
		# Find killer
		var killer = get_player_by_index(killer_idx)
		if killer and killer.get_team() == "infected":
			convert_to_infected(player)

func convert_to_infected(player) -> void:
	if player in humans:
		humans.erase(player)
	infected.append(player)
	player.set_team("infected")
	var spawns = get_spawn_points("infected")
	player.respawn(get_random_spawn(spawns), "infected")
	player_infected.emit(player)
	print("[Infection] Player %d converted to Infected" % player.PlayerIndex)

func select_alpha_zombie():
	# First round: random. Subsequent rounds: lowest-scoring player
	if round_number <= 1:
		return players[randi() % players.size()]
	else:
		var lowest = players[0]
		for p in players:
			if p.score < lowest.score:
				lowest = p
		return lowest

func connect_players() -> void:
	players = get_tree().get_nodes_in_group("players")
	for p in players:
		p.died.connect(_on_player_died)

func get_spawn_points(team: String) -> Array:
	var spawns = []
	var file = FileAccess.open("res://data/spawn_coordinates.json", FileAccess.READ)
	if file:
		var json = JSON.parse_string(file.get_as_text())
		if json and "spawns" in json:
			for s in json["spawns"]:
				if s["team"] == team:
					spawns.append(Vector3(s["pos"][0], s["pos"][1], s["pos"][2]))
	return spawns

func get_random_spawn(spawns: Array) -> Vector3:
	if spawns.is_empty():
		return Vector3.ZERO
	return spawns[randi() % spawns.size()]

func get_player_by_index(idx: int):
	for p in players:
		if p.PlayerIndex == idx:
			return p
	return null