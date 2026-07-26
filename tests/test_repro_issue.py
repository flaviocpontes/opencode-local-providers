from opencode_config.use_cases.helpers import model_to_entry
from opencode_config.domain.entities import Model

def test_model_to_entry_requires_output_limit():
    m = Model(id="GLM-4.7-Flash-GGUF", max_context_window=202752,
              labels=[], recipe="llamacpp")
    entry = model_to_entry(m)
    
    assert "limit" in entry, "Model entry should have 'limit' key"
    assert "output" in entry["limit"], "Model entry should have 'limit.output' key even for non-reasoning models"
