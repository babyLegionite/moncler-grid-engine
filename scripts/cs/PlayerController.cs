using Godot;
using System;
using System.Collections.Generic;

/// <summary>
/// Halo Reach biped player controller with exact physics replication.
/// Loads physics constants from reach_physics.json at runtime.
/// Designed for split-screen: receives device-specific input via DeviceId.
/// </summary>
public partial class PlayerController : CharacterBody3D
{
    [Export] public int PlayerIndex { get; set; } = 0;
    [Export] public int DeviceId { get; set; } = 0;
    [Export] public string Team { get; set; } = "human";

    // Physics constants loaded from JSON
    private float _gravity;
    private float _walkSpeed, _runSpeed, _crouchSpeed, _sprintSpeed;
    private float _jumpVelocity;
    private float _groundAccel, _groundDecel;
    private float _airAccel, _airDecel, _maxAirControl;
    private float _terminalVelocity, _stepHeight, _slopeLimit;
    private float _lookSensH, _lookSensV, _lookAccel, _lookPeg;
    private float _crouchTransitionSpeed, _standTransitionSpeed;
    private float _playerHeightStanding, _playerHeightCrouching;
    private float _meleeDamage, _meleeRange;
    private float _grenadeVelocity;

    // Runtime state
    private Vector3 _velocity = Vector3.Zero;
    private float _lookYaw = 0f;
    private float _lookPitch = 0f;
    private bool _isGrounded = false;
    private bool _isCrouching = false;
    private bool _isSprinting = false;
    private bool _jumpQueued = false;
    private float _targetHeight;
    private float _health = 100f;
    private float _shield = 100f;
    private bool _isDead = false;

    // Input accumulator (populated by _UnhandledInput)
    private float _leftStickX, _leftStickY, _rightStickX, _rightStickY;
    private float _leftTrigger, _rightTrigger;
    private bool _jumpPressed, _crouchPressed, _sprintPressed;
    private bool _firePressed, _adsPressed, _reloadPressed, _grenadePressed;
    private bool _meleePressed, _switchWeaponPressed;

    // References
    private Camera3D _camera;
    private CollisionShape3D _collisionShape;
    private CapsuleShape3D _capsuleShape;

    // Signals
    [Signal] public delegate void DiedEventHandler(int victimPlayerIndex, int killerPlayerIndex);
    [Signal] public delegate void DamageTakenEventHandler(int playerIndex, float damage, float newHealth);

    public override void _Ready()
    {
        _camera = GetNode<Camera3D>("Camera3D");
        _collisionShape = GetNode<CollisionShape3D>("CollisionShape3D");
        _capsuleShape = _collisionShape.Shape as CapsuleShape3D;

        LoadPhysicsConstants();

        _capsuleShape.Height = _playerHeightStanding;
        _targetHeight = _playerHeightStanding;

        // Let InputManager assign device
        AddToGroup("players");
        AddToGroup(Team);

        // Default camera FOV
        _camera.Fov = 78.0f;
    }

    private void LoadPhysicsConstants()
    {
        try
        {
            using var file = FileAccess.Open("res://data/reach_physics.json", FileAccess.ModeFlags.Read);
            var json = Json.ParseString(file.GetAsText()).AsGodotDictionary();

            _gravity = (float)(double)json["gravity"];
            _walkSpeed = (float)(double)json["player_walk_speed"];
            _runSpeed = (float)(double)json["player_run_speed"];
            _crouchSpeed = (float)(double)json["player_crouch_speed"];
            _sprintSpeed = (float)(double)json["player_sprint_speed"];
            _jumpVelocity = (float)(double)json["jump_initial_velocity"];
            _groundAccel = (float)(double)json["ground_acceleration"];
            _groundDecel = (float)(double)json["ground_deceleration"];
            _airAccel = (float)(double)json["air_acceleration"];
            _airDecel = (float)(double)json["air_deceleration"];
            _maxAirControl = (float)(double)json["max_air_control"];
            _terminalVelocity = (float)(double)json["terminal_velocity"];
            _stepHeight = (float)(double)json["step_height"];
            _slopeLimit = (float)(double)json["slope_angle_limit"];
            _lookSensH = (float)(double)json["look_sensitivity_horizontal"];
            _lookSensV = (float)(double)json["look_sensitivity_vertical"];
            _lookAccel = (float)(double)json["look_acceleration_time"];
            _lookPeg = (float)(double)json["look_pegged_speed"];
            _crouchTransitionSpeed = (float)(double)json["crouch_transition_speed"];
            _standTransitionSpeed = (float)(double)json["stand_transition_speed"];
            _playerHeightStanding = (float)(double)json["player_height_standing"];
            _playerHeightCrouching = (float)(double)json["player_height_crouching"];
            _meleeDamage = (float)(double)json["melee_damage"];
            _meleeRange = (float)(double)json["melee_lunge_range"];
            _grenadeVelocity = (float)(double)json["grenade_throw_velocity"];
        }
        catch (Exception e)
        {
            GD.PrintErr($"Failed to load reach_physics.json: {e.Message}");
            SetDefaults();
        }
    }

    private void SetDefaults()
    {
        _gravity = -4.0f;
        _walkSpeed = 1.5f;
        _runSpeed = 2.7f;
        _crouchSpeed = 0.8f;
        _sprintSpeed = 3.0f;
        _jumpVelocity = 3.5f;
        _groundAccel = 10f;
        _groundDecel = 12f;
        _airAccel = 2f;
        _airDecel = 1f;
        _maxAirControl = 0.25f;
        _terminalVelocity = -15f;
        _stepHeight = 0.25f;
        _slopeLimit = 60f;
        _lookSensH = 2f;
        _lookSensV = 1.5f;
        _lookAccel = 0.08f;
        _lookPeg = 6f;
        _crouchTransitionSpeed = 5f;
        _standTransitionSpeed = 3f;
        _playerHeightStanding = 1.2f;
        _playerHeightCrouching = 0.7f;
        _meleeDamage = 20f;
        _meleeRange = 1f;
        _grenadeVelocity = 12f;
    }

    public override void _PhysicsProcess(double delta)
    {
        if (_isDead) return;

        var dt = (float)delta;

        // Update crouch height smoothly
        UpdateCrouch(dt);

        // Read cooked input
        var inputDir = GetInputDirection();
        bool wantCrouch = _crouchPressed;
        bool wantSprint = _sprintPressed && !wantCrouch && _isGrounded;

        _isCrouching = wantCrouch;
        _isSprinting = wantSprint;

        // Apply gravity
        if (!_isGrounded)
        {
            _velocity.Y += _gravity * dt;
            _velocity.Y = Mathf.Max(_velocity.Y, _terminalVelocity);
        }

        // Select speed
        float currentSpeed = _walkSpeed;
        if (_isCrouching) currentSpeed = _crouchSpeed;
        else if (_isSprinting) currentSpeed = _sprintSpeed;
        else if (_firePressed) currentSpeed = _runSpeed; // auto-run when firing

        // Target horizontal velocity
        Vector3 targetVel = inputDir * currentSpeed;
        targetVel.Y = _velocity.Y;

        // Acceleration: ground vs air
        if (_isGrounded)
        {
            _velocity.X = MoveToward(_velocity.X, targetVel.X, _groundAccel * dt);
            _velocity.Z = MoveToward(_velocity.Z, targetVel.Z, _groundAccel * dt);
            // Snappy deceleration: accelerate decel when input is neutral
            if (inputDir.Length() < 0.1f)
            {
                _velocity.X = MoveToward(_velocity.X, 0f, _groundDecel * dt);
                _velocity.Z = MoveToward(_velocity.Z, 0f, _groundDecel * dt);
            }
        }
        else
        {
            // Limited air control
            _velocity.X = MoveToward(_velocity.X, targetVel.X * _maxAirControl, _airAccel * dt);
            _velocity.Z = MoveToward(_velocity.Z, targetVel.Z * _maxAirControl, _airAccel * dt);
        }

        // Jump (Blam engine: queued jump on next grounded frame)
        if (_jumpPressed && _isGrounded)
        {
            _velocity.Y = _jumpVelocity;
            _isGrounded = false;
            _jumpPressed = false;
            _jumpQueued = false;
        }
        else if (_jumpPressed && !_isGrounded && !_jumpQueued)
        {
            _jumpQueued = true;
        }
        if (_jumpQueued && _isGrounded)
        {
            _velocity.Y = _jumpVelocity;
            _isGrounded = false;
            _jumpQueued = false;
        }

        // Apply velocity
        Velocity = _velocity;
        MoveAndSlide();
        _isGrounded = IsOnFloor();
    }

    public override void _Process(double delta)
    {
        if (_isDead) return;

        var dt = (float)delta;

        // Look (right stick) — processed in _Process for smoothness
        float lookH = _rightStickX * _lookSensH;
        float lookV = _rightStickY * _lookSensV;

        // Apply look acceleration (Reach style)
        _lookYaw -= lookH * _lookAccel;
        _lookPitch -= lookV * _lookAccel;
        _lookPitch = Mathf.Clamp(_lookPitch, -1.5f, 1.5f);

        Rotation = new Vector3(0, _lookYaw, 0);
        _camera.Rotation = new Vector3(_lookPitch, 0, 0);

        // Weapon actions (hand off to WeaponController)
        ProcessWeaponActions();
    }

    private void ProcessWeaponActions()
    {
        if (_firePressed)
        {
            // WeaponController handles this via signal or direct call
            GD.Print($"Player {PlayerIndex}: Fire");
        }
        if (_reloadPressed)
        {
            GD.Print($"Player {PlayerIndex}: Reload");
        }
        if (_meleePressed)
        {
            PerformMelee();
            _meleePressed = false;
        }
        if (_grenadePressed)
        {
            ThrowGrenade();
            _grenadePressed = false;
        }
    }

    private void PerformMelee()
    {
        // Check for nearby enemies
        var spaceState = GetWorld3D().DirectSpaceState;
        var query = new PhysicsShapeQueryParameters3D();
        var sphere = new SphereShape3D();
        sphere.Radius = _meleeRange;
        query.Shape = sphere;
        query.Transform = GlobalTransform;
        query.CollisionMask = 2; // Player layer

        var results = spaceState.IntersectShape(query);
        foreach (var result in results)
        {
            var collider = (Node3D)result["collider"];
            if (collider is PlayerController other && other != this && other.Team != Team)
            {
                other.TakeDamage(_meleeDamage, PlayerIndex);
            }
        }
    }

    private void ThrowGrenade()
    {
        // Placeholder — spawn grenade projectile
        GD.Print($"Player {PlayerIndex}: Grenade thrown");
    }

    private Vector3 GetInputDirection()
    {
        var input = new Vector2(_leftStickX, _leftStickY);
        if (input.Length() > 1f) input = input.Normalized();

        var dir = (Transform.Basis * new Vector3(input.X, 0, -input.Y)).Normalized();
        return dir;
    }

    private float MoveToward(float current, float target, float maxDelta)
    {
        if (Mathf.Abs(current - target) <= Mathf.Abs(maxDelta))
            return target;
        return current + Mathf.Sign(target - current) * Mathf.Abs(maxDelta);
    }

    private void UpdateCrouch(float dt)
    {
        _targetHeight = _isCrouching ? _playerHeightCrouching : _playerHeightStanding;
        float speed = _isCrouching ? _crouchTransitionSpeed : _standTransitionSpeed;
        _capsuleShape.Height = Mathf.MoveToward(_capsuleShape.Height, _targetHeight, speed * dt);
    }

    public override void _UnhandledInput(InputEvent @event)
    {
        // Device-specific input filtering for split-screen
        if (@event is InputEventJoypadMotion joyMotion && joyMotion.Device == DeviceId)
        {
            switch (joyMotion.Axis)
            {
                case JoyAxis.LeftX: _leftStickX = joyMotion.AxisValue; break;
                case JoyAxis.LeftY: _leftStickY = joyMotion.AxisValue; break;
                case JoyAxis.RightX: _rightStickX = joyMotion.AxisValue; break;
                case JoyAxis.RightY: _rightStickY = joyMotion.AxisValue; break;
                case JoyAxis.TriggerLeft: _leftTrigger = joyMotion.AxisValue; break;
                case JoyAxis.TriggerRight: _rightTrigger = joyMotion.AxisValue; break;
            }
        }
        else if (@event is InputEventJoypadButton joyButton && joyButton.Device == DeviceId)
        {
            var pressed = joyButton.Pressed;
            switch (joyButton.ButtonIndex)
            {
                case JoyButton.A: _jumpPressed = pressed || _jumpPressed; break;
                case JoyButton.B: _crouchPressed = pressed; break;
                case JoyButton.X: _sprintPressed = pressed; break;
                case JoyButton.Y: _switchWeaponPressed = pressed; break;
                case JoyButton.LeftShoulder: _grenadePressed = pressed || _grenadePressed; break;
                case JoyButton.RightShoulder: _meleePressed = pressed || _meleePressed; break;
                case JoyButton.Back: _reloadPressed = pressed || _reloadPressed; break; // Select on PS4
            }
            // Triggers as buttons
            if (joyButton.ButtonIndex == JoyButton.TriggerLeft)
                _adsPressed = pressed;
            if (joyButton.ButtonIndex == JoyButton.TriggerRight)
                _firePressed = pressed;
        }
    }

    public void TakeDamage(float damage, int attackerIndex)
    {
        if (_isDead) return;

        // Shield absorbs first
        if (_shield > 0)
        {
            float oldShield = _shield;
            _shield -= damage;
            if (_shield < 0) _shield = 0;
            float overflow = damage - oldShield;
            if (overflow > 0)
                _health -= overflow;
        }
        else
        {
            _health -= damage;
        }

        EmitSignal(SignalName.DamageTaken, PlayerIndex, damage, _health);

        if (_health <= 0)
        {
            _health = 0;
            _isDead = true;
            EmitSignal(SignalName.Died, PlayerIndex, attackerIndex);
        }
    }

    public void Respawn(Vector3 position, string newTeam)
    {
        _health = 100f;
        _shield = 100f;
        _isDead = false;
        _velocity = Vector3.Zero;
        Team = newTeam;
        Position = position;

        RemoveFromGroup("human");
        RemoveFromGroup("infected");
        AddToGroup(Team);
    }

    public void SetTeam(string newTeam)
    {
        RemoveFromGroup("human");
        RemoveFromGroup("infected");
        Team = newTeam;
        AddToGroup(Team);
    }

    public void ApplyBonus(string bonusType, float multiplier)
    {
        switch (bonusType)
        {
            case "speed":
                _walkSpeed *= multiplier;
                _runSpeed *= multiplier;
                _sprintSpeed *= multiplier;
                break;
            case "damage":
                _meleeDamage *= multiplier;
                break;
            case "shield":
                _shield *= multiplier;
                break;
        }
    }

    public void Reset()
    {
        _health = 100f;
        _shield = 100f;
        _isDead = false;
        _velocity = Vector3.Zero;
        Team = "human";
    }

    public bool IsDead() => _isDead;
    public float GetHealth() => _health;
    public float GetShield() => _shield;
    public string GetTeam() => Team;
}