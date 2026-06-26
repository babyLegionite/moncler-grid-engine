# SplitScreenManager.gd
# 4-player split-screen via SubViewport
# Layout: 2x2 grid for 4 players, 1-2 players get dynamic layout
extends Control
class_name SplitScreenManager

@export var max_players: int = 4

var viewports: Array[SubViewport] = []
var containers: Array[SubViewportContainer] = []

func _ready() -> void:
	setup_viewports()

func setup_viewports() -> void:
	# Grid container for 2x2 layout
	var grid = GridContainer.new()
	grid.columns = 2
	grid.set_anchors_preset(Control.PRESET_FULL_RECT)
	grid.add_theme_constant_override("h_separation", 0)
	grid.add_theme_constant_override("v_separation", 0)

	for i in range(max_players):
		# SubViewportContainer handles stretching
		var container = SubViewportContainer.new()
		container.stretch = true
		container.stretch_shrink = 1  # Scale factor for performance

		var vp = SubViewport.new()
		vp.size = Vector2i(960, 540)  # Quarter 1080p (Xbox 360 4-player)
		vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
		vp.transparent_bg = false

		# World 3D
		var world_3d = World3D.new()
		vp.world_3d = world_3d

		# Add camera - will be assigned by game setup
		var cam = Camera3D.new()
		cam.current = true
		cam.fov = 78.0  # Halo FOV
		vp.add_child(cam)

		# Assign player camera later
		vp.set_meta("player_index", i)
		vp.set_meta("camera", cam)

		container.add_child(vp)
		grid.add_child(container)

		viewports.append(vp)
		containers.append(container)

	add_child(grid)

func assign_player_camera(player_index: int, player_node: Node3D) -> void:
	if player_index >= viewports.size():
		return

	var vp = viewports[player_index]
	var cam = vp.get_meta("camera") as Camera3D
	if cam == null:
		return

	# Parent camera to player for first-person view
	var player_cam = player_node.get_node_or_null("Camera3D")
	if player_cam:
		# Use a remote transform instead of reparenting
		var remote = RemoteTransform3D.new()
		remote.remote_path = cam.get_path()
		remote.update_position = true
		remote.update_rotation = true
		remote.update_scale = true
		player_cam.add_child(remote)
	else:
		# Fallback: add follow script
		var follow = CameraFollow.new()
		follow.Target = player_node
		cam.add_child(follow)

	# Set viewport world to match game world
	vp.world_3d = player_node.get_world_3d()

func get_viewport(player_index: int) -> SubViewport:
	if player_index < viewports.size():
		return viewports[player_index]
	return null

func update_layout(active_players: int) -> void:
	var grid = get_child(0) as GridContainer
	if grid == null:
		return

	match active_players:
		1:
			grid.columns = 1
			for i in range(containers.size()):
				containers[i].visible = (i == 0)
			viewports[0].size = Vector2i(1920, 1080)  # Full 1080p for 1 player
		2:
			grid.columns = 1  # Top/bottom split
			for i in range(containers.size()):
				containers[i].visible = (i < 2)
			for i in range(2):
				viewports[i].size = Vector2i(1920, 540)
		3:
			# One large top, two small bottom
			grid.columns = 2
			for i in range(containers.size()):
				containers[i].visible = (i < 3)
			viewports[0].size = Vector2i(1920, 720)
			viewports[1].size = Vector2i(960, 360)
			viewports[2].size = Vector2i(960, 360)
		4:
			grid.columns = 2
			for i in range(containers.size()):
				containers[i].visible = (i < 4)
			for i in range(4):
				viewports[i].size = Vector2i(960, 540)