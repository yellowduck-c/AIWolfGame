# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository now contains a working frontend/backend scaffold for an AI Werewolf game in addition to the original requirement documents. The codebase is still evolving quickly, so verify commands and module layout against the current files before making structural assumptions.

## Commands

Verified commands should be re-checked against the current manifests before use. At minimum, backend runtime tests exist under `werewolf_backend/tests/`; prefer verifying exact commands from the current Python environment and test tooling before suggesting broader build/lint workflows.

## Project goal

The project is an AI Werewolf multi-agent system built to study asymmetric-information gameplay under a Multi-Agent collaboration framework. The main goal is not only to run a Werewolf game, but to model how role-specific agents cooperate, compete, reason, speak, and decide under strict information-isolation constraints.

The system should support:

- Full 6-12 player AI Werewolf games.
- Role-specific autonomous behavior for Werewolf, Seer, Witch, Hunter, and Villager agents.
- Structured logging for full-game observability, replay, evaluation, and post-game analysis.
- A spectator UI for pure AI matches, with human-in-the-loop play reserved as an extension.

## Current architecture

The codebase currently uses a front-end/back-end split:

- Frontend: Vue 3 + TypeScript + Vite, Element Plus, Pinia, Axios, WebSocket.
- Backend: FastAPI + WebSocket, asyncio, Redis-backed runtime persistence, game engine orchestration, agent package, and an LLM service layer.
- Communication model: HTTP for health/basic endpoints; WebSocket for game control and real-time phase updates, speeches, status changes, and control events.

Current backend package layout:

```text
werewolf_backend/
├── main.py
├── agent/
├── api/
├── cache/
├── config/
├── database/
├── game_engine/
├── llm_service/
├── tests/
├── utils/
└── websocket/
```

Current frontend layout centers on `werewolf_frontend/src/` with stores, utils, views, and components.

## Big-picture architecture constraints

### Agent system

Agents share a common base abstraction but differ by role goals and action space.

Expected cross-cutting agent concerns:

- Shared agent interface for speech, voting, skill use, and state updates.
- Layered memory model: short-term, long-term, and private memory.
- Role-specific behavior:
  - Werewolves cooperate, conceal identity, and coordinate kills.
  - Seer performs identity checks and builds public reasoning.
  - Witch manages heal/poison tradeoffs.
  - Hunter reacts to death-triggered actions.
  - Villagers reason only from public information.

### Information isolation

This is a core architectural requirement.

Implementations must clearly separate:

- Public information available to all players.
- Camp-shared information such as werewolf night coordination.
- Private role information visible only to the acting agent.

No agent should be able to read internal reasoning, memory, or hidden state that its role should not know.

### Game engine responsibilities

The backend game engine is responsible for:

- Game creation and role assignment.
- Phase and turn progression.
- Scheduling agent actions at the correct time.
- Resolving votes, skills, eliminations, and endgame checks.
- Emitting structured events and final outcomes.
- Persisting runtime summary and replayable event history in Redis.

The simplified required loop is: night actions → day announcement → speeches → voting → win-condition check.

### Observability and logs

Structured logs are part of the product, not an afterthought. The requirements expect logs that capture:

- Game metadata such as game ID, player count, role allocation, and model configuration.
- Phase-level events and timestamps.
- Agent actions including speeches, votes, skill targets, and status changes.
- Final outcome and camp survival summary.

These logs should be suitable for real-time UI rendering, replay, evaluation, and retrospective analysis.

## WebSocket protocol requirements

Frontend → backend commands currently include:

```json
{"cmd":"GAME_START"}
{"cmd":"GAME_PAUSE"}
{"cmd":"GAME_STOP"}
{"cmd":"GAME_RESET"}
```

The requirements also mention likely future extensions such as speed control and human actions.

Backend → frontend events currently include at least:

- `GAME_STARTED`
- `AGENT_SPEAK_CHUNK`
- `AGENT_SPEAK`
- `AGENT_STATUS_CHANGE`
- `AGENT_VOTE`
- `AGENT_SKILL`
- `PHASE_CHANGE`
- `GAME_OVER`
- `GAME_PAUSED`
- `GAME_RESET`
- `ERROR`

## Frontend expectations

The main UI is a god-view spectator dashboard after game start. It must show hidden game information rather than a player-limited perspective.

Key expectations from the requirements:

- Agent cards display player ID, true role, camp, alive/dead/exiled status, and current speech.
- A global public speech log shows timestamp, player ID, role, and content.
- Per-agent speech history or recent speech should be visible in each card.
- Layout must adapt cleanly for 6-12 players, with 6-8 fitting compactly and 9-12 using a two-row grid.
- Dead or exiled players should be visually distinct.
- UI controls should at least cover start, pause, stop, reset, and optionally speed adjustment.

## Scope notes from the requirements

The project is expected to support pure AI matches first. Human-vs-AI mixed play, evaluation/leaderboard tooling, and self-evolving agents are described as extensions or advanced directions, not the initial baseline.
