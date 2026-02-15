from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient
from loguru import logger

from app.config import settings
from app.utils.file_utils import ensure_upload_dir, safe_filename


class StorageService:
    def __init__(self) -> None:
        self._connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self._container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        self._upload_dir = settings.UPLOAD_DIR
        self._client: BlobServiceClient | None = None

    async def _get_client(self) -> BlobServiceClient | None:
        if not self._connection_string:
            return None
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(
                self._connection_string
            )
        return self._client

    async def _ensure_container(self, client: BlobServiceClient) -> None:
        container_client = client.get_container_client(self._container_name)
        try:
            await container_client.create_container()
        except ResourceExistsError:
            return

    async def upload_file(
        self, content: bytes, filename: str, content_type: str
    ) -> str:
        clean_name = safe_filename(filename)
        if not self._connection_string:
            upload_dir = ensure_upload_dir(self._upload_dir)
            file_path = upload_dir / clean_name
            if file_path.exists():
                stem = file_path.stem
                suffix = file_path.suffix
                counter = 1
                while file_path.exists():
                    file_path = upload_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            file_path.write_bytes(content)
            return str(file_path)

        client = await self._get_client()
        if client is None:
            raise RuntimeError("Falha ao criar cliente de storage")

        await self._ensure_container(client)
        blob_name = clean_name
        container_client = client.get_container_client(self._container_name)
        blob_client = container_client.get_blob_client(blob_name)
        content_settings = ContentSettings(content_type=content_type)
        await blob_client.upload_blob(
            content, overwrite=True, content_settings=content_settings
        )
        return blob_client.url

    async def get_blob_content(self, blob_url: str) -> bytes:
        if not blob_url:
            raise FileNotFoundError("URL do blob vazia")

        local_path = Path(blob_url)
        if local_path.exists():
            return local_path.read_bytes()

        if blob_url.startswith("file://"):
            path = Path(blob_url.replace("file://", "", 1))
            if path.exists():
                return path.read_bytes()
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        client = await self._get_client()
        if client is None:
            raise FileNotFoundError(
                "Storage não configurado e arquivo local inexistente"
            )

        container_name, blob_name = self._parse_blob_url(blob_url)
        container_client = client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        downloader = await blob_client.download_blob()
        return await downloader.readall()

    def _parse_blob_url(self, blob_url: str) -> tuple[str, str]:
        parsed = urlparse(blob_url)
        parts = parsed.path.lstrip("/").split("/")
        if self._container_name in parts:
            idx = parts.index(self._container_name)
            container_name = parts[idx]
            blob_name = "/".join(parts[idx + 1 :])
            return container_name, blob_name
        if len(parts) >= 2:
            container_name = parts[-2]
            blob_name = parts[-1]
            return container_name, blob_name
        logger.warning(f"URL de blob inesperada: {blob_url}")
        return self._container_name, parts[-1] if parts else ""


storage_service = StorageService()
