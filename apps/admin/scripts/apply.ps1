<#
.SYNOPSIS
一键把 Directus schema 快照 apply 到当前环境（含公共只读权限）。

.DESCRIPTION
步骤：
  1. `docker compose up -d mysql directus` 拉起依赖（不改 docker-compose.yml）
  2. 等 MySQL / Directus 就绪（compose 里 directus 无 restart 策略，MySQL 未就绪时容器会退出，脚本会自动补启动）
  3. 把 apps/admin/schema/snapshot.yaml 复制进 directus 容器并执行 `directus schema apply`
     （全新数据库若未安装 Directus，先执行 `directus bootstrap` 再 apply）
  4. 给 Public 政策补 nodes / contents 的只读权限（幂等）

.EXAMPLE
pwsh -File apps/admin/scripts/apply.ps1
pwsh -File apps/admin/scripts/apply.ps1 -SkipPermissions   # 只 apply schema
#>
[CmdletBinding()]
param(
    [string]$ComposeFile = (Resolve-Path (Join-Path $PSScriptRoot '../../..' 'docker-compose.yml')).Path,
    [string]$Snapshot = (Resolve-Path (Join-Path $PSScriptRoot '../schema/snapshot.yaml')).Path,
    [string]$DirectusUrl = 'http://127.0.0.1:8055',
    [string]$AdminEmail = 'admin@worldknowledge.org',
    [string]$AdminPassword = 'password',
    [switch]$SkipPermissions
)

$ErrorActionPreference = 'Stop'
$Service = 'directus'
$RemoteSnapshot = '/directus/uploads/schema-snapshot.yaml'
# Directus 内置的 Public 政策（固定 UUID）
$PublicPolicy = 'abf8a154-5b1c-4a46-ac9c-7300570f4f17'
$ReadCollections = @('nodes', 'contents')

function Compose { docker compose -f $ComposeFile @args }

function Get-DirectusContainer {
    $id = (Compose 'ps' '-q' $Service) | Select-Object -First 1
    if (-not $id) { throw "未找到 compose 服务 $Service 的容器，请先 docker compose up -d $Service" }
    return $id.Trim()
}

Write-Host '[1/4] 拉起依赖：mysql + directus'
Compose 'up' '-d' 'mysql' $Service | Out-Null

Write-Host '[2/4] 等待 MySQL 就绪…'
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Compose 'exec' '-T' 'mysql' 'mysqladmin' 'ping' '-uroot' '-ppassword' *> $null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Start-Sleep -Seconds 5
}
if (-not $ok) { throw 'MySQL 未就绪（30 次探测失败）' }

Write-Host '[3/4] 等待 Directus 就绪，并 apply schema 快照'
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        Invoke-WebRequest -Uri "$DirectusUrl/server/ping" -UseBasicParsing -TimeoutSec 5 *> $null
        $ready = $true; break
    } catch {
        # 容器可能在 MySQL 就绪前已退出，补一次 start
        $id = (Compose 'ps' '-a' '-q' $Service) | Select-Object -First 1
        if ($id) {
            $running = (docker inspect -f '{{.State.Running}}' $id.Trim()) -eq 'true'
            if (-not $running) { Compose 'start' $Service *> $null }
        }
        Start-Sleep -Seconds 5
    }
}
if (-not $ready) { throw "Directus 未就绪：$DirectusUrl" }

$container = Get-DirectusContainer
docker cp $Snapshot "${container}:$RemoteSnapshot" | Out-Null

function Invoke-DirectusCli([string[]]$CliArgs) {
    return (docker exec $container node /directus/cli.js @CliArgs 2>&1 | Out-String)
}

$applyOut = Invoke-DirectusCli @('schema', 'apply', '--yes', $RemoteSnapshot)
if ($applyOut -match "isn't installed") {
    Write-Host '  - 目标库未安装 Directus，先执行 bootstrap'
    $bootOut = Invoke-DirectusCli @('bootstrap')
    Write-Host ('    ' + ($bootOut.Trim() -split "`n" | Select-Object -Last 1))
    $applyOut = Invoke-DirectusCli @('schema', 'apply', '--yes', $RemoteSnapshot)
}
Write-Host ('    ' + ($applyOut.Trim() -split "`n" | Select-Object -Last 1))
if ($applyOut -notmatch 'Snapshot applied successfully|No changes to apply') { throw 'schema apply 未成功，请检查上方输出' }

if ($SkipPermissions) {
    Write-Host '[4/4] 已跳过公共只读权限'
    return
}

Write-Host '[4/4] 配置 Public 只读权限（nodes / contents）'
$body = @{ email = $AdminEmail; password = $AdminPassword } | ConvertTo-Json
$login = Invoke-RestMethod "$DirectusUrl/auth/login" -Method Post -ContentType 'application/json' -Body $body
$headers = @{ Authorization = "Bearer $($login.data.access_token)" }

$existing = @(Invoke-RestMethod "$DirectusUrl/permissions?limit=-1" -Headers $headers).data
$createdAny = $false
foreach ($collection in $ReadCollections) {
    $hit = $existing | Where-Object { $_.policy -eq $PublicPolicy -and $_.collection -eq $collection -and $_.action -eq 'read' }
    if ($hit) { Write-Host "  = 已存在：public read $collection（跳过）"; continue }
    # fields 必须为 '*'：Directus 12 对「字段级自定义权限规则」是受限资源（RESOURCE_RESTRICTED）
    $payload = @{ policy = $PublicPolicy; collection = $collection; action = 'read'; fields = '*' } | ConvertTo-Json -Compress
    $new = Invoke-RestMethod "$DirectusUrl/permissions" -Method Post -Headers $headers -ContentType 'application/json' -Body $payload
    Write-Host "  + 新建：public read $collection（id=$($new.data.id)）"
    $createdAny = $true
}

function Test-AnonymousRead {
    for ($i = 0; $i -lt 3; $i++) {
        try { $null = Invoke-RestMethod "$DirectusUrl/items/nodes?limit=1"; return $true } catch { Start-Sleep -Seconds 3 }
    }
    return $false
}

# 新建权限后 Directus 的公共权限缓存不会立即失效，需重启服务才生效
if ($createdAny -and -not (Test-AnonymousRead)) {
    Write-Host '  ! 公共权限未即时生效，重启 directus 容器刷新缓存'
    Compose 'restart' $Service | Out-Null
    for ($i = 0; $i -lt 20; $i++) {
        try { Invoke-WebRequest -Uri "$DirectusUrl/server/ping" -UseBasicParsing -TimeoutSec 3 *> $null; break } catch { Start-Sleep -Seconds 3 }
    }
}

if (Test-AnonymousRead) {
    $anon = Invoke-RestMethod "$DirectusUrl/items/nodes?limit=-1"
    Write-Host "  √ 匿名 GET /items/nodes -> $((@($anon.data)).Count) 条（公共读生效）"
} else {
    Write-Warning '匿名读 nodes 仍被拒绝，请检查 Public 政策权限'
}
Write-Host '完成。'
