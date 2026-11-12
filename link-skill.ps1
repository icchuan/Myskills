<#
.SYNOPSIS
把 agent-skills 里的一个技能链接到指定项目的 .agents\skills 下。
#>
param(
  [Parameter(Mandatory = $true)][string]$Skill,
  [string]$Project = (Get-Location).Path
)

$source = Join-Path $PSScriptRoot $Skill
if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md'))) {
  throw "技能不存在或缺少 SKILL.md：$source"
}

$target = Join-Path $Project ".agents\skills\$Skill"
New-Item -ItemType Directory -Force (Split-Path $target -Parent) | Out-Null

if (Test-Path -LiteralPath $target) {
  $existing = Get-Item -LiteralPath $target -Force
  throw "目标已存在（$($existing.LinkType)）：$target"
}

New-Item -ItemType Junction -Path $target -Target $source | Out-Null
"linked: $target -> $source"
