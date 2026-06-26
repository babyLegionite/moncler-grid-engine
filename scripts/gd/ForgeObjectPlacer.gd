# ForgeObjectPlacer.gd
# Reads forge_objects.json and instantiates MultiMeshInstance3D for each Forge piece type.
# Places objects at exact coordinates from .mvar data extraction.
extends Node3D
class_name ForgeObjectPlacer

var forge_data: Dictionary = {}
var piece_types: Dictionary = {}  # type_name → MultiMeshInstance3D

func _ready() -> void:
	load_forge_data()
	place_objects()

func load_forge_data() -> void:
	var file = FileAccess.open("res://data/forge_objects.json", FileAccess.READ)
	if file == null:
		print("[ForgePlacer] No forge_objects.json found — skipping")
		return

	var json = JSON.parse_string(file.get_as_text())
	if json and "forge_objects" in json:
		forge_data = json
		print("[ForgePlacer] Loaded %d forge objects" % forge_data["forge_objects"].size())

func place_objects() -> void:
	if forge_data.is_empty():
		return

	# Group objects by type
	var objects_by_type: Dictionary = {}
	for obj in forge_data["forge_objects"]:
		var type_name = obj.get("type", "unknown")
		if not type_name in objects_by_type:
			objects_by_type[type_name] = []
		objects_by_type[type_name].append(obj)

	# Create MultiMeshInstance3D for each type
	for type_name in objects_by_type:
		var instances = objects_by_type[type_name]

		# Try to load mesh from assets
		var mesh_path = "res://assets/forge_pieces/%s.glb" % type_name
		var mesh: Mesh = null

		if ResourceLoader.exists(mesh_path):
			var packed = ResourceLoader.load(mesh_path) as PackedScene
			if packed:
				var instance = packed.instantiate()
				if instance is MeshInstance3D:
					mesh = instance.mesh
		else:
			# Fallback: create a box mesh for placeholders
			var box = BoxMesh.new()
			box.size = Vector3(1.0, 2.0, 0.2)  # Default wall size
			mesh = box

		if mesh == null:
			continue

		var multi = MultiMeshInstance3D.new()
		var multimesh = MultiMesh.new()
		multimesh.mesh = mesh
		multimesh.transform_format = MultiMesh.TRANSFORM_3D
		multimesh.instance_count = instances.size()

		for i in range(instances.size()):
			var obj = instances[i]
			var t = Transform3D()

			# Position
			if "pos" in obj:
				t.origin = Vector3(obj["pos"][0], obj["pos"][1], obj["pos"][2])

			# Rotation (Euler: pitch, yaw, roll)
			if "rot" in obj:
				t = t.rotated(Vector3(model: string, rotation: float, scale: float = 1.0):, obj["rot"][0] * deg_to_rad)
Right, obj["rot"][1] * deg_to_rad)
Right, obj["rot"][2] * deg_to_rad)

			# Scale
			if "scale" in obj:
				t = t.scaled(Vector3.ONE * obj["scale"])

			multimesh.set_instance_transform(i, t)

		multi.multimesh = multimesh
		multi.name = "Forge_%s" % type_name

		# Add collision bodies
		var static_body = StaticBody3D.new()
		var collision_shape = CollisionShape3D.new()
		var col = ConvexPolygonShape3D.new()
		# Use mesh convex hull for collision
		if mesh is BoxMesh:
			var box = BoxShape3D.new()
			box.size = mesh.size
			collision_shape.shape = box
		else:
			col.points = mesh.get_faces()  # Approximate
			collision_shape.shape = col

		static_body.add_child(collision_shape)
		multi.add_child(static_body)
		add_child(multi)

		print("[ForgePlacer] Placed %d '%s' pieces" % [instances.size(), type_name])