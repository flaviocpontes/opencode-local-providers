## ADDED Requirements

### Requirement: Unknown server type is a config error

When a registry entry declares a `type` value other than `lemonade` or `ollama`, the tool SHALL treat it as a config error: a single-line message naming the registry path and the offending entry, no output file written, exit code 2.

#### Scenario: Registry entry with unknown type

- **WHEN** a registry entry declares `"type": "vllm"` and any mode other than `--init-servers` runs
- **THEN** a single-line error names the registry path and the entry
- **AND** the exit code is 2 and no output file is written
