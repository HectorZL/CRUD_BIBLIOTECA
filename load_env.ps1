# Script para cargar variables de entorno desde .env
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

# Verificar variables requeridas
$requiredVars = @("MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
foreach ($var in $requiredVars) {
    if (-not [Environment]::GetEnvironmentVariable($var)) {
        Write-Warning "Advertencia: La variable $var no está configurada"
    } else {
        Write-Host "$var está configurado correctamente"
    }
}

Write-Host "`nVariables de entorno cargadas correctamente"
