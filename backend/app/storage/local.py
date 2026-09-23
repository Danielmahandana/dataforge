import os
import shutil
import hashlib
from pathlib import Path
from typing import Tuple
import aiofiles
from fastapi import UploadFile
from backend.app.config import settings

class LocalStorageManager:
    def __init__(self):
        self.uploads_dir = settings.uploads_path
        self.raw_dir = settings.raw_path
        self.processed_dir = settings.processed_path
        self.exports_dir = settings.exports_path
        self.temp_dir = settings.temp_path

    async def save_upload(self, file: UploadFile, doc_id: str) -> Tuple[str, str, int, str]:
        """
        Saves uploaded file to disk.
        Returns: (relative_file_path, original_filename, file_size, sha256_hash)
        """
        original_name = file.filename or "unnamed_document.pdf"
        ext = Path(original_name).suffix.lower()
        if not ext:
            ext = ".pdf"
        
        safe_filename = f"{doc_id}_{Path(original_name).stem[:50]}{ext}"
        target_path = self.uploads_dir / safe_filename

        hasher = hashlib.sha256()
        total_size = 0

        async with aiofiles.open(target_path, "wb") as out_file:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(content)
                hasher.update(content)
                await out_file.write(content)

        return str(target_path), original_name, total_size, hasher.hexdigest()

    def get_file_path(self, path_str: str) -> Path:
        return Path(path_str).resolve()

    def delete_file(self, path_str: str) -> bool:
        try:
            p = Path(path_str)
            if p.exists() and p.is_file():
                p.unlink()
                return True
        except Exception:
            pass
        return False

    def save_export_file(self, filename: str, content: bytes) -> str:
        target = self.exports_dir / filename
        with open(target, "wb") as f:
            f.write(content)
        return str(target)

storage_manager = LocalStorageManager()
