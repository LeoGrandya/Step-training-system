# Reset dev database pose3d_project_3 (drops all tables/data).
# Usage: powershell -File web_1\scripts\reset_pose3d_mysql_db.ps1

$mysql = "C:\Program Files\MySQL\MySQL Server 5.5\bin\mysql.exe"
if (-not (Test-Path $mysql)) {
    Write-Error "mysql.exe not found at $mysql — adjust path for your install."
    exit 1
}

$user = if ($env:MYSQL_USER) { $env:MYSQL_USER } else { "root" }
$pass = if ($env:MYSQL_PASSWORD) { $env:MYSQL_PASSWORD } else { "root" }

& $mysql -u $user "-p$pass" -e @"
DROP DATABASE IF EXISTS pose3d_project_3;
CREATE DATABASE pose3d_project_3 CHARACTER SET utf8 COLLATE utf8_general_ci;
"@

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Database pose3d_project_3 reset OK. Next: cd web_1; python -m alembic upgrade head"
