@echo off
cd /d "%~dp0.."
set "LOG=diag.log"
set "WP=80"
for /f "tokens=2 delims==" %%a in ('findstr /b /c:"WEB_PORT=" ".env" 2^>nul') do set "WP=%%a"
echo == containers > "%LOG%"
docker compose ps >> "%LOG%" 2>&1
echo == variables de l API >> "%LOG%"
docker compose exec -T api printenv SALUBRI_DEMO_MODE SALUBRI_DATA_MODE >> "%LOG%" 2>&1
echo == le code de l image connait l admin par defaut >> "%LOG%"
docker compose exec -T api python -c "from salubri_api.config import get_settings as g;s=g();print(s.default_admin_login, s.demo_mode)" >> "%LOG%" 2>&1
echo == comptes >> "%LOG%"
docker compose exec -T api python -m salubri_api.users list >> "%LOG%" 2>&1
echo == connexion admin >> "%LOG%"
curl.exe -s -m 10 --noproxy "*" -X POST http://127.0.0.1:%WP%/api/auth/login -H "Content-Type: application/json" -d "{\"login\":\"admin\",\"password\":\"Salubri2026\"}" >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo == journal de l API >> "%LOG%"
docker compose logs api --tail 400 2>&1 | findstr /i "admin demonstration traceback error refus" >> "%LOG%"
echo FIN >> "%LOG%"

pause
