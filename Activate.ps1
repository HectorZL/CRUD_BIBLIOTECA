# Activate.ps1
$envFile = ".\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $name, $value = $_.Split('=', 2)
        if ($name -and $name -notmatch '^#' -and $value) {
            $value = $value.Trim()
            [Environment]::SetEnvironmentVariable($name.Trim(), $value, "Process")
            Write-Host "Variable cargada: $($name.Trim())"
        }
    }
}

# Verificar que las variables requeridas estén configuradas
$requiredVars = @("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DB")
foreach ($var in $requiredVars) {
    if (-not [Environment]::GetEnvironmentVariable($var)) {
        Write-Warning "Advertencia: La variable $var no está configurada"
    }
}

Write-Host "`nVariables de entorno cargadas correctamente"