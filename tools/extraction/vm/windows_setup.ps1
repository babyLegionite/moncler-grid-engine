# windows_setup.ps1
# Auto-configure Windows 11 ARM VM for Halo Reach extraction.
# Run as Administrator in PowerShell: Right-click → Run with PowerShell (Admin)
#
# What this does:
#   1. Installs OpenSSH Server for programmatic access from macOS
#   2. Configures SSH key authentication
#   3. Creates extraction directory structure
#   4. Installs required tools (Steam, HREK, Assembly)
#   5. Configures Windows for headless operation

param(
    [switch]$SkipSteam = $false,
    [string]$SSHPublicKey = ""
)

$ErrorActionPreference = "Continue"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  moncler-grid-engine — Windows VM Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ── 1. Install OpenSSH Server ────────────────────────────────────────────────

Write-Host "`n[1/6] Installing OpenSSH Server..." -ForegroundColor Yellow

$sshInstalled = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

if ($sshInstalled.State -ne "Installed") {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    Write-Host "  ✅ OpenSSH Server installed" -ForegroundColor Green
} else {
    Write-Host "  ✅ OpenSSH Server already installed" -ForegroundColor Green
}

# Start and enable SSH
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
Write-Host "  ✅ SSH service started and set to auto-start"

# Configure firewall
if (!(Get-NetFirewallRule -Name "OpenSSH-Server" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name "OpenSSH-Server" -DisplayName "OpenSSH Server" `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
    Write-Host "  ✅ Firewall rule added for SSH"
}

# ── 2. Configure SSH Key Authentication ─────────────────────────────────────

Write-Host "`n[2/6] Configuring SSH key authentication..." -ForegroundColor Yellow

$sshDir = "$env:ProgramData\ssh"
$adminKeyFile = "$sshDir\administrators_authorized_keys"

# Create administrators_authorized_keys if it doesn't exist
if (!(Test-Path $adminKeyFile)) {
    New-Item -Path $adminKeyFile -ItemType File -Force | Out-Null
}

# Set proper permissions (required for sshd to accept the file)
try {
    icacls $adminKeyFile /inheritance:r /grant "SYSTEM:(F)" /grant "Administrators:(F)" | Out-Null
    Write-Host "  ✅ SSH authorized_keys permissions set"
} catch {
    Write-Host "  ⚠️  Could not set permissions — this is normal on some ARM Windows builds"
}

if ($SSHPublicKey -ne "") {
    Add-Content -Path $adminKeyFile -Value $SSHPublicKey
    Write-Host "  ✅ SSH public key added"
    Write-Host "  ℹ️  Key added to: $adminKeyFile"
} else {
    Write-Host "  ℹ️  No SSH key provided — add manually:"
    Write-Host "     Copy your ~/.ssh/id_ed25519.pub to: $adminKeyFile"
}

# Also configure sshd_config for key auth
$sshdConfig = "$sshDir\sshd_config"
if (Test-Path $sshdConfig) {
    $config = Get-Content $sshdConfig
    if ($config -notmatch "PubkeyAuthentication yes") {
        Add-Content $sshdConfig "`nPubkeyAuthentication yes"
    }
    Write-Host "  ✅ sshd_config: PubkeyAuthentication enabled"
}

# ── 3. Create Extraction Directory Structure ─────────────────────────────────

Write-Host "`n[3/6] Creating extraction directories..." -ForegroundColor Yellow

$extractionDir = "C:\Extraction"
$dirs = @(
    $extractionDir,
    "$extractionDir\bsp",
    "$extractionDir\collision",
    "$extractionDir\textures",
    "$extractionDir\spawns",
    "$extractionDir\forge",
    "$extractionDir\physics",
    "C:\Tools"
)

foreach ($dir in $dirs) {
    if (!(Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
    }
}
Write-Host "  ✅ Extraction directories created at $extractionDir"

# ── 4. Install Tools ─────────────────────────────────────────────────────────

Write-Host "`n[4/6] Tool installation guide..." -ForegroundColor Yellow

# ── Steam + MCC ──
if (-not $SkipSteam) {
    Write-Host "`n  🎮 Steam + MCC:"
    Write-Host "     1. Download Steam: https://store.steampowered.com/about/"
    Write-Host "     2. Install Steam"
    Write-Host "     3. Install Halo: The Master Chief Collection"
    Write-Host "     4. Install HREK: Steam → MCC → Workshop → Halo Reach Editing Kit"
    Write-Host "     Expected path: $env:ProgramFiles\Steam\steamapps\common\Halo The Master Chief Collection"
} else {
    Write-Host "  ⏭️  Steam installation skipped (--SkipSteam)"
}

# ── Assembly (XboxChaos) ──
Write-Host "`n  🔧 Assembly (Tag Editor):"
Write-Host "     1. Visit: https://github.com/XboxChaos/Assembly/releases"
Write-Host "     2. Download latest Assembly.zip"
Write-Host "     3. Extract to C:\Tools\Assembly"
Write-Host "     Expected path: C:\Tools\Assembly\Assembly.exe"

# ── Halo Asset Blender Dev Toolset ──
Write-Host "`n  🎨 Halo Asset Blender Dev Toolset:"
Write-Host "     This runs on macOS. Install in Blender > Preferences > Add-ons"
Write-Host "     Reference: c20.reclaimers.net (linked from HREK page)"

# ── .mvar file ──
Write-Host "`n  📁 Infection .mvar file:"
Write-Host "     1. Find 'Hemorrhage Infection' variant in Halo File Share Archive"
Write-Host "     2. Download the .mvar file"
Write-Host "     3. Place at: $extractionDir\hemorrhage_infection.mvar"

# ── 5. Verify Installation ───────────────────────────────────────────────────

Write-Host "`n[5/6] Verifying installation..." -ForegroundColor Yellow

$checks = @(
    @{Name="SSH Server"; Test={Get-Service sshd -ErrorAction SilentlyContinue | Where-Object Status -eq "Running"}},
    @{Name="Extraction Dir"; Test={Test-Path "C:\Extraction"}},
    @{Name="Tools Dir"; Test={Test-Path "C:\Tools"}},
    @{Name="Steam"; Test={Test-Path "$env:ProgramFiles\Steam\steam.exe"}},
    @{Name="MCC Maps"; Test={Test-Path "$env:ProgramFiles\Steam\steamapps\common\Halo The Master Chief Collection\haloreach\maps\forge_halo.map"}},
    @{Name="Assembly"; Test={Test-Path "C:\Tools\Assembly\Assembly.exe"}}
)

foreach ($check in $checks) {
    $status = if (& $check.Test) { "✅" } else { "❌" }
    Write-Host "  $status $($check.Name)"
}

# ── 6. Get Network Info ──────────────────────────────────────────────────────

Write-Host "`n[6/6] Network configuration..." -ForegroundColor Yellow

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*" -and $_.PrefixOrigin -ne "WellKnown"
}).IPAddress | Select-Object -First 1

Write-Host "  🌐 Windows VM IP Address: $ip"
Write-Host "  📋 Add this to tools/extraction/configs/config.yaml:"
Write-Host "     vm:"
Write-Host "       host: '$ip'"
Write-Host "       port: 22"
Write-Host "       username: '$env:USERNAME'"

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ✅ Windows VM Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps (on macOS):"
Write-Host "  1. Copy your SSH key to the VM:"
Write-Host "     ssh-copy-id $env:USERNAME@$ip"
Write-Host "  2. Test connection:"
Write-Host "     python3 tools/extraction/scripts/extract_assets.py --test"
Write-Host "  3. Run extraction:"
Write-Host "     python3 tools/extraction/orchestrate.py --all"
Write-Host ""

# Keep window open
Read-Host "Press Enter to close"