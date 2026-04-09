import os
import re
import base64
import logging
import httpx
from urllib.parse import urlparse, unquote
from azure.identity import CertificateCredential, ClientSecretCredential, DefaultAzureCredential
from app.config import settings

logger = logging.getLogger(__name__)


class GraphClientError(Exception):
    """Custom exception for Graph API errors."""
    pass


class GraphClient:
    """Microsoft Graph API client for SharePoint file operations."""

    def __init__(self):
        self._credential = None
        self._token = None

    @property
    def credential(self):
        if self._credential is None:
            if settings.azure_client_secret:
                self._credential = ClientSecretCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret,
                )
            elif settings.azure_client_certificate_path:
                self._credential = CertificateCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    certificate_path=settings.azure_client_certificate_path,
                    password=settings.azure_client_certificate_password or None,
                )
            else:
                # Use DefaultAzureCredential for Managed Identity on App Service
                self._credential = DefaultAzureCredential()
        return self._credential

    async def _get_token(self) -> str:
        """Get a Graph API access token."""
        token = self.credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    @staticmethod
    def is_sharing_link(url: str) -> bool:
        """Check if a URL is a SharePoint sharing link (e.g. /:w:/s/... or /:b:/s/...)."""
        parsed = urlparse(url)
        return bool(re.match(r"^/:[\.\w]:/(s|r)/", parsed.path))

    @staticmethod
    def _encode_sharing_url(url: str) -> str:
        """Encode a sharing URL to a share token for the Graph /shares API."""
        encoded = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
        return "u!" + encoded.rstrip("=")

    async def resolve_sharing_link(self, url: str) -> dict:
        """Resolve a SharePoint sharing link to driveItem metadata via Graph /shares API.

        Returns dict with keys: drive_id, item_id, filename, parent_path.
        """
        share_token = self._encode_sharing_url(url)
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://graph.microsoft.com/v1.0/shares/{share_token}/driveItem",
                headers=headers,
            )
            if resp.status_code != 200:
                raise GraphClientError(
                    f"Failed to resolve sharing link: {resp.status_code} - {resp.text}"
                )
            item = resp.json()

        parent_ref = item.get("parentReference", {})
        return {
            "drive_id": parent_ref.get("driveId", ""),
            "item_id": item["id"],
            "filename": item["name"],
            "parent_path": parent_ref.get("path", ""),
        }

    def parse_sharepoint_url(self, url: str) -> dict:
        """Parse a SharePoint URL to extract site hostname, site path, and file path.

        Handles URLs like:
        - https://contoso.sharepoint.com/sites/mysite/Shared Documents/folder/file.docx
        - https://contoso-my.sharepoint.com/personal/user/Documents/file.docx
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        path = unquote(parsed.path)

        # Extract site path and file path
        # Pattern: /sites/{sitename}/... or /personal/{username}/...
        site_match = re.match(r"^(/(?:sites|personal)/[^/]+)(/.+)$", path)
        if site_match:
            site_path = site_match.group(1)
            file_path = site_match.group(2)
            # Remove common SharePoint path prefixes
            file_path = re.sub(r"^/Shared Documents", "/Shared Documents", file_path)
        else:
            raise GraphClientError(f"Could not parse SharePoint URL: {url}")

        return {
            "hostname": hostname,
            "site_path": site_path,
            "file_path": file_path,
            "filename": os.path.basename(file_path),
        }

    async def get_site_and_drive(
        self, hostname: str, site_path: str, library_name: str = ""
    ) -> tuple[str, str]:
        """Resolve site ID and drive ID from hostname and site path.

        If library_name is provided, resolve the drive for that specific
        document library instead of the default one.
        """
        if settings.sharepoint_site_id and settings.sharepoint_drive_id and not library_name:
            return settings.sharepoint_site_id, settings.sharepoint_drive_id

        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            # Get site ID
            site_url = (
                f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
            )
            resp = await client.get(site_url, headers=headers)
            if resp.status_code != 200:
                raise GraphClientError(
                    f"Failed to resolve site: {resp.status_code} - {resp.text}"
                )
            site_id = resp.json()["id"]

            if library_name:
                # List all drives and find the one matching the library name
                drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
                resp = await client.get(drives_url, headers=headers)
                if resp.status_code != 200:
                    raise GraphClientError(
                        f"Failed to list drives: {resp.status_code} - {resp.text}"
                    )
                drives = resp.json().get("value", [])
                drive_id = None
                for drive in drives:
                    if drive.get("name", "").lower() == library_name.lower():
                        drive_id = drive["id"]
                        break
                if not drive_id:
                    available = [d.get("name", "") for d in drives]
                    raise GraphClientError(
                        f"Document library '{library_name}' not found. "
                        f"Available libraries: {available}"
                    )
            else:
                # Get default drive (document library)
                drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
                resp = await client.get(drive_url, headers=headers)
                if resp.status_code != 200:
                    raise GraphClientError(
                        f"Failed to get drive: {resp.status_code} - {resp.text}"
                    )
                drive_id = resp.json()["id"]

        return site_id, drive_id

    async def download_file(self, document_url: str) -> str:
        """Download a file from SharePoint to local temp directory.

        Supports both direct file URLs and sharing links.
        Returns the local file path.
        """
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        if self.is_sharing_link(document_url):
            resolved = await self.resolve_sharing_link(document_url)
            download_url = (
                f"https://graph.microsoft.com/v1.0/drives/{resolved['drive_id']}"
                f"/items/{resolved['item_id']}/content"
            )
            filename = resolved["filename"]
        else:
            parsed = self.parse_sharepoint_url(document_url)
            site_id, drive_id = await self.get_site_and_drive(
                parsed["hostname"], parsed["site_path"]
            )
            download_url = (
                f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
                f"/root:{parsed['file_path']}:/content"
            )
            filename = parsed["filename"]

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(download_url, headers=headers)

            if resp.status_code != 200:
                raise GraphClientError(
                    f"Failed to download file: {resp.status_code} - {resp.text}"
                )

            os.makedirs(settings.temp_dir, exist_ok=True)
            local_path = os.path.join(settings.temp_dir, filename)
            with open(local_path, "wb") as f:
                f.write(resp.content)

            logger.info(
                f"Downloaded {filename} ({len(resp.content)} bytes) to {local_path}"
            )
            return local_path

    async def upload_file(
        self, local_path: str, document_url: str, output_filename: str = "",
        output_folder_url: str = "",
    ) -> str:
        """Upload a file to SharePoint, returning the web URL of the uploaded file.

        If output_folder_url is provided, uploads there instead of the source folder.
        Supports both direct file URLs and sharing links.
        """
        if output_folder_url:
            # Parse the folder URL to get site info and the path after the site
            folder_parsed = self.parse_sharepoint_url(output_folder_url)
            # file_path looks like "/Redlined Contracts/" or "/Shared Documents/subfolder/"
            # The first segment is the document library name, rest is subfolder path
            path_parts = folder_parsed["file_path"].strip("/").split("/", 1)
            library_name = path_parts[0] if path_parts else "Shared Documents"
            subfolder = "/" + path_parts[1] if len(path_parts) > 1 else ""
            site_id, drive_id = await self.get_site_and_drive(
                folder_parsed["hostname"], folder_parsed["site_path"],
                library_name=library_name,
            )
            if not output_filename:
                if self.is_sharing_link(document_url):
                    resolved = await self.resolve_sharing_link(document_url)
                    name, ext = os.path.splitext(resolved["filename"])
                else:
                    parsed = self.parse_sharepoint_url(document_url)
                    name, ext = os.path.splitext(parsed["filename"])
                output_filename = f"{name}_redlined{ext}"
            upload_path = f"{subfolder}/{output_filename}"
        elif self.is_sharing_link(document_url):
            resolved = await self.resolve_sharing_link(document_url)
            drive_id = resolved["drive_id"]
            if not output_filename:
                name, ext = os.path.splitext(resolved["filename"])
                output_filename = f"{name}_redlined{ext}"
            # parent_path from Graph looks like /drives/{id}/root:/folder
            # Extract the folder path after "root:"
            raw_parent = resolved["parent_path"]
            folder_path = raw_parent.split("root:", 1)[-1] if "root:" in raw_parent else ""
            upload_path = f"{folder_path}/{output_filename}"
        else:
            parsed = self.parse_sharepoint_url(document_url)
            site_id, drive_id = await self.get_site_and_drive(
                parsed["hostname"], parsed["site_path"]
            )
            if not output_filename:
                name, ext = os.path.splitext(parsed["filename"])
                output_filename = f"{name}_redlined{ext}"
            parent_path = os.path.dirname(parsed["file_path"])
            upload_path = f"{parent_path}/{output_filename}"

        token = await self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        with open(local_path, "rb") as f:
            content = f.read()

        async with httpx.AsyncClient() as client:
            upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{upload_path}:/content"
            resp = await client.put(upload_url, headers=headers, content=content)

            if resp.status_code not in (200, 201):
                raise GraphClientError(
                    f"Failed to upload file: {resp.status_code} - {resp.text}"
                )

            result = resp.json()
            web_url = result.get("webUrl", "")
            logger.info(
                f"Uploaded {output_filename} ({len(content)} bytes) to SharePoint"
            )
            return web_url

    def cleanup_temp_file(self, local_path: str):
        """Remove a temporary local file."""
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.debug(f"Cleaned up temp file: {local_path}")
        except OSError as e:
            logger.warning(f"Failed to clean up temp file {local_path}: {e}")


# Singleton instance
graph_client = GraphClient()
