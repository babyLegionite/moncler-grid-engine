# MapPreview.gd — 3D map preview for Godot editor
# Shows terrain, spawn points, forge objects, and player paths
# Usage: Attach to a Node3D in your scene, enable in editor

@tool
extends Node3D
class_name MapPreview

@export var show_spawns: bool = true:
	set(v):
		show_spawns = v
		_refresh()
@export var show_forge: bool = true:
	set(v):
		show_forge = v
		_refresh()
@export var spawn_sphere_radius: float = 0.3
@export var human_spawn_color: Color = Color.GREEN
@export var infected_spawn_color: Color = Color.ORANGE_RED
@export var forge_color: Color = Color(0.5, 0.5, 0.5, 0.5)

var _spawn_markers: Array[MeshInstance3D] = []
var _forge_markers: Array[MeshInstance3D] = []

func _ready() -> void:
	if Engine.is_editor_hint():
		_refresh()

func _refresh() -> void:
	_clear_markers()

	if show_spawns:
		_draw_spawns()
	if show_forge:
		_draw_forge()

func _clear_markers() -> void:
	for m in _spawn_markers:
		m.queue_free()
	_spawn_markers.clear()
	for m in _forge_markers:
		m.queue_free()
	_forge_markers.clear()

func _draw_spawns() -> void:
	var file = FileAccess.open("res://data/spawn_coordinates.json", FileAccess.READ)
	if file == null:
		return

	var json = JSON.parse_string(file.get_as_text())
	if json == null:
		return

	var sphere_mesh = SphereMesh.new()
	sphere_mesh.radius = spawn_sphere_radius
	sphere_mesh.height = spawn_sphere_radius * 2

	for s in json.get("spawns", []):
		var marker = MeshInstance3D.new()
		marker.mesh = sphere_mesh

		var mat = StandardMaterial3D.new()
		mat.albedo_color = human_spawn_color if s.get("team") == "human" else infected_spawn_color
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		marker.material_override = mat

		marker.position = Vector3(s["pos"][0], s["pos"][1], s["pos"][2])
		marker.name = "Spawn_%s_%d" % [s.get("team", "?"), s.get("id", 0)]

		add_child(marker)
		_spawn_markers.append(marker)

func _draw_forge() -> void:
	var file = FileAccess.open("res://data/forge_objects.json", FileAccess.READ)
	if file == null:
		return

	var json = JSON.parse_string(file.get_as_text())
	if json == null:
		return

	var box_mesh = BoxMesh.new()
	box_mesh.size = Vector3(0.5, 1.0, 0.1)

	for obj in json.get("forge_objects", []):
		var marker = MeshInstance3D.new()
		marker.mesh = box_mesh

		var mat = StandardMaterial3D.new()
		mat.albedo_color = forge_color
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		marker.material_override = mat

		marker.position = Vector3(obj["pos"][0], obj["pos"][1], obj["pos"][2])
		if "rot" in obj:
			marker.rotation_degrees = Vector3(obj["rot"][0], obj["rot"][1], obj["rot"][2])
		marker.name = "Forge_%s_%d" % [obj.get("type", "?"), obj.get("id", 0)]

		add_child(marker)
		_forge_markers.append(marker)