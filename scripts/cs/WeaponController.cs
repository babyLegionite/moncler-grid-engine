using Godot;
using System;
using System.Collections.Generic;

/// <summary>
/// Weapon controller — handles weapon state, firing, reloading, and swapping.
/// Attached to each player. Reads weapon data from weapon_data.json.
/// </summary>
public partial class WeaponController : Node
{
    [Export] public int PlayerIndex { get; set; } = 0;

    private Dictionary<string, WeaponData> _weapons = new();
    private WeaponData _currentWeapon;
    private string _currentWeaponId = "assault_rifle";
    private float _fireTimer = 0f;
    private float _reloadTimer = 0f;
    private bool _isReloading = false;
    private int _currentAmmo;
    private int _reserveAmmo;
    private bool _triggerHeld = false;

    // Weapon data class
    public class WeaponData
    {
        public string Id, DisplayName, Type;
        public float Damage, RoundsPerSecond, ReloadTime, ReloadEmpty, Range, Spread;
        public int MagazineSize, MaxAmmo, ZoomLevels;
        public bool CanHeadshot;
        public float HeadshotMultiplier, ReloadPerShell;
        public float LungeRange, LungeSpeed, SwingSpeed;
    }

    // Signals
    [Signal] public delegate void WeaponFiredEventHandler(int playerIndex, string weaponId);
    [Signal] public delegate void WeaponReloadedEventHandler(int playerIndex, string weaponId);
    [Signal] public delegate void WeaponSwappedEventHandler(int playerIndex, string oldWeapon, string newWeapon);
    [Signal] public delegate void AmmoChangedEventHandler(int playerIndex, int current, int reserve);

    public override void _Ready()
    {
        LoadWeaponData();
        EquipWeapon(_currentWeaponId);
    }

    private void LoadWeaponData()
    {
        try
        {
            using var file = FileAccess.Open("res://data/weapon_data.json", FileAccess.ModeFlags.Read);
            var json = Json.ParseString(file.GetAsText()).AsGodotDictionary();
            var weapons = json["weapons"].AsGodotDictionary();

            foreach (var kvp in weapons)
            {
                var data = kvp.Value.AsGodotDictionary();
                var w = new WeaponData
                {
                    Id = kvp.Key.ToString(),
                    DisplayName = data["display_name"].ToString(),
                    Type = data["type"].ToString(),
                    Damage = (float)(double)data["damage_per_shot"],
                    RoundsPerSecond = (float)(double)data["rounds_per_second"],
                    MagazineSize = (int)(double)data["magazine_size"],
                    MaxAmmo = (int)(double)data["max_ammo"],
                    ReloadTime = (float)(double)data["reload_time"],
                    ReloadEmpty = data.ContainsKey("reload_time_empty") ? (float)(double)data["reload_time_empty"] : 0f,
                    Range = (float)(double)data["range"],
                    Spread = (float)(double)data["spread"],
                    ZoomLevels = (int)(double)data["zoom_levels"],
                    CanHeadshot = (bool)data["can_headshot"],
                    HeadshotMultiplier = data.ContainsKey("headshot_multiplier") ? (float)(double)data["headshot_multiplier"] : 1f,
                    SwingSpeed = data.ContainsKey("swings_per_second") ? 1f / (float)(double)data["swings_per_second"] : 0.5f
                };
                _weapons[w.Id] = w;
            }
        }
        catch (Exception e)
        {
            GD.PrintErr($"Failed to load weapon_data.json: {e.Message}");
        }
    }

    public void EquipWeapon(string weaponId)
    {
        if (!_weapons.ContainsKey(weaponId)) return;

        _currentWeaponId = weaponId;
        _currentWeapon = _weapons[weaponId];
        _currentAmmo = _currentWeapon.MagazineSize;
        _reserveAmmo = _currentWeapon.MaxAmmo;
        _fireTimer = 0f;
        _isReloading = false;

        EmitSignal(SignalName.AmmoChanged, PlayerIndex, _currentAmmo, _reserveAmmo);
    }

    public void Fire(bool triggerHeld)
    {
        if (_isReloading || _currentWeapon == null) return;

        if (_fireTimer > 0)
        {
            _fireTimer -= (float)GetPhysicsProcessDeltaTime();
            return;
        }

        if (_currentAmmo <= 0)
        {
            Reload();
            return;
        }

        _currentAmmo--;
        _fireTimer = 1f / _currentWeapon.RoundsPerSecond;

        // Perform hitscan or melee
        if (_currentWeapon.Type == "hitscan")
            PerformHitscan();
        else if (_currentWeapon.Type == "melee")
            PerformMelee();

        EmitSignal(SignalName.WeaponFired, PlayerIndex, _currentWeapon.Id);
        EmitSignal(SignalName.AmmoChanged, PlayerIndex, _currentAmmo, _reserveAmmo);

        if (_currentAmmo <= 0 && _reserveAmmo <= 0)
            Reload();
    }

    private void PerformHitscan()
    {
        var player = GetParent();
        if (player == null) return;

        var camera = player.GetNode<Camera3D>("Camera3D");
        if (camera == null) return;

        var spaceState = player.GetWorld3D().DirectSpaceState;
        var from = camera.GlobalPosition;
        var to = from + camera.GlobalTransform.Basis.Z * -_currentWeapon.Range;

        // Apply spread
        var spread = _currentWeapon.Spread * 0.01f;
        to += new Vector3(
            (float)GD.RandRange(-spread, spread),
            (float)GD.RandRange(-spread, spread),
            (float)GD.RandRange(-spread, spread)
        );

        var query = PhysicsRayQueryParameters3D.Create(from, to);
        query.CollisionMask = 2; // Player layer
        var result = spaceState.IntersectRay(query);

        if (result.Count > 0)
        {
            var collider = (Node3D)result["collider"];
            if (collider is PlayerController other)
            {
                float damage = _currentWeapon.Damage;
                // Headshot check
                var hitPos = (Vector3)result["position"];
                var headPos = other.GlobalPosition + Vector3.Up * 1.1f;
                if (hitPos.DistanceTo(headPos) < 0.2f && _currentWeapon.CanHeadshot)
                    damage *= _currentWeapon.HeadshotMultiplier;

                other.TakeDamage(damage, ((PlayerController)player).PlayerIndex);
            }
        }
    }

    private void PerformMelee()
    {
        // Melee handled by PlayerController.PerformMelee()
    }

    public void Reload()
    {
        if (_isReloading || _currentWeapon == null) return;
        if (_currentAmmo == _currentWeapon.MagazineSize) return;
        if (_reserveAmmo <= 0) return;

        _isReloading = true;
        float reloadTime = (_currentAmmo == 0 && _currentWeapon.ReloadEmpty > 0)
            ? _currentWeapon.ReloadEmpty
            : _currentWeapon.ReloadTime;

        GetTree().CreateTimer(reloadTime).Timeout += () =>
        {
            int needed = _currentWeapon.MagazineSize - _currentAmmo;
            int transfer = Math.Min(needed, _reserveAmmo);
            _currentAmmo += transfer;
            _reserveAmmo -= transfer;
            _isReloading = false;
            EmitSignal(SignalName.WeaponReloaded, PlayerIndex, _currentWeapon.Id);
            EmitSignal(SignalName.AmmoChanged, PlayerIndex, _currentAmmo, _reserveAmmo);
        };
    }

    public void SwapWeapon(string newWeaponId)
    {
        if (_isReloading || newWeaponId == _currentWeaponId) return;
        var old = _currentWeaponId;
        EquipWeapon(newWeaponId);
        EmitSignal(SignalName.WeaponSwapped, PlayerIndex, old, newWeaponId);
    }

    public int GetCurrentAmmo() => _currentAmmo;
    public int GetReserveAmmo() => _reserveAmmo;
    public string GetCurrentWeaponId() => _currentWeaponId;
}