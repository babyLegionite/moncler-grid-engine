# InputManager.gd
# Autoload singleton — DualShock 4 controller detection and routing for 4 players
extends Node

var controller_map: Dictionary = {}  # device_id → player_index
var available_ids: Array = []  # List of connected device IDs

signal controller_connected(player_index: int, device_id: int, name: String)
signal controller_disconnected(player_index: int, device_id: int)

func _ready() -> void:
	Input.joy_connection_changed.connect(_on_joy_connection)
	detect_controllers()

func detect_controllers() -> void:
	available_ids = Input.get_connected_joypads()
	for i in range(available_ids.size()):
		var device_id = available_ids[i]
		var name = Input.get_joy_name(device_id)
		if is_playstation_controller(name):
			controller_map[device_id] = i  # Player 0-3
			controller_connected.emit(i, device_id, name)
			print("[InputManager] Player %d: %s (device %d)" % [i, name, device_id])

func _on_joy_connection(device_id: int, connected: bool) -> void:
	if connected:
		var name = Input.get_joy_name(device_id)
		if is_playstation_controller(name):
			# Assign lowest available player index
			var assigned = -1
			for i in range(4):
				if not controller_map.values().has(i):
					assigned = i
					break
			if assigned >= 0:
				controller_map[device_id] = assigned
				available_ids.append(device_id)
				controller_connected.emit(assigned, device_id, name)
				print("[InputManager] Player %d connected: %s (device %d)" % [assigned, name, device_id])
	else:
		if device_id in controller_map:
			var player_idx = controller_map[device_id]
			controller_map.erase(device_id)
			available_ids.erase(device_id)
			controller_disconnected.emit(player_idx, device_id)
			print("[InputManager] Player %d disconnected (device %d)" % [player_idx, device_id])

func is_playstation_controller(name: String) -> bool:
	var n = name.to_lower()
	return "dualshock" in n or "ps4" in n or "ps5" in n or "sony" in n or "playstation" in n or "wireless controller" in n

func get_player_device(player_index: int) -> int:
	for device_id in controller_map:
		if controller_map[device_id] == player_index:
			return device_id
	return -1

func get_player_count() -> int:
	return controller_map.size()

func get_connected_players() -> Array:
	var players = []
	for device_id in controller_map:
		players.append({
			"player_index": controller_map[device_id],
			"device_id": device_id,
			"name": Input.get_joy_name(device_id)
		})
	players.sort_custom(func(a, b): return a["player_index"] < b["player_index"])
	return players