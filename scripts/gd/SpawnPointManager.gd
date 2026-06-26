# SpawnPointManager.gd
# Reads spawn_coordinates.json and places Marker3D nodes at spawn positions.
# Separates spawns by team (human/infected).
extends Node3D
class_name SpawnPointManager

var human_spawns: Array[Marker3D] = []
var infected_spawns: Array[Marker3D] = []
var item_spawns: Array[Marker3D] = []

func _ready() -> void:
	load_spawn_points()

func load_spawn_points() -> void:
	var file = FileAccess.open("res://data/spawn_coordinates.json", FileAccess.READ)
	if file == null:
		print("[SpawnManager] No spawn_coordinates.json — using defaults")
		create_default_spawns()
		return

	var json = JSON.parse_string(file.get_as_text())
	if json == null:
		create_default_spawns()
		return

	# Player spawns
	if "spawns" in json:
		for s in json["spawns"]:
			var marker = Marker3D.new()
			marker.position = Vector3(s["pos"][0], s["pos"][1], s["pos"][2])
			marker.set_meta("team", s.get("team", "human"))
			marker.set_meta("spawn_id", s.get("id", 0))

			if s.get("team") == "infected":
				infected_spawns.append(marker)
			else:
				human_spawns.append(marker)

			add_child(marker)

	# Item spawns (weapons, equipment)
	if "item_spawns" in json:
		for s in json["item_spawns"]:
			var marker = Marker3D.new()
			marker.position = Vector3(s["pos"][0], s["pos"][1], s["pos"][2])
			marker.set_meta("type", s.get("type", ""))
			marker.set_meta("respawn_time", s.get("respawn_time", 30.0))
			item_spawns.append(marker)
			add_child(marker)

	print("[SpawnManager] Loaded %d human, %d infected, %d item spawns" % [human_spawns.size(), infected_spawns.size(), item_spawns.size()])

func create_default_spawns() -> void:
	# Placeholder spawns for testing before extraction
	for i in range(4):
		var m = Marker3D.new()
		m.position = Vector3(i * 3 - 4.5, 1, 0)
		m.set_meta("team", "human")
		human_spawns.append(m)
		add_child(m)

	for i in range(2):
		var m = Marker3D.new()
		m.position = Vector3(i * 10 - 5, 1, 10)
		m.set_meta("team", "infected")
		infected_spawns.append(m)
		add_child(m)

func get_random_spawn(team: String) -> Vector3:
	var spawns = human_spawns if team == "human" else infected_spawns
	if spawns.is_empty():
		return Vector3.ZERO
	return spawns[randi() % spawns.size()].global_position

func get_human_spawns() -> Array[Marker3D]:
	return human_spawns

func get_infected_spawns() -> Array[Marker3D]:
	return infected_spawns