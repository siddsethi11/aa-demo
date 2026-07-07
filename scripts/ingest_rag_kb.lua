local embeddings = require("kong.llm.embeddings")
local uuid = require("kong.tools.utils").uuid
local vectordb = require("kong.llm.vectordb")

local function read_file(path)
  local file, err = io.open(path, "r")
  if not file then
    return nil, "Failed to open content file: " .. tostring(err)
  end

  local content = file:read("*a")
  file:close()

  if not content or content == "" then
    return nil, "Content file is empty"
  end

  return content
end

local function get_plugin_by_id(id)
  local row, err = kong.db.plugins:select(
    { id = id },
    { workspace = ngx.null, show_ws_id = true, expand_partials = true }
  )

  if err then
    return nil, err
  end

  return row
end

local function ingest_chunk(conf, content)
  local metadata = {
    ingest_duration = ngx.now(),
    chunk_id = uuid(),
  }

  local vectordb_driver, err = vectordb.new(
    conf.vectordb.strategy,
    conf.vectordb_namespace,
    conf.vectordb,
    true
  )
  if err then
    return nil, "Failed to load vector database driver: " .. err
  end

  local embeddings_driver, err = embeddings.new(conf.embeddings, conf.vectordb.dimensions)
  if err then
    return nil, "Failed to instantiate embeddings driver: " .. err
  end

  local embeddings_vector, embeddings_tokens_count, err = embeddings_driver:generate(content)
  if err then
    return nil, "Failed to generate embeddings: " .. err
  end

  metadata.embeddings_tokens_count = embeddings_tokens_count

  if #embeddings_vector ~= conf.vectordb.dimensions then
    return nil, "Embedding dimensions do not match configured vector dimensions"
  end

  local _, insert_err = vectordb_driver:insert(embeddings_vector, content, metadata.chunk_id)
  if insert_err then
    return nil, "Failed to insert chunk: " .. insert_err
  end

  ngx.log(ngx.INFO, "Ingested chunk " .. metadata.chunk_id)
  return metadata
end

assert(#args == 3, "Expected plugin_id and content_file_path")

local plugin_id = args[2]
local content_file_path = args[3]

local plugin, err = get_plugin_by_id(plugin_id)
if err then
  ngx.log(ngx.ERR, "Failed to get plugin: " .. err)
  return
end

if not plugin then
  ngx.log(ngx.ERR, "Plugin not found")
  return
end

local content, read_err = read_file(content_file_path)
if read_err then
  ngx.log(ngx.ERR, read_err)
  return
end

local metadata, ingest_err = ingest_chunk(plugin.config, content)
if ingest_err then
  ngx.log(ngx.ERR, "Failed to ingest: " .. ingest_err)
  return
end

ngx.say(require("cjson").encode({ metadata = metadata }))
