from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DECK_FILE = REPO_ROOT / "kong" / "deck" / "kong.yaml"


def _value_after_colon(text: str) -> str:
    _, _, value = text.partition(":")
    return value.strip().strip('"').strip("'")


@lru_cache(maxsize=1)
def load_kong_gateway_inventory() -> dict[str, Any]:
    lines = DECK_FILE.read_text().splitlines()
    inventory: dict[str, Any] = {
        "global_plugins": [],
        "services": [],
        "consumers": [],
        "consumer_groups": [],
    }

    section: str | None = None
    service_mode: str | None = None
    route_mode: str | None = None
    consumer_mode: str | None = None
    consumer_plugin_mode: str | None = None
    mcp_mode: str | None = None
    acl_mode: str | None = None

    current_service: dict[str, Any] | None = None
    current_route: dict[str, Any] | None = None
    current_plugin: dict[str, Any] | None = None
    current_consumer: dict[str, Any] | None = None
    current_consumer_plugin: dict[str, Any] | None = None
    current_tool: dict[str, Any] | None = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if indent == 0 and stripped in {"plugins:", "services:", "consumers:", "consumer_groups:"}:
            section = stripped[:-1]
            service_mode = None
            route_mode = None
            consumer_mode = None
            mcp_mode = None
            acl_mode = None
            current_service = None
            current_route = None
            current_plugin = None
            current_consumer = None
            current_consumer_plugin = None
            current_tool = None
            continue

        if section == "plugins":
            if indent == 2 and stripped.startswith("- name:"):
                inventory["global_plugins"].append(_value_after_colon(stripped))
            continue

        if section == "services":
            if indent == 2 and stripped.startswith("- name:"):
                current_service = {
                    "name": _value_after_colon(stripped),
                    "url": "",
                    "plugins": [],
                    "routes": [],
                }
                inventory["services"].append(current_service)
                current_route = None
                current_plugin = None
                current_tool = None
                service_mode = None
                route_mode = None
                mcp_mode = None
                acl_mode = None
                continue

            if current_service is None:
                continue

            if indent == 4 and stripped.startswith("url:"):
                current_service["url"] = _value_after_colon(stripped)
                continue

            if indent == 4 and stripped == "routes:":
                service_mode = "routes"
                current_route = None
                current_plugin = None
                current_tool = None
                route_mode = None
                mcp_mode = None
                acl_mode = None
                continue

            if indent == 4 and stripped == "plugins:":
                service_mode = "plugins"
                current_route = None
                current_plugin = None
                current_tool = None
                route_mode = None
                mcp_mode = None
                acl_mode = None
                continue

            if service_mode == "plugins" and indent == 6 and stripped.startswith("- name:"):
                current_service["plugins"].append({"name": _value_after_colon(stripped)})
                continue

            if service_mode == "routes" and indent == 6 and stripped.startswith("- name:"):
                current_route = {
                    "name": _value_after_colon(stripped),
                    "paths": [],
                    "plugins": [],
                    "mcp_tools": [],
                }
                current_service["routes"].append(current_route)
                current_plugin = None
                current_tool = None
                route_mode = None
                mcp_mode = None
                acl_mode = None
                continue

            if current_route is None:
                continue

            if indent == 8 and stripped == "paths:":
                route_mode = "paths"
                continue

            if indent == 8 and stripped == "plugins:":
                route_mode = "plugins"
                current_plugin = None
                current_tool = None
                mcp_mode = None
                acl_mode = None
                continue

            if route_mode == "paths" and indent == 10 and stripped.startswith("- "):
                current_route["paths"].append(stripped[2:].strip())
                continue

            if route_mode == "plugins" and indent == 10 and stripped.startswith("- name:"):
                current_plugin = {"name": _value_after_colon(stripped)}
                current_route["plugins"].append(current_plugin)
                current_tool = None
                mcp_mode = None
                acl_mode = None
                continue

            if current_plugin is None or current_plugin.get("name") != "ai-mcp-proxy":
                continue

            if indent == 16 and stripped == "tools:":
                mcp_mode = "tools"
                current_tool = None
                acl_mode = None
                continue

            if mcp_mode == "tools" and indent == 18 and stripped.startswith("- name:"):
                current_tool = {
                    "name": _value_after_colon(stripped),
                    "method": "",
                    "path": "",
                    "allowed_groups": [],
                }
                current_route["mcp_tools"].append(current_tool)
                acl_mode = None
                continue

            if current_tool is None:
                continue

            if indent == 20 and stripped.startswith("method:"):
                current_tool["method"] = _value_after_colon(stripped)
                continue

            if indent == 20 and stripped.startswith("path:"):
                current_tool["path"] = _value_after_colon(stripped)
                continue

            if indent == 22 and stripped == "allow:":
                acl_mode = "allow"
                continue

            if acl_mode == "allow" and indent == 24 and stripped.startswith("- "):
                current_tool["allowed_groups"].append(stripped[2:].strip())
                continue

        if section == "consumers":
            if indent == 2 and stripped.startswith("- username:"):
                current_consumer = {
                    "username": _value_after_colon(stripped),
                    "groups": [],
                    "plugins": [],
                }
                inventory["consumers"].append(current_consumer)
                consumer_mode = None
                consumer_plugin_mode = None
                current_consumer_plugin = None
                continue

            if current_consumer is None:
                continue

            if indent == 4 and stripped == "groups:":
                consumer_mode = "groups"
                consumer_plugin_mode = None
                current_consumer_plugin = None
                continue

            if indent == 4 and stripped == "plugins:":
                consumer_mode = "plugins"
                consumer_plugin_mode = None
                current_consumer_plugin = None
                continue

            if consumer_mode == "groups" and indent == 6 and stripped.startswith("- name:"):
                current_consumer["groups"].append(_value_after_colon(stripped))
                continue

            if consumer_mode == "plugins" and indent == 6 and stripped.startswith("- name:"):
                current_consumer_plugin = {"name": _value_after_colon(stripped)}
                current_consumer["plugins"].append(current_consumer_plugin)
                consumer_plugin_mode = None
                continue

            if current_consumer_plugin is None:
                continue

            if indent == 8 and stripped == "config:":
                consumer_plugin_mode = "config"
                continue

            if consumer_plugin_mode != "config":
                continue

            if current_consumer_plugin.get("name") == "ai-rate-limiting-advanced":
                if indent == 10 and stripped.startswith("tokens_count_strategy:"):
                    current_consumer_plugin["tokens_count_strategy"] = _value_after_colon(stripped)
                    continue

                if indent == 10 and stripped == "llm_providers:":
                    current_consumer_plugin["llm_providers"] = []
                    continue

                if indent == 12 and stripped.startswith("- name:"):
                    current_consumer_plugin.setdefault("llm_providers", []).append(
                        {
                            "name": _value_after_colon(stripped),
                            "limit": [],
                            "window_size": [],
                        }
                    )
                    continue

                llm_providers = current_consumer_plugin.get("llm_providers") or []
                if not llm_providers:
                    continue

                current_provider = llm_providers[-1]
                if indent == 14 and stripped == "limit:":
                    current_provider["_reading"] = "limit"
                    continue
                if indent == 14 and stripped == "window_size:":
                    current_provider["_reading"] = "window_size"
                    continue
                if indent == 16 and stripped.startswith("- "):
                    reading = current_provider.get("_reading")
                    if reading in {"limit", "window_size"}:
                        current_provider[reading].append(stripped[2:].strip())
                    continue

        if section == "consumer_groups":
            if indent == 2 and stripped.startswith("- name:"):
                inventory["consumer_groups"].append(_value_after_colon(stripped))

    return inventory


def find_route_object(
    inventory: dict[str, Any],
    *,
    route_name: str | None = None,
    path: str | None = None,
) -> dict[str, Any] | None:
    for service in inventory["services"]:
        for route in service["routes"]:
            if route_name and route["name"] == route_name:
                return build_route_object(inventory, service, route)
            if path and path in route["paths"]:
                return build_route_object(inventory, service, route)
    return None


def build_route_object(
    inventory: dict[str, Any],
    service: dict[str, Any],
    route: dict[str, Any],
) -> dict[str, Any]:
    effective_plugins = [
        {"name": plugin_name, "scope": "global"}
        for plugin_name in inventory["global_plugins"]
    ]
    effective_plugins.extend(
        {"name": plugin["name"], "scope": "service"}
        for plugin in service.get("plugins", [])
    )
    effective_plugins.extend(
        {"name": plugin["name"], "scope": "route"}
        for plugin in route.get("plugins", [])
    )
    return {
        "service_name": service["name"],
        "service_url": service.get("url", ""),
        "route_name": route["name"],
        "paths": route.get("paths", []),
        "service_plugins": [plugin["name"] for plugin in service.get("plugins", [])],
        "route_plugins": [plugin["name"] for plugin in route.get("plugins", [])],
        "effective_plugins": effective_plugins,
        "mcp_tools": route.get("mcp_tools", []),
    }


def consumer_objects(
    inventory: dict[str, Any],
    *,
    usernames: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected = set(usernames or [])
    consumers = []
    for consumer in inventory.get("consumers", []):
        if selected and consumer.get("username") not in selected:
            continue
        consumers.append(
            {
                "username": consumer.get("username"),
                "groups": consumer.get("groups", []),
                "plugins": consumer.get("plugins", []),
            }
        )
    return consumers
