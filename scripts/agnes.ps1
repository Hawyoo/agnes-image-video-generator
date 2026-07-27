param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AgnesArgs
)

$ErrorActionPreference = "Stop"
$Python = (Get-Command python -ErrorAction Stop).Source
$Client = Join-Path $PSScriptRoot "agnes_media.py"

& $Python -u $Client @AgnesArgs
exit $LASTEXITCODE
