from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Microsoft Graph / Azure AD
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_client_certificate_path: str = ""
    azure_client_certificate_password: str = ""

    # SharePoint
    sharepoint_site_id: str = ""
    sharepoint_drive_id: str = ""

    # API Security
    api_key: str = ""

    # App
    app_name: str = "Contract Redline Tool"
    debug: bool = False
    temp_dir: str = "/tmp/redline"

    # Redline defaults
    default_author: str = "Contract Review Agent"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
