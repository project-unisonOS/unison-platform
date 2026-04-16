# Milestone 1 Native Runtime Profile

This document defines the concrete runtime and install contract for the supported Milestone 1 UnisonOS deployment.

It exists to turn the Milestone 1 install strategy into a platform-owned runtime profile rather than leaving the supported path implicit across broad compose defaults.

## 1. Supported Milestone 1 Target

Supported target:

- Ubuntu 24.04 LTS
- x86_64
- native installation
- local microphone and speakers
- local-first inference baseline

Canonical install path:

- `installer/install-native.sh`
- `unisonctl`
- `compose/compose.native.yaml`
- `docs/install.md`
- `docs/deployment/ubuntu-native.md`

Evaluator channels such as WSL2, Linux VM, and bare-metal ISO may continue to exist, but they are not the canonical supported install route for Milestone 1.

## 2. Product Shape

Milestone 1 is a narrow, local-first, single-machine operating surface.

It is not the full platform vision.

Milestone 1 product expectations:

- one person
- one machine
- text + voice as first-class interaction modes
- renderer-led operating surface
- small set of real outcomes
- bounded, supportable install and recovery path

## 3. Required Runtime Services

The supported Milestone 1 native profile should include these services.

### 3.1 Infrastructure

- `postgres`
- `redis`

### 3.2 Core platform services

- `auth`
- `context`
- `policy`
- `orchestrator`
- `inference`
- `storage`
- `experience-renderer`
- `agent-vdi`
- `io-core`
- `io-speech`

### 3.3 Integration services required by the current golden path

- `intent-graph`
- `context-graph`

### 3.4 Optional or non-blocking services for Milestone 1

These should not be treated as required for the supported Milestone 1 native route unless the runtime profile is later revised.

- `updates` (optional until the release/update path is fully promoted, and kept behind its compose profile)
- evaluator image build tooling
- broad observability extras
- non-primary modality services
- experimental or non-essential connectors

## 4. Service Exposure Policy

The Milestone 1 native profile should behave like a supported local product install, not a broad developer bring-up.

Therefore:

- only the required host-facing surfaces should be exposed by default
- internal service-to-service traffic should stay on the compose network
- host port publication should be treated as a deliberate install/runtime contract, not a broad convenience default

Minimum host-facing surfaces expected for Milestone 1:

- renderer
- orchestrator health/startup path as required by operations tooling
- auth bootstrap/admin path when auth is enabled
- any required local speech or diagnostics endpoint needed by the documented experience

Any additional published ports should be justified explicitly against Milestone 1 supportability or operator tooling needs.

## 5. Environment Contract

The supported Milestone 1 native path must distinguish between:

- required first-start values
- install-time defaults that are intentionally unsafe placeholders
- optional tuning values
- developer-only or evaluator-only overrides

### 5.1 Required before first start

At minimum, the native install must require replacement of:

- `UNISON_ENV=development`
- `POSTGRES_PASSWORD=unison_password`
- `JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production`

And, when auth is enabled:

- `UNISON_AUTH_BOOTSTRAP_TOKEN`

### 5.2 Required operator clarity

The environment contract should make it obvious which settings are:

- mandatory for supported native installs
- optional for local hardware tuning
- optional for model selection
- unsupported or evaluator-only for Milestone 1

## 6. Required Milestone 1 Journeys

The supported native runtime profile is only acceptable if it supports these end-to-end journeys:

1. Clean Ubuntu native install
2. First boot without developer-only ambiguity
3. Explicit first admin bootstrap
4. Renderer-led ready state
5. First text interaction
6. First voice interaction
7. Personal briefing
8. Safe Gmail summarize/draft path when configured
9. Bounded VDI retrieval/download path
10. Reboot and recovery via `unisonctl`

## 7. Validation Requirements

The supported native profile should remain tied to these checks:

- `unisonctl doctor`
- `unisonctl health`
- `make validate-golden`
- `make validate-recovery`
- `make qa-native-install`

Where available, acceptance should be run against the exact supported install profile, not a broader developer compose shape.

## 8. Release Requirements

Milestone 1 release assets should foreground the supported native route.

Release expectations:

- canonical native install documentation is present
- native install path is supportable from public docs
- manifest / bill of materials is published
- checksums are published
- release notes foreground the native route
- evaluator artifacts are secondary when present

## 9. Immediate Platform Follow-Up

The platform implementation should next make this profile more explicit in runtime assets by:

- separating supported native defaults from broad developer defaults where practical
- narrowing or documenting host-port exposure for the native route
- making release workflow outputs and notes foreground the native route
- keeping evaluator image channels clearly secondary in release materials

## 10. Runtime Bundle Note

The supported native installer/runtime path now defaults to:

- `compose/compose.native.yaml`

That bundle now serves as the canonical runtime entrypoint for the Milestone 1 native install route.

Current native-bundle rules:
- core services from `compose/compose.yaml` are included by default
- `agent-vdi` is opt-in behind the `vdi` compose profile
- `io-vision` and `io-core` are opt-in behind the `vision` or `multimodal` compose profiles
- `updates` remains opt-in behind the `updates` compose profile
- observability services remain opt-in behind the `observability` compose profile

Further narrowing of service exposure and optional-service removal can build on this explicit native bundle.

## 11. Bottom Line

For Milestone 1, the platform should optimize for one thing above all else:

- a clean, supportable, native Ubuntu install that produces a trustworthy functional system

Everything else should be framed as secondary until it reaches the same level of supportability.
