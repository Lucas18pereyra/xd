# Controla Tu Vida (online + login)

App movil en Python + Flet con:
- Login/registro por email y contrasena (Supabase Auth).
- Base de datos compartida en la nube (Postgres en Supabase).
- Datos separados por usuario con RLS (seguridad por fila).

## 1) Crear proyecto en Supabase
1. Crea una cuenta/proyecto en Supabase.
2. En `SQL Editor`, ejecuta `supabase/schema.sql`.
3. En `Settings -> API`, copia:
   - `Project URL`
   - `anon public key`

## 2) Configurar variables de entorno
Opcion A (recomendada): crea un archivo `.env` en la raiz del proyecto:

```env
SUPABASE_URL=https://TU-PROYECTO.supabase.co
SUPABASE_ANON_KEY=TU-ANON-LEGACY-JWT
```

Opcion B: en PowerShell (misma terminal donde ejecutaras la app):

```powershell
$env:SUPABASE_URL="https://TU-PROYECTO.supabase.co"
$env:SUPABASE_ANON_KEY="TU-ANON-LEGACY-JWT"
```

Tambien tienes un ejemplo en `.env.example`.

## 3) Instalar y ejecutar
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 4) Probar flujo
1. Crear cuenta.
2. Iniciar sesion.
3. Crear habitos/recordatorios.
4. Cerrar sesion y entrar con otro usuario para verificar que no comparten datos privados.

## Nota
- Si en Supabase tienes confirmacion por email activa, despues de crear cuenta debes confirmar el correo antes de iniciar sesion.
- Si aparece `Invalid API key`, usa la `anon` legacy (JWT que empieza con `eyJ...`) para `SUPABASE_ANON_KEY`.

## Android (APK)
Build debug:

```powershell
.\.venv\Scripts\flet.exe build apk
```

Build release firmado (cuando tengas keystore):

```powershell
.\.venv\Scripts\flet.exe build apk --android-signing-key-store "ruta\\upload-keystore.jks" --android-signing-key-store-password "TU_STORE_PASS" --android-signing-key-password "TU_KEY_PASS" --android-signing-key-alias "upload"
```
