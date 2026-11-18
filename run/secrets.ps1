# SPDX-License-Identifier: AGPL-3.0-or-later
# Hors démonstration (défaut ; SALUBRI_DEMO_MODE=true dans .env l'active) : génère une fois le code de service, la clé de
# session et le mot de passe du premier admin (compte « admin ») manquants, les écrit dans .env.
$ErrorActionPreference = 'Stop'
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
if (-not (Test-Path $envFile)) { New-Item -ItemType File -Path $envFile | Out-Null }
$lines = @(Get-Content -LiteralPath $envFile -Encoding UTF8)
if ($lines | Where-Object { $_ -match '^\s*SALUBRI_DEMO_MODE\s*=\s*true\s*$' }) { exit 0 }

function New-Secret {
  $b = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return (($b | ForEach-Object { $_.ToString('x2') }) -join '')
}
function Get-Value($name) {
  $l = $lines | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -Last 1
  if ($l) { return ($l -split '=', 2)[1].Trim() } else { return '' }
}

function New-Pass { $c='abcdefghjkmnpqrstuvwxyz23456789'; $r=New-Object byte[] 12; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($r); return -join ($r | ForEach-Object { $c[$_ % $c.Length] }) }
$created = @()
foreach ($name in 'SALUBRI_ADMIN_TOKEN', 'SALUBRI_SECRET_KEY') {
  $v = Get-Value $name
  if ($v -eq '' -or $v -eq 'ouaga2026' -or $v.Length -lt 16) {
    $new = New-Secret
    $lines = @($lines | Where-Object { $_ -notmatch "^\s*$name\s*=" }) + "$name=$new"
    $created += "$name=$new"
  }
}
$bp = Get-Value 'SALUBRI_BOOTSTRAP_ADMIN_PASSWORD'
if ($bp.Length -lt 8) {
  $newp = New-Pass
  $lines = @($lines | Where-Object { $_ -notmatch '^\s*SALUBRI_BOOTSTRAP_ADMIN_PASSWORD\s*=' }) + "SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=$newp"
  $created += "SALUBRI_BOOTSTRAP_ADMIN_PASSWORD=$newp"
}
if ($created.Count -gt 0) {
  # UTF-8 sans BOM : un BOM casserait la première variable lue par docker compose
  [System.IO.File]::WriteAllLines($envFile, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host ''
  Write-Host 'Premier lancement : secrets générés et enregistrés dans .env :'
  $created | ForEach-Object { Write-Host "  $_" }
  Write-Host 'Connexion mairie : identifiant admin, mot de passe SALUBRI_BOOTSTRAP_ADMIN_PASSWORD (relisible dans .env).'
  Write-Host 'Gardez le fichier .env privé.'
  Write-Host ''
}
