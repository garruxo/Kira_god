File_manager
"""
KiraOS - Utilidad de Control de Archivos y Backups (utils/file_manager.py)
"""
import os
import shutil
import logging
from datetime import datetime
logger = logging.getLogger("KiraFileManager")
class KiraFileManager:
    def __init__(self, backup_dir="kira_backups"):
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)
    def crear_backup(self, file_path: str) -> str:
        """Crea una copia de seguridad con marca de tiempo antes de alterar un archivo."""
        if not os.path.exists(file_path):
            return f"[x] El archivo {file_path} no existe para respaldar."
        
        try:
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{timestamp}_{filename}"
            destination = os.path.join(self.backup_dir, backup_name)
            
            shutil.copy2(file_path, destination)
            logger.info(f"Backup creado con éxito para {file_path} en {destination}")
            return f"[✔] Backup guardado en: {destination}"
        except Exception as e:
            logger.error(f"Error creando backup de {file_path}: {e}")
            return f"[x] Error al crear backup: {e}"
    def leer_archivo_seguro(self, file_path: str) -> str:
        """Lee el contenido de un archivo de texto de forma segura."""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"[x] Error al leer el archivo: {e}"
        return f"[x] El archivo {file_path} no se encuentra."
    def escribir_archivo_seguro(self, file_path: str, contenido: str) -> str:
        """Crea un backup previo automático y escribe el nuevo contenido."""
        if os.path.exists(file_path):
            self.crear_backup(file_path)
            
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(contenido)
            logger.info(f"Archivo modificado y guardado de forma segura: {file_path}")
            return f"[✔] Archivo actualizado correctamente: {file_path}"
        except Exception as e:
            logger.error(f"Error escribiendo en {file_path}: {e}")
            return f"[x] Error al escribir el archivo: {e}"
