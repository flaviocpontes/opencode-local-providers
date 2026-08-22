# ollama-support Specification

## Purpose

Lets the tool sync models from Ollama inference servers alongside Lemonade servers, normalizing both into one `opencode.json` provider format.

## Requirements

### Requirement: Registry entries declare server type

The server registry SHALL accept a `type` field per server entry with values `lemonade` and `ollama`. Entries without a `type` SHALL be treated as `lemonade`, so existing registry files behave identically without migration. An `ollama` entry without an explicit `port` SHALL default to port 11434; a `lemonade` entry without a port SHALL default to 13305.

#### Scenario: Omitted type is lemonade

- **WHEN** a registry entry has no `type` field
- **THEN** the entry is synced as a Lemonade server with the same output as before this capability existed

#### Scenario: Per-type default port

- **WHEN** an `ollama` entry omits `port`
- **THEN** the tool connects to port 11434 for that entry

#### Scenario: Explicit port overrides default

- **WHEN** an `ollama` entry sets `port: 1234`
- **THEN** the tool connects to port 1234 for that entry

### Requirement: Ollama sync emits a provider entry with the v1 base URL

For each enabled `ollama` server, sync SHALL write a provider entry using `options.baseURL` of the form `http://<host>:<port>/v1`, with the same provider structure as Lemonade servers (npm package, name, models map). Server listing SHALL work for Ollama servers the same as for Lemonade servers.

#### Scenario: Provider entry for an Ollama server

- **WHEN** sync runs with an enabled `ollama` server at `192.168.0.30` with models present
- **THEN** `opencode.json` contains a provider entry whose `options.baseURL` is `http://192.168.0.30:11434/v1`
- **AND** the entry's models map contains the server's chat models

#### Scenario: Mixed registry

- **WHEN** the registry contains one `lemonade` and one `ollama` server, both reachable
- **THEN** sync writes one provider entry per server and exits 0

### Requirement: Only chat models are included

Sync SHALL include an Ollama model only when the model reports chat-completion capability. Models that lack it (e.g. embedding-only models) SHALL be excluded regardless of `--show-all`. Models whose capabilities cannot be determined SHALL be included.

#### Scenario: Embedding model excluded

- **WHEN** an Ollama model's capabilities do not include completion
- **THEN** it does not appear in the generated provider entry

#### Scenario: Unknown capabilities included conservatively

- **WHEN** capability information is unavailable for a model
- **THEN** the model is included in the generated provider entry

### Requirement: Model details are mapped to opencode fields

Sync SHALL map Ollama model details onto the same opencode model fields used for Lemonade: vision capability to image input modalities; thinking/reasoning capability to the raised output limit; the model's context length to `limit.context` when known. The display name SHALL be the model id with a trailing `:latest` tag stripped.

#### Scenario: Vision model gets modalities

- **WHEN** a synced Ollama model reports vision capability
- **THEN** its opencode model entry declares image input modality

#### Scenario: Context length mapped

- **WHEN** a synced Ollama model reports a context length
- **THEN** its opencode model entry sets `limit.context` to that value

#### Scenario: Latest tag stripped from display name

- **WHEN** a model is named `gemma4:latest`
- **THEN** its opencode model entry's `name` is `gemma4`
- **AND** the model key under `models` remains the full id `gemma4:latest`

### Requirement: Per-model detail failures degrade gracefully

If fetching details for an individual model fails while the model listing succeeded, sync SHALL still include that model (without context/vision enrichment) rather than dropping it or failing the server, and other models' enrichment SHALL be unaffected.

#### Scenario: Detail fetch fails for one model

- **WHEN** the model list succeeds but detail lookup fails for one model
- **THEN** that model appears in the provider entry without `limit.context`
- **AND** remaining models are fully enriched
- **AND** the sync does not report the server as failed

### Requirement: Below-64k context models trigger a warning

opencode requires 64k+ context. When a synced Ollama model has a known context length below 65536, sync SHALL print a warning naming the model and its context length. The model SHALL still be included in the output. Models with unknown context length SHALL NOT trigger the warning.

#### Scenario: Small context warned

- **WHEN** a synced model reports context length 8192
- **THEN** a warning naming the model and 8192 is printed
- **AND** the model still appears in the provider entry

#### Scenario: Unknown context not warned

- **WHEN** a model's context length cannot be determined
- **THEN** no context warning is printed for it
