using Godot;

/// <summary>
/// Camera follow script — attaches to a Camera3D, follows a target node.
/// Handles first-person and third-person views with smooth damping.
/// </summary>
public partial class CameraFollow : Node
{
    [Export] public Node3D Target { get; set; }
    [Export] public Vector3 Offset { get; set; } = new Vector3(0, 0.7f, 0); // Eye height offset
    [Export] public float SmoothSpeed { get; set; } = 20f;
    [Export] public bool FirstPerson { get; set; } = true;

    private Camera3D _camera;

    public override void _Ready()
    {
        _camera = GetParent<Camera3D>();
    }

    public override void _Process(double delta)
    {
        if (Target == null || _camera == null) return;

        if (FirstPerson)
        {
            // Camera inherits Target's rotation (set by PlayerController)
            _camera.GlobalPosition = Target.GlobalPosition + Offset;
            // Rotation handled by PlayerController directly on the camera
        }
        else
        {
            // Third person: camera follows behind
            var targetPos = Target.GlobalPosition + Offset + Target.Transform.Basis.Z * 3f;
            _camera.GlobalPosition = _camera.GlobalPosition.Lerp(targetPos, SmoothSpeed * (float)delta);
            _camera.LookAt(Target.GlobalPosition + Offset);
        }
    }
}