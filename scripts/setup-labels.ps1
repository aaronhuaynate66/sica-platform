# Sincroniza labels del repo con .github/labels-init.yml — Windows.
#
# Idempotente. Requiere `gh` CLI autenticado.
# A diferencia del .sh, no necesita `yq`: parsea el YAML con un
# regex minimo (es un formato chico y controlado).

[CmdletBinding()]
param(
    [string]$Repo = "aaronhuaynate66/sica-platform",
    [string]$LabelsFile = ".github/labels-init.yml"
)

$ErrorActionPreference = "Stop"

function Test-GhInstalled {
    try {
        $null = Get-Command gh -ErrorAction Stop
        return $true
    } catch {
        Write-Error "gh CLI no instalado. Instalalo desde https://cli.github.com"
        return $false
    }
}

if (-not (Test-GhInstalled)) { exit 1 }
if (-not (Test-Path $LabelsFile)) {
    Write-Error "No existe $LabelsFile en este directorio."
    exit 1
}

# Parser ligero: cada entrada empieza con "- name:" y agrupa los campos
# siguientes hasta el proximo "- name:" o EOF.
$content = Get-Content $LabelsFile -Raw -Encoding UTF8
$entries = @()
$current = $null
foreach ($line in $content -split "`r?`n") {
    if ($line -match '^\s*-\s+name:\s*"?([^"]+)"?\s*$') {
        if ($current) { $entries += [PSCustomObject]$current }
        $current = @{ name = $Matches[1].Trim(); color = ""; description = "" }
    } elseif ($line -match '^\s+color:\s*"?([^"]+)"?\s*$' -and $current) {
        $current.color = $Matches[1].Trim()
    } elseif ($line -match '^\s+description:\s*"?(.+?)"?\s*$' -and $current) {
        $current.description = $Matches[1].Trim()
    }
}
if ($current) { $entries += [PSCustomObject]$current }

Write-Host "-> Sincronizando $($entries.Count) labels contra $Repo..."

$existing = gh label list --repo $Repo --json name -q '.[].name' | ForEach-Object { $_.Trim() }

foreach ($e in $entries) {
    if ($existing -contains $e.name) {
        gh label edit $e.name --repo $Repo --color $e.color --description $e.description | Out-Null
        Write-Host "  . actualizado: $($e.name)"
    } else {
        gh label create $e.name --repo $Repo --color $e.color --description $e.description | Out-Null
        Write-Host "  + creado: $($e.name)"
    }
}

Write-Host ""
Write-Host "OK. Labels sincronizados ($($entries.Count) total)."
