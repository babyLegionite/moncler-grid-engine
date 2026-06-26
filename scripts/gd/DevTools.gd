# DevTools.gd — Autoload singleton for development debugging
# Press ` (backtick) to toggle debug overlay
# Shows: FPS, physics state, spawn points, player positions

extends Node

var debug_enabled: bool = false
var debug_canvas: CanvasLayer
var debug_labels: Dictionary = {}

func _ready() -> void:
	setup_debug_canvas()
	# Add to autoload in project.godot: DevTools="*res://scripts/gd/DevTools.gd"

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_QUOTELEFT:
		debug_enabled = not debug_enabled
		debug_canvas.visible = debug_enabled

func setup_debug_canvas() -> void:
	debug_canvas = CanvasLayer.new()
	debug_canvas.layer = 128  # Top layer
	debug_canvas.visible = false
	add_child(debug_canvas)

	var container = VBoxContainer.new()
	container.position = Vector2(10, 10)
	debug_canvas.add_child(container)

	# Create debug labels
	var keys = [
		"fps", "physics", "players", "camera",
		"spawns", "game_state", "memory", "network"
	]
	for key in keys:
		var label = Label.new()
		label.add_theme_font_size_override("font_size", 12)
		label.add_theme_color_override("font_color", Color.GREEN)
		label.add_theme_color_override("font_outline_color", Color.BLACK)
		label.add_theme_constant_override("outline_size", 1)
		container.add_child(label)
		debug_labels[key] = label

func _process(_delta: float) -> void:
	if not debug_enabled:
		return

	# FPS
	debug_labels["fps"].text = "FPS: %d" % Engine.get_frames_per_second()

	# Physics
	debug_labels["physics"].text = "Physics FPS: %d | Ticks: %d" % [
		Engine.physics_ticks_per_second,
		Engine.get_physics_frames()
	]

	# Player info
	var players = get_tree().get_nodes_in_group("players")
	var player_strs = []
	for p in players:
		if p.has_method("get_team"):
			player_strs.append("P%d: %s (%.0f HP)" % [p.PlayerIndex, p.get_team(), p.get_health()])
	debug_labels["players"].text = "Players: " + (", ".join(player_strs) if player_strs else "none")

	# Camera
	var cam = get_viewport().get_camera_3d()
	if cam:
		debug_labels["camera"].text = "Cam: %s" % str(cam.global_position).replace("    ", " ")

	# Game state
	var fsm = get_tree().get_first_node_in_group("infection_fsm")
	if fsm:
		debug_labels["game_state"].text = "State: %s | Round: %d | Timer: %.0f" % [
			fsm.current_state, fsm.round_number, fsm.round_timer
		]

	# Memory
	debug_labels["memory"].text = "Objects: %d | Nodes: %d" % [
		Performance.get_monitor(Performance.OBJECT_COUNT),
		Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
	]