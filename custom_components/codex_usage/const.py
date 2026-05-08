"""Constants for Codex Usage integration."""

from homeassistant.const import Platform

DOMAIN = "codex_usage"
PLATFORMS = [Platform.SENSOR]

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_ISSUER = "https://auth.openai.com"

AUTH_METHOD_DEVICE = "device_code"
AUTH_METHOD_TOKEN = "access_token"
AUTH_METHOD_AUTH_JSON = "auth_json"

CONF_AUTH_METHOD = "auth_method"
CONF_CODEX_HOME = "codex_home"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ID_TOKEN = "id_token"
CONF_ACCOUNT_ID = "account_id"
CONF_BACKEND_URL = "backend_url"
CONF_REFRESH_URL = "refresh_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_CODEX_HOME = "~/.codex"
DEFAULT_BACKEND_URL = "https://chatgpt.com/backend-api/wham/usage"
DEFAULT_REFRESH_URL = "https://auth.openai.com/oauth/token"
DEFAULT_SCAN_INTERVAL = 60
