local TraceEnricher = {
  VERSION = "0.1.0",
  PRIORITY = 100,
}

local function truncate(value, max_len)
  if value == nil then
    return nil
  end

  local str = tostring(value)
  if max_len <= 0 or #str <= max_len then
    return str
  end

  return string.sub(str, 1, max_len) .. "...(truncated)"
end

local function set_attributes(span, attributes)
  if not span then
    return
  end

  for key, value in pairs(attributes) do
    if value ~= nil and value ~= "" then
      span:set_attribute(key, tostring(value))
    end
  end
end

local function enrich_mcp(attributes, ai, conf)
  local mcp = ai["mcp"] or {}
  local rpc_entries = mcp["rpc"] or {}
  local mcp_entry = rpc_entries[1] or {}
  local mcp_payload = mcp_entry["payload"] or {}

  if next(mcp) == nil and next(mcp_entry) == nil then
    return
  end

  attributes["mcp.session_id"] = mcp["mcp_session_id"]
  attributes["mcp.request.id"] = mcp_entry["id"]
  attributes["mcp.method"] = mcp_entry["method"]
  attributes["mcp.tool_name"] = mcp_entry["tool_name"]
  attributes["mcp.error"] = mcp_entry["error"]
  attributes["mcp.latency_ms"] = mcp_entry["latency"]
  attributes["mcp.response_body_size"] = mcp_entry["response_body_size"]

  if conf.include_payloads then
    attributes["mcp.request.payload"] = truncate(mcp_payload["request"], conf.payload_max_len)
    attributes["mcp.response.payload"] = truncate(mcp_payload["response"], conf.payload_max_len)
  end

  return true
end

local function enrich_a2a(attributes, ai, conf)
  local a2a = ai["a2a"] or {}
  local rpc_entries = a2a["rpc"] or {}
  local a2a_entry = rpc_entries[1] or {}
  local a2a_payload = a2a_entry["payload"] or {}

  if next(a2a) == nil and next(a2a_entry) == nil then
    return
  end

  attributes["a2a.method"] = a2a_entry["method"]
  attributes["a2a.request.id"] = a2a_entry["id"]
  attributes["a2a.error"] = a2a_entry["error"]
  attributes["a2a.latency_ms"] = a2a_entry["latency"]
  attributes["a2a.response_body_size"] = a2a_entry["response_body_size"]

  if conf.include_payloads then
    attributes["a2a.request.payload"] = truncate(a2a_payload["request"], conf.payload_max_len)
    attributes["a2a.response.payload"] = truncate(a2a_payload["response"], conf.payload_max_len)
  end

  return true
end

function TraceEnricher:log(conf)
  local log_payload = kong.log.serialize() or {}
  local request = log_payload["request"] or {}
  local request_headers = request["headers"] or {}
  local ai = log_payload["ai"] or {}

  local attributes = {
    ["demo.run_id"] = request_headers["x-demo-run-id"] or request_headers["X-Demo-Run-Id"],
    ["demo.context_id"] = request_headers["x-demo-context-id"] or request_headers["X-Demo-Context-Id"],
    ["a2a.task_id"] = request_headers["x-demo-task-id"] or request_headers["X-Demo-Task-Id"],
    ["a2a.message_id"] = request_headers["x-demo-message-id"] or request_headers["X-Demo-Message-Id"],
  }

  local has_mcp = enrich_mcp(attributes, ai, conf)
  local has_a2a = enrich_a2a(attributes, ai, conf)

  if not has_mcp and not has_a2a then
    return
  end

  local root_span = kong.tracing.get_root_span and kong.tracing.get_root_span() or nil
  set_attributes(root_span, attributes)
  set_attributes(kong.tracing.active_span(), attributes)
end

return TraceEnricher
