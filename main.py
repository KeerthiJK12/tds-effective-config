import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

def coerce_value(key: str, value: Any) -> Any:
    """Convert configuration strings to the required types."""
    if key in ("port", "workers"):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be an integer")

    if key == "debug":
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
        raise ValueError("debug must be true/false, 1/0, yes/no, or on/off")

    # log_level, api_key, and any other keys are strings.
    return str(value)

def apply_layer(config: dict[str, Any], layer: dict[str, Any]) -> None:
    for key, value in layer.items():
        if value is not None:
            config[key] = coerce_value(key, value)

def read_yaml() -> dict[str, Any]:
    path = BASE_DIR / "config.development.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError("config.development.yaml must contain a YAML object")
    return data

def read_dotenv_layer() -> dict[str, Any]:
    # Read .env separately so it stays a distinct precedence layer.
    raw = dotenv_values(BASE_DIR / ".env")
    layer: dict[str, Any] = {}
    for key, value in raw.items():
        if value is None:
            continue
        if key == "NUM_WORKERS":
            layer["workers"] = value
        elif key.startswith("APP_"):
            layer[key[4:].lower()] = value
    return layer

def read_os_environment_layer() -> dict[str, Any]:
    layer: dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            layer[key[4:].lower()] = value
    return layer

def effective_config(overrides: list[str] | None = None) -> dict[str, Any]:
    config = dict(DEFAULTS)
    apply_layer(config, read_yaml())
    apply_layer(config, read_dotenv_layer())
    apply_layer(config, read_os_environment_layer())

    # Each query parameter is expected as set=key=value. Multiple `set`
    # parameters are supported, and they override every earlier layer.
    for item in overrides or []:
        if "=" not in item:
            raise ValueError("Each set parameter must use key=value, e.g. set=port=9000")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if not key:
            raise ValueError("Override key cannot be empty")
        config[key] = coerce_value(key, value)

    # The real secret must never be returned.
    if "api_key" in config:
        config["api_key"] = "*****"
    return config

app = FastAPI(title="TDS Effective Configuration Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "TDS config service is running", "endpoint": "/effective-config"}

@app.get("/effective-config")
async def get_effective_config(request: Request):
    overrides = request.query_params.getlist("set")
    try:
        return JSONResponse(content=effective_config(overrides))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

if __name__ == "__main__":
    import uvicorn
    # Hosting platforms usually provide PORT. This is the web-server port,
    # separate from the app's effective configuration value named `port`.
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
