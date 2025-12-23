# SX9 Prompt Forge

**Status:** Active Development  
**Version:** 4.0  
**Stack:** React 19 + TypeScript + TailwindCSS v4 + Next.js

---

## Overview

SX9 Prompt Forge is a deterministic prompt engineering IDE that transforms natural language mission objectives into production-ready Rust crates. It implements RFC-9112 (Deterministic Prompt Engineering) and RFC-9116 (Dev Forge System Architecture).

### Key Features

- ✅ **Phase 1 & 2 UI Controls** - Harness mode, persona, inference parameters, Linear/Slack integration, context sources
- ✅ **Two-Glyph Rail System** - High-density IDE layout with collapsible sidebars
- ✅ **Intelligence Panels** - Pattern suggestions, tool recommendations, threat scenarios
- 🚧 **QA Gates** - 4-dimensional quality analysis (static/arch/pattern/aggregator)
- 🚧 **Agent Harness** - Redux-based background intelligence queries
- 🚧 **Git/Linear/Slack Workflow** - Automated PR creation and decision gates

---

## Repository Structure

```
sx9-forge/
├── src/                          # Current implementation (from sx9-dev-forge-rn-migration)
│   ├── screens/
│   │   └── PromptForgeScreen.tsx # Main UI with Phase 1 & 2 controls
│   └── store/
│       └── intelligence/         # Redux intelligence layer (to be integrated)
├── forge-unified-v5/             # Production QA and harness bundle
│   ├── canonical/                # 6 reference Rust patterns
│   ├── gates/                    # 4 QA gates (Python)
│   ├── harness/                  # TypeScript Redux modules
│   ├── agents/                   # Agent prompts (YAML)
│   └── integrations/             # RFC-9122 Git/Linear/Slack specs
├── docs/
│   ├── implementation_plan.md    # Detailed integration plan
│   ├── walkthrough.md            # Phase 1 & 2 implementation walkthrough
│   ├── forge_missing_controls.md # Gap analysis
│   └── forge_synchronization.md  # RFC alignment document
└── README.md                     # This file
```

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.9+ (for QA gates)
- Linear API key
- Slack bot token

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/sx9-forge.git
cd sx9-forge

# Install dependencies
npm install

# Setup API keys
cp .env.example .env.local
# Edit .env.local with your keys

# Run development server
npm run dev
```

Navigate to `http://localhost:3001/forge`

---

## Implementation Status

### ✅ Completed (Phase 1 & 2)

- [x] Harness mode selector (Build/Research/Security/Planning)
- [x] Persona selector (FORGE/AXIOM/VECTOR/SENTINEL)
- [x] Inference parameters (model + temperature)
- [x] Use Harness toggle
- [x] Linear integration controls (team + auto-create toggle)
- [x] Slack integration controls (channel + notifications toggle)
- [x] Context source toggles (Memory/Linear/Drive/Filesystem/Web)

### 🚧 In Progress (Phase 3 & 4)

- [ ] QA gates integration (4-dimensional scoring)
- [ ] Redux intelligence layer (pattern/tool/threat queries)
- [ ] Agent prompt execution
- [ ] Vector DB panel (ChromaDB collection management)
- [ ] Grammar validation display
- [ ] Hash preview (Murmur3)
- [ ] Mission history/templates
- [ ] Execution monitoring (progress, logs)
- [ ] Atomic clipboard access

---

## Architecture

### UI Layer (React + TypeScript)

- **PromptForgeScreen.tsx** - Main IDE interface
- **Two-Glyph Rail System** - Collapsible left/right sidebars
- **6 Control Tabs** - Harness, Persona, Inference, Linear, Slack, Context

### Intelligence Layer (Redux)

- **Leptose Connection** - Rust inference engine
- **ChromaDB Connection** - Vector store for pattern matching
- **Query Types** - Patterns, Tools, Threats, EEI

### QA Layer (Python)

- **Static Gate** - Structure + complexity analysis
- **Arch Gate** - ECS compliance + forbidden dependencies
- **Pattern Gate** - Canonical pattern matching
- **Aggregator** - Final grade calculation (A-F)

### Workflow Layer (Git/Linear/Slack)

- **Branch Strategy** - feature/* (human), factory/* (agent)
- **Linear States** - Backlog → Ready → Building → Review → Done
- **Slack Channels** - #sx9-factory, #sx9-review, #sx9-decisions, #sx9-alerts
- **Decision Gates** - Human approval via Slack reactions

---

## Documentation

- [Implementation Plan](docs/implementation_plan.md) - Detailed integration roadmap
- [Walkthrough](docs/walkthrough.md) - Phase 1 & 2 implementation details
- [Gap Analysis](docs/forge_missing_controls.md) - Missing controls inventory
- [RFC Synchronization](docs/forge_synchronization.md) - RFC-9112 & RFC-9116 alignment

---

## Contributing

This is an internal SX9 project. For questions or issues, contact the development team.

---

## License

Proprietary - SX9 Internal Use Only
