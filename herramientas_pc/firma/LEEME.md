# Firma fija de Kira

Android solo deja **actualizar** una app (instalar el APK nuevo encima del viejo, sin perder nada) si los dos APK
llevan la **misma firma**. Antes, cada compilación en GitHub creaba una firma nueva y había que desinstalar Kira.

`kira_debug.keystore` es la firma fija (alias `androiddebugkey`, contraseña `android`, como la de depuración
estándar de Android). El workflow `compilar_apk.yml` la copia a `~/.android/debug.keystore` antes de compilar y
comprueba después que el APK la lleva.

**Más privado (opcional):** como el repositorio es público, cualquiera podría firmar un APK con esta misma firma.
Kira solo se instala desde los APK que tú descargas, así que el riesgo es pequeño; aun así, si quieres que nadie más
la tenga, crea otra firma, guárdala en GitHub → Settings → Secrets and variables → Actions → **KIRA_KEYSTORE_B64**
(el archivo en base64) y el workflow usará esa. Ojo: cambiar de firma obliga a desinstalar Kira UNA vez más.
