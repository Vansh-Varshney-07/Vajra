"""
CARTO Data Warehouse & Spatial API Client for Vajra backend.

Provides python client interface to interact with CARTO SQL API and MCP endpoint:
- Query spatial datasets (districts, coastal zones, NWP mesh grid)
- Connection health check & verification
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

CARTO_API_BASE_URL = os.getenv("CARTO_API_BASE_URL", "https://gcp-asia-northeast1.api.carto.com")
CARTO_ACCOUNT_ID = os.getenv("CARTO_ACCOUNT_ID", "ac_yl5r440d")
CARTO_API_TOKEN = os.getenv("CARTO_API_TOKEN", "")


class CartoClient:
    def __init__(
        self,
        token: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.token = token or CARTO_API_TOKEN
        self.account_id = account_id or CARTO_ACCOUNT_ID
        self.base_url = base_url or CARTO_API_BASE_URL

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "Vajra-Threat-Tracker/1.0",
        }

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verify connection to CARTO platform and MCP integration.
        """
        if not self.is_configured:
            return {"connected": False, "error": "CARTO_API_TOKEN not configured in environment"}

        url = f"{self.base_url}/v3/connections"
        try:
            resp = requests.get(url, headers=self.authorization_header(), timeout=5)
            # CARTO API Access Token with MCP scope returns HTTP 403 listing allowed_apis: ["mcp", "resources"]
            data = resp.json() if resp.text.startswith('{') else {}
            allowed = data.get("allowed_a_p_is") or data.get("allowedAPIs") or []

            if resp.status_code == 200 or "mcp" in allowed or "resources" in allowed:
                return {
                    "connected": True,
                    "account_id": self.account_id,
                    "mcp_url": f"{self.base_url}/mcp/{self.account_id}",
                    "allowed_apis": allowed or ["mcp", "resources"],
                    "status": "ACTIVE",
                }
            return {"connected": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def authorization_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def query_sql(self, sql: str, connection: str = "carto_dw") -> Optional[Dict[str, Any]]:
        """
        Execute spatial SQL query against CARTO Data Warehouse.
        """
        if not self.is_configured:
            return None

        url = f"{self.base_url}/v3/sql/{self.account_id}/{connection}/query"
        try:
            resp = requests.post(
                url,
                headers=self._get_headers(),
                json={"q": sql},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except Exception as e:
            return {"error": str(e)}
