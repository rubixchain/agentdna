# tools/google/google_apis.py
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def create_service(client_secret_file, api_name, api_version, scopes, prefix: str = ""):
    # token dir: <project_root>/token files/
    project_root = Path(__file__).resolve().parents[2]
    token_dir = Path(os.getenv("GOOGLE_TOKEN_DIR", project_root / "token files"))
    token_dir.mkdir(parents=True, exist_ok=True)

    token_file = token_dir / f"token_{api_name}_{api_version}{prefix}.json"
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0, open_browser=True)
        token_file.write_text(creds.to_json())

    return build(api_name, api_version, credentials=creds, static_discovery=False)