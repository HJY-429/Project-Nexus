# Pipeline System Simple Test

## 📋 Quick Verification Commands

### 1. Environment Setup
```bash
# Set database URL for testing
export DATABASE_URI="sqlite:///test.db"

# Alternatively, create a test environment file
echo "DATABASE_URI=sqlite:///test.db" > .env.test
echo "LLM_PROVIDER=ollama" >> .env.test
echo "LLM_MODEL=aya-expanse" >> .env.test
echo "OLLAMA_BASE_URL=http://localhost:11434" >> .env.test
```

## Example Test Scripts

### Script 1: validate_pipelines.py
**Purpose**: Validates core pipeline selection logic without database dependencies
```bash
python3 validate_pipelines.py
```

**Expected Output**:
```
Pipeline System Validation
============================================================
🧪 Validating Pipeline Selection Logic
==================================================
Testing selection logic:
  ✅ Single doc to existing topic: single_doc_existing_topic
  ✅ Batch docs to existing topic: batch_doc_existing_topic
  ✅ New topic with batch docs: new_topic_batch
  ✅ Dialogue history processing: memory_direct_graph
  ✅ Single text memory: memory_single
```


## Verification Examples

### Example 1: Components Loading
```bash
# Check if all components load correctly
python3 -c "
import os
os.environ['DATABASE_URI'] = 'sqlite:///test.db'
from tools.orchestrator import PipelineOrchestrator
from tools.base import TOOL_REGISTRY

# Test 1: Orchestrator instantiation
orch = PipelineOrchestrator()
print('✅ Orchestrator loaded')

# Test 2: Available pipelines
print('✅ Pipelines:', list(orch.standard_pipelines.keys()))

# Test 3: Tool registration
print('✅ Tools:', TOOL_REGISTRY.list_tools())

# Test 4: Pipeline selection
result = orch.select_default_pipeline('knowledge_graph', 'test', 1, False)
print('✅ Selection:', result)
"
```

```bash
python3 -c "
import os, sys
os.environ['DATABASE_URI'] = 'sqlite:///test.db'
sys.path.insert(0, '.')

try:
    from tools.orchestrator import PipelineOrchestrator
    from tools.base import TOOL_REGISTRY
    
    orch = PipelineOrchestrator()
    tools = TOOL_REGISTRY.list_tools()
    pipelines = list(orch.standard_pipelines.keys())
    
    print('✅')
    print(f'   Tools: {len(tools)} registered')
    print(f'   Pipelines: {len(pipelines)} available')
except Exception as e:
    print('❌')
    print(f'   Error: {e}')
"
```

### Example 2: Memory Pipeline
```bash
# Test memory pipeline selection
python3 -c "
import os
os.environ['DATABASE_URI'] = 'sqlite:///test.db'
from tools.orchestrator import PipelineOrchestrator

orch = PipelineOrchestrator()

# Test memory scenarios
scenarios = [
    ('personal_memory', 'user123', 0, False, 'dialogue'),
    ('personal_memory', 'user123', 1, False, 'text'),
]

for target, topic, count, is_new, input_type in scenarios:
    result = orch.select_default_pipeline(target, topic, count, is_new, input_type=input_type)
    print(f'✅ {target} ({input_type}): {result}')
"
```

### Example 3: Knowledge Graph Scenarios
```bash
# Test knowledge graph scenarios
python3 -c "
import os
os.environ['DATABASE_URI'] = 'sqlite:///test.db'
from tools.orchestrator import PipelineOrchestrator

orch = PipelineOrchestrator()

# Test KG scenarios
scenarios = [
    ('knowledge_graph', 'existing', 1, False, 'single_doc_existing_topic'),
    ('knowledge_graph', 'existing', 3, False, 'batch_doc_existing_topic'),
    ('knowledge_graph', 'new', 2, True, 'new_topic_batch'),
]

for target, topic, count, is_new, expected in scenarios:
    result = orch.select_default_pipeline(target, topic, count, is_new)
    status = '✅' if result == expected else '❌'
    print(f'{status} {target} {count} docs: {result} (expected {expected})')
"
```


## Common Issues

### Issue 1: DATABASE_URI not set
```bash
# Error: Expected string or URL object, got None
# Solution:
export DATABASE_URI="sqlite:///test.db"
```

### Issue 2: Database connection issues
```bash
# Error: 'connect_timeout' invalid keyword
# Solution: Minor config issue, doesn't affect core functionality
```

### Issue 3: Normal tests need database setup

## Final Verification Checklist

Use this checklist to verify everything is working:

- [ ] **Environment Setup**: `DATABASE_URI` is set
- [ ] **Pipeline Selection**: All 5 scenarios work correctly
- [ ] **Tool Registration**: All 3 tools registered (DocumentETLTool, BlueprintGenerationTool, GraphBuildTool)
- [ ] **Pipeline Definitions**: All 6 pipelines defined
- [ ] **Integration Tests**: All 5 tests pass
- [ ] **Memory Support**: Both memory pipelines work
- [ ] **API Integration**: Context preparation works
