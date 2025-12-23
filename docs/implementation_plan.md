# Forge Unified V5 - Implementation Plan

**Date:** 2025-12-23  
**Bundle:** `forge-unified-v5.tar.gz`  
**Target:** `sx9-dev-forge-rn-migration`  
**Status:** PLANNING

---

## Executive Summary

The forge-unified-v5 bundle provides a **production-grade QA system** and **enhanced agent harness** that will transform the current Prompt Forge from a UI prototype into a fully operational code factory. This implementation will close the remaining ~40% feature gap and add sophisticated quality gates.

### Impact Summary

| Component                     | Impact                                    | Complexity | Risk   |
| ----------------------------- | ----------------------------------------- | ---------- | ------ |
| **QA Gates**                  | HIGH - Adds 4-dimensional quality scoring | MEDIUM     | MEDIUM |
| **Agent Harness**             | HIGH - Adds Redux intelligence layer      | HIGH       | HIGH   |
| **Canonical Patterns**        | MEDIUM - Provides 6 reference patterns    | LOW        | LOW    |
| **Git/Linear/Slack Workflow** | HIGH - Automates entire pipeline          | HIGH       | MEDIUM |

**Overall Impact:** 🔴 **CRITICAL** - This is the missing production infrastructure  
**Implementation Time:** 2-3 weeks  
**Risk Level:** MEDIUM-HIGH (requires careful integration)

---

## Bundle Contents Analysis

### 1. Canonical Patterns (`forge/canonical/`)

**Purpose:** Reference implementations of 6 design patterns with strict constraints

**Files:**

- `validation/USER_VALIDATE_INPUT_SECURITY.rs` - Input validation pattern
- `persistence/SYSTEM_WRITE_IDEMPOTENT_RECORD.rs` - Idempotent write pattern
- `concurrency/WORKER_PROCESS_TASK_BOUNDED.rs` - Bounded concurrency pattern
- `security/SERVICE_ROTATE_TOKEN_SECURE.rs` - Token rotation pattern
- `lifecycle/RESOURCE_CLOSE_GRACEFUL.rs` - Graceful shutdown pattern
- `design/SERVICE_ADAPTER_IO_WRAPPER.rs` - Adapter pattern
- `manifest.json` - Pattern metadata and constraints

**Constraints Applied:**

```json
{
  "deterministic": true,
  "no_io": true,
  "no_logging": true,
  "no_config": true,
  "single_responsibility": true
}
```

**Integration Point:** These serve as templates for the pattern matching gate

---

### 2. QA Gates (`forge/gates/`)

**Purpose:** 4-dimensional quality analysis system

#### Gate 1: Static Analysis (`static_gate.py`)

- **Analyzes:** Code structure + complexity
- **Outputs:** `static.findings.json`
- **Metrics:** Halstead, Cyclomatic Complexity, Maintainability Index
- **Weight:** 50% (25% structure + 25% complexity)

#### Gate 2: Architecture Compliance (`arch_gate.py`)

- **Analyzes:** ECS layer compliance, forbidden dependencies
- **Outputs:** `arch.findings.json`
- **Checks:**
  - `bevy_free` (auto-fail if false)
  - `ecs_layer` (must be "legion" or "apecs")
  - TCR compliance
- **Weight:** 25%

#### Gate 3: Pattern Matching (`pattern_gate.py`)

- **Analyzes:** Alignment with canonical patterns
- **Outputs:** `pattern.matches.json`
- **Uses:** Vector embeddings + N-V-N-N structure matching
- **Weight:** 25%

#### Gate 4: Aggregator (`aggregator.py`)

- **Combines:** All gate outputs
- **Outputs:** `qa.report.json` with final grade (A-F)
- **Pass Threshold:** Grade B (70/100) minimum
- **Auto-Fail:** Bevy imports detected

**Grading Scale:**

```python
A: 85+ (Production ready)
B: 70-84 (Acceptable, minor issues)
C: 55-69 (Needs refactoring)
D: 40-54 (Major issues)
F: <40 (Rejected)
```

---

### 3. Agent Harness (`forge/harness/`)

**Purpose:** Redux-based intelligence layer for background queries

**TypeScript Modules:**

1. `types.ts` - Type definitions for intelligence state
2. `actions.ts` - Redux actions for queries
3. `reducer.ts` - State management logic
4. `selectors.ts` - State selectors
5. `middleware.ts` - Async query middleware
6. `validators.ts` - Input validation
7. `executor.ts` - Query execution engine
8. `graphActions.ts` - GLAF graph operations
9. `graphCRUD.ts` - Graph CRUD operations

**Intelligence Queries:**

- **Pattern Suggestions:** ChromaDB vector search for similar crate interviews
- **Tool Recommendations:** Kali tool ranking by relevance
- **Threat Scenarios:** MITRE ATT&CK context
- **EEI Answers:** Knowledge graph Q&A

**Connection Status:**

```typescript
type ConnectionStatus =
  | "offline"
  | "connecting"
  | "ready"
  | "querying"
  | "error";
```

---

### 4. Agent Prompts (`forge/agents/`)

**Primary Agent:**

- `CANONICAL_DISCOVERY_AGENT.prompt.yml` - Discovers pattern instances in legacy code

**Sub-Agents:**

- `CONSTRAINT_VALIDATION_AGENT.prompt.yml` - Validates constraint compliance
- `STATIC_SHAPE_AGENT.prompt.yml` - Analyzes code structure
- `GLAF_ANNOTATION_AGENT.prompt.yml` - Generates graph annotations
- `SEMANTIC_INTENT_AGENT.prompt.yml` - Extracts semantic intent

**All agents:**

- Temperature: 0.0 (deterministic)
- Output: JSON only
- No code modifications
- Schema-validated outputs

---

### 5. Git/Linear/Slack Workflow (`forge/integrations/`)

**RFC-9122 Specification:**

**Branch Strategy:**

- `main` - Production registry source
- `develop` - Integration branch
- `feature/*` - Human development
- `factory/*` - Agent development (isolated)
- `hotfix/*` - Emergency fixes
- `experiment/*` - R&D (never merges)

**Linear States:**

```
Backlog → Ready → Building → Review → Done
                      ↓
                   Blocked
```

**Slack Channels:**

- `#sx9-factory` - Build status
- `#sx9-review` - PR reviews
- `#sx9-decisions` - Human approval gates
- `#sx9-alerts` - Failures/blocks
- `#sx9-releases` - Production releases

**PR Workflow:**

1. Validate branch naming
2. Build + test
3. Birth certificate validation
4. Lightning QA (Grade A required)
5. Security scan
6. Decision gate (auto-merge vs human review)
7. Slack notification
8. Merge or rework

---

## Critical Failure Points & Mitigation

### 🔴 Failure Point 1: QA Gate Integration Mismatch

**Risk:** The Python QA gates expect specific file structures and outputs that may not match current implementation

**Symptoms:**

- Gates fail to find input files
- JSON schema validation errors
- Incorrect score calculations
- Missing refactor directives

**Root Causes:**

1. Current `PromptForgeScreen` doesn't generate required intermediate files
2. File paths hardcoded in Python scripts don't match Next.js structure
3. Schema versions may be incompatible

**Mitigation Strategy:**

```typescript
// 1. Create QA bridge API endpoint
// app/api/qa/run/route.ts

export async function POST(req: Request) {
  const { cratePath } = await req.json();

  // Prepare workspace
  const tempDir = `/tmp/qa-${Date.now()}`;
  await fs.mkdir(tempDir, { recursive: true });

  // Run gates in sequence
  const staticResult = await runCommand(
    `python3 forge/gates/static_gate.py ${cratePath} ${tempDir}/static.json`
  );

  const archResult = await runCommand(
    `python3 forge/gates/arch_gate.py ${cratePath} ${tempDir}/arch.json`
  );

  const patternResult = await runCommand(
    `python3 forge/gates/pattern_gate.py ${cratePath} ${tempDir}/pattern.json`
  );

  // Aggregate
  const qaReport = await runCommand(
    `python3 forge/gates/aggregator.py ${tempDir}/static.json ${tempDir}/arch.json ${tempDir}/pattern.json ${tempDir}/qa.report.json ${crateName}`
  );

  return NextResponse.json(qaReport);
}
```

**Validation:**

- Test with known-good crate
- Verify all 4 gates produce valid JSON
- Confirm grade calculation matches expected values

---

### 🔴 Failure Point 2: Redux Harness State Collision

**Risk:** The new Redux intelligence layer may conflict with existing state management

**Symptoms:**

- State updates don't trigger re-renders
- Query results disappear
- Connection status stuck in "connecting"
- Type errors in selectors

**Root Causes:**

1. Existing `src/store/` structure may have naming conflicts
2. Middleware order matters for async queries
3. Selector memoization issues with new state shape

**Mitigation Strategy:**

```typescript
// 1. Namespace the intelligence slice
// src/store/index.ts

import { configureStore } from "@reduxjs/toolkit";
import intelligenceReducer from "./intelligence/reducer";
import { intelligenceMiddleware } from "./intelligence/middleware";

export const store = configureStore({
  reducer: {
    // Existing reducers
    intelligence: intelligenceReducer, // NEW - namespaced
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(intelligenceMiddleware), // Add AFTER defaults
});

// 2. Update selectors to use namespace
// src/store/intelligence/selectors.ts

export const selectLeptoseStatus = (state: RootState) =>
  state.intelligence.leptose.status; // Note: intelligence.leptose

export const selectPatternSuggestions = (state: RootState) =>
  state.intelligence.patterns.results;
```

**Validation:**

- Redux DevTools shows correct state shape
- Queries trigger status changes
- Results populate UI panels
- No console errors

---

### 🔴 Failure Point 3: Agent Prompt Execution Environment

**Risk:** Agent prompts expect specific execution environment that may not exist

**Symptoms:**

- Agents can't find canonical registry
- Schema validation fails
- Output files not created
- Determinism violated (temperature != 0.0)

**Root Causes:**

1. Prompts reference paths that don't exist in Next.js app
2. LLM API may not respect temperature=0.0
3. JSON schema files not accessible to agents

**Mitigation Strategy:**

```typescript
// 1. Create agent execution wrapper
// src/lib/agents/executor.ts

import { readFile } from "fs/promises";
import yaml from "yaml";

export async function executeAgent(
  agentPath: string,
  inputs: Record<string, string>
) {
  // Load prompt YAML
  const promptYaml = await readFile(agentPath, "utf-8");
  const prompt = yaml.parse(promptYaml);

  // Validate inputs match expected
  const requiredInputs = prompt.io.inputs;
  for (const input of requiredInputs) {
    if (!inputs[input]) {
      throw new Error(`Missing required input: ${input}`);
    }
  }

  // Enforce determinism
  const temperature = prompt.constraints.determinism.temperature;
  if (temperature !== 0.0) {
    console.warn(`Agent ${agentPath} has non-zero temperature`);
  }

  // Execute with LLM
  const response = await callLLM({
    model: "claude-sonnet-4.5",
    temperature: 0.0, // FORCE determinism
    messages: [
      {
        role: "user",
        content: buildPromptFromYAML(prompt, inputs),
      },
    ],
  });

  // Validate output against schema
  const outputSchema = await loadSchema(prompt.io.outputs[0]);
  const valid = validateJSON(response, outputSchema);

  if (!valid) {
    throw new Error("Agent output failed schema validation");
  }

  return response;
}
```

**Validation:**

- Agent produces valid JSON
- Temperature is exactly 0.0
- No code modifications occur
- Outputs match schema

---

### 🔴 Failure Point 4: Linear/Slack Webhook Integration

**Risk:** Webhook receivers may not handle all event types correctly

**Symptoms:**

- Linear state changes don't trigger Slack notifications
- PR creation doesn't move issue to "Review"
- Decision reactions don't approve PRs
- Webhook signature validation fails

**Root Causes:**

1. Linear webhook secret not configured
2. Slack reaction events not subscribed
3. GitHub webhook payload structure changed
4. Race conditions in state transitions

**Mitigation Strategy:**

```typescript
// 1. Add webhook signature validation
// app/api/webhooks/linear/route.ts

import crypto from "crypto";

export async function POST(req: Request) {
  const signature = req.headers.get("linear-signature");
  const body = await req.text();

  // Validate signature
  const secret = process.env.LINEAR_WEBHOOK_SECRET;
  if (!secret) {
    console.error("LINEAR_WEBHOOK_SECRET not configured");
    return new Response("Webhook secret not configured", { status: 500 });
  }

  const expectedSignature = crypto
    .createHmac("sha256", secret)
    .update(body)
    .digest("hex");

  if (signature !== expectedSignature) {
    console.error("Invalid webhook signature");
    return new Response("Invalid signature", { status: 401 });
  }

  const event = JSON.parse(body);

  // Handle event types
  switch (event.type) {
    case "Issue":
      await handleIssueEvent(event);
      break;
    case "IssueComment":
      await handleCommentEvent(event);
      break;
    default:
      console.warn(`Unknown event type: ${event.type}`);
  }

  return new Response("OK", { status: 200 });
}

// 2. Add idempotency to prevent duplicate actions
const processedEvents = new Set<string>();

async function handleIssueEvent(event: any) {
  const eventId = event.data.id + event.updatedAt;

  if (processedEvents.has(eventId)) {
    console.log(`Skipping duplicate event: ${eventId}`);
    return;
  }

  processedEvents.add(eventId);

  // Process event...
}
```

**Validation:**

- Webhook signature validates correctly
- All event types handled
- No duplicate notifications
- State transitions are atomic

---

## Implementation Plan

### Phase 1: QA Gates Integration (Week 1)

#### Step 1.1: Copy QA Gates

```bash
# Copy Python gates to Next.js public directory
mkdir -p public/forge/gates
cp -r forge-unified-v5-extracted/forge/gates/* public/forge/gates/

# Copy canonical patterns
mkdir -p public/forge/canonical
cp -r forge-unified-v5-extracted/forge/canonical/* public/forge/canonical/

# Copy schemas
mkdir -p public/forge/schemas
cp -r forge-unified-v5-extracted/forge/schemas/* public/forge/schemas/
```

#### Step 1.2: Create QA API Endpoint

```typescript
// app/api/qa/run/route.ts
// Implement as shown in Failure Point 1 mitigation
```

#### Step 1.3: Add QA Results Display

```typescript
// src/components/QAResultsPanel.tsx
export const QAResultsPanel: React.FC<{ report: QAReport }> = ({ report }) => {
  return (
    <div className="qa-results">
      <div className="grade-badge grade-{report.grade}">
        Grade: {report.grade}
      </div>
      <div className="score">{report.score}/100</div>

      <div className="dimensions">
        {Object.entries(report.dimensions).map(([name, dim]) => (
          <div key={name} className="dimension">
            <span>{name}</span>
            <div className="score-bar" style={{ width: `${dim.score}%` }} />
            <span>{dim.score}/100</span>
          </div>
        ))}
      </div>

      {report.refactor_directives.length > 0 && (
        <div className="directives">
          <h4>Refactor Directives:</h4>
          <ul>
            {report.refactor_directives.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
```

#### Step 1.4: Wire to Generate Button

```typescript
// src/screens/PromptForgeScreen.tsx
const generate = async () => {
  // ... existing generation logic ...

  // Run QA gates
  const qaResponse = await fetch("/api/qa/run", {
    method: "POST",
    body: JSON.stringify({ cratePath: generatedCratePath }),
  });

  const qaReport = await qaResponse.json();

  if (qaReport.grade === "F") {
    setFeedback(`QA FAILED: ${qaReport.refactor_directives[0]}`);
    return;
  }

  setFeedback(`QA PASSED: Grade ${qaReport.grade} (${qaReport.score}/100)`);
};
```

---

### Phase 2: Redux Intelligence Layer (Week 1-2)

#### Step 2.1: Copy Harness Modules

```bash
mkdir -p src/store/intelligence
cp forge-unified-v5-extracted/forge/harness/* src/store/intelligence/
```

#### Step 2.2: Update Store Configuration

```typescript
// src/store/index.ts
import { configureStore } from "@reduxjs/toolkit";
import intelligenceReducer from "./intelligence/reducer";
import { intelligenceMiddleware } from "./intelligence/middleware";

export const store = configureStore({
  reducer: {
    intelligence: intelligenceReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(intelligenceMiddleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

#### Step 2.3: Connect Intelligence Panels

```typescript
// src/screens/PromptForgeScreen.tsx - RightContent component
const RightContent: React.FC<{ tab: string }> = ({ tab }) => {
  const dispatch = useDispatch();
  const patterns = useSelector(selectPatternSuggestions);
  const tools = useSelector(selectToolRecommendations);
  const threats = useSelector(selectThreatScenarios);

  const objective = useSelector((state) => state.objective); // From main form

  // Query on objective change
  useEffect(() => {
    if (objective && tab === "intel") {
      dispatch(queryPatterns({ text: objective, nResults: 5 }));
    }
    if (objective && tab === "tools") {
      dispatch(queryTools({ text: objective, nResults: 10 }));
    }
    if (objective && tab === "threats") {
      dispatch(queryThreats({ text: objective, nResults: 5 }));
    }
  }, [objective, tab, dispatch]);

  return (
    <div className="right-content">
      {tab === "intel" && (
        <div className="patterns">
          {patterns.loading && <Spinner />}
          {patterns.results.map((p) => (
            <PatternCard key={p.interview_id} pattern={p} />
          ))}
        </div>
      )}

      {tab === "tools" && (
        <div className="tools">
          {tools.results.map((t) => (
            <ToolCard key={t.tool_name} tool={t} />
          ))}
        </div>
      )}

      {tab === "threats" && (
        <div className="threats">
          {threats.results.map((t) => (
            <ThreatCard key={t.scenario_id} threat={t} />
          ))}
        </div>
      )}
    </div>
  );
};
```

#### Step 2.4: Create Mock Intelligence APIs

```typescript
// app/api/intelligence/patterns/route.ts
export async function POST(req: Request) {
  const { text, nResults } = await req.json();

  // TODO: Replace with actual ChromaDB query
  const mockPatterns: PatternSuggestion[] = [
    {
      interview_id: "uuid-1",
      pattern: "Reactor",
      similarity: 0.92,
      voice_narrative:
        "I am a network event handler that processes incoming connections...",
    },
    // ... more patterns
  ];

  return NextResponse.json(mockPatterns);
}
```

---

### Phase 3: Agent Prompts Integration (Week 2)

#### Step 3.1: Copy Agent Prompts

```bash
mkdir -p prompts/agents
cp -r forge-unified-v5-extracted/forge/agents/* prompts/agents/
```

#### Step 3.2: Create Agent Executor

```typescript
// src/lib/agents/executor.ts
// Implement as shown in Failure Point 3 mitigation
```

#### Step 3.3: Wire Discovery Agent to Generate

```typescript
// src/screens/PromptForgeScreen.tsx
const generate = async () => {
  // ... existing logic ...

  // Run canonical discovery agent
  const discoveryResult = await executeAgent(
    "prompts/agents/primary/CANONICAL_DISCOVERY_AGENT.prompt.yml",
    {
      repo_path: "/path/to/generated/crate",
      canonical_registry_path: "public/forge/canonical",
      static_outputs_path: "/tmp/static.json",
      semantic_outputs_path: "/tmp/semantic.json",
    }
  );

  // discoveryResult contains pattern.matches.json and graph.delta.json
  console.log("Discovered patterns:", discoveryResult);
};
```

---

### Phase 4: Git/Linear/Slack Workflow (Week 2-3)

#### Step 4.1: Add LINEAR_WEBHOOK_SECRET

```bash
# Update SX9_API_VAULT.json
{
  "linear": {
    "api_key": "...",
    "webhook_secret": "generate-random-secret-here"
  }
}

# Run setup script
./setup-api-keys-from-vault.sh
```

#### Step 4.2: Update Linear Webhook Receiver

```typescript
// app/api/webhooks/linear/route.ts
// Implement as shown in Failure Point 4 mitigation
```

#### Step 4.3: Add Slack Reaction Handler

```typescript
// app/api/webhooks/slack/route.ts
export async function POST(req: Request) {
  const event = await req.json();

  if (event.type === "url_verification") {
    return NextResponse.json({ challenge: event.challenge });
  }

  if (
    event.type === "event_callback" &&
    event.event.type === "reaction_added"
  ) {
    const { reaction, item } = event.event;

    if (reaction === "white_check_mark") {
      // Approve PR
      await approvePR(item.ts);
    } else if (reaction === "x") {
      // Request changes
      await requestChanges(item.ts);
    }
  }

  return new Response("OK", { status: 200 });
}
```

#### Step 4.4: Create PR Workflow Script

```bash
# forge/forge-pipeline.sh
#!/bin/bash
# Complete pipeline: Generate → QA → PR → Slack

set -e

ISSUE_ID=$1
CRATE_NAME=$2

echo "🔨 Starting factory build for $ISSUE_ID"

# 1. Generate crate (via Prompt Forge)
curl -X POST http://localhost:3001/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"issue_id\": \"$ISSUE_ID\", \"crate_name\": \"$CRATE_NAME\"}"

# 2. Run QA gates
python3 public/forge/gates/static_gate.py "crates/$CRATE_NAME" /tmp/static.json
python3 public/forge/gates/arch_gate.py "crates/$CRATE_NAME" /tmp/arch.json
python3 public/forge/gates/pattern_gate.py "crates/$CRATE_NAME" /tmp/pattern.json
python3 public/forge/gates/aggregator.py /tmp/static.json /tmp/arch.json /tmp/pattern.json /tmp/qa.json "$CRATE_NAME"

# 3. Check grade
GRADE=$(jq -r '.grade' /tmp/qa.json)
if [ "$GRADE" != "A" ]; then
  echo "❌ QA Failed: Grade $GRADE"
  exit 1
fi

# 4. Create branch and PR
git checkout -b "factory/$ISSUE_ID-$CRATE_NAME"
git add "crates/$CRATE_NAME"
git commit -m "feat: Add $CRATE_NAME (SX9-$ISSUE_ID)"
git push origin "factory/$ISSUE_ID-$CRATE_NAME"

gh pr create \
  --title "[$ISSUE_ID] Add $CRATE_NAME" \
  --body "Auto-generated by Factory Agent. QA Grade: $GRADE" \
  --base develop

echo "✅ PR created successfully"
```

---

## Verification Checklist

### QA Gates

- [ ] All 4 gates execute without errors
- [ ] Aggregator produces valid `qa.report.json`
- [ ] Grades match expected values for test crates
- [ ] Refactor directives are actionable
- [ ] Bevy imports trigger auto-fail

### Redux Intelligence

- [ ] Leptose connection status updates correctly
- [ ] ChromaDB connection status updates correctly
- [ ] Pattern queries return results
- [ ] Tool queries return results
- [ ] Threat queries return results
- [ ] Results populate UI panels
- [ ] No state collision with existing reducers

### Agent Prompts

- [ ] Discovery agent produces valid JSON
- [ ] Temperature is enforced at 0.0
- [ ] Schema validation passes
- [ ] No code modifications occur
- [ ] All sub-agents execute correctly

### Git/Linear/Slack

- [ ] Linear webhook signature validates
- [ ] Issue state transitions work
- [ ] Slack notifications sent correctly
- [ ] Reaction handlers approve/reject PRs
- [ ] PR workflow completes end-to-end
- [ ] No duplicate notifications

---

## Success Criteria

1. **QA Integration:** Generate button runs all 4 gates and displays grade
2. **Intelligence Panels:** Right sidebar shows actual pattern/tool/threat data
3. **Agent Execution:** Discovery agent finds canonical patterns in generated code
4. **Workflow Automation:** Complete pipeline from issue → branch → PR → merge works

**Timeline:** 2-3 weeks  
**Risk:** MEDIUM-HIGH  
**Confidence:** 75% (high complexity, multiple integration points)

---

## Next Steps

1. Review this plan with user
2. Address any concerns about failure points
3. Begin Phase 1 (QA Gates) implementation
4. Test each phase thoroughly before proceeding
5. Document any deviations from plan
