# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository currently contains requirement documents only, primarily [项目实现规划.md](项目实现规划.md) and [课题要求.md](课题要求.md). No backend, frontend, package manifests, or test configuration have been created yet. Do not invent build, lint, or test commands until the corresponding project files exist.

## Commands

There are no verified development commands yet because the codebase has not been scaffolded. Before suggesting or running build, lint, test, dev-server, or single-test commands, first verify that the relevant project manifests and tool configuration files have been added.

## Project goal

The project is an AI Werewolf multi-agent system built to study asymmetric-information gameplay under a Multi-Agent collaboration framework. The main goal is not only to run a Werewolf game, but to model how role-specific agents cooperate, compete, reason, speak, and decide under strict information-isolation constraints.

The system should support:

- Full 6-12 player AI Werewolf games.
- Role-specific autonomous behavior for Werewolf, Seer, Witch, Hunter, and Villager agents.
- Structured logging for full-game observability, replay, evaluation, and post-game analysis.
- A spectator UI for pure AI matches, with human-in-the-loop play reserved as an extension.

## Intended architecture

The requirements describe a front-end/back-end split:

- Frontend: Vue 3 + TypeScript + Vite, Element Plus, Pinia, Axios, WebSocket.
- Backend: FastAPI + WebSocket, asyncio, SQLite, an agent-team layer, and an LLM service layer.
- Communication model: HTTP for game creation and configuration; WebSocket for real-time phase updates, speeches, status changes, and control events.

Target directory layout from the requirements:

```text
werewolf_backend/
├── main.py
├── config/
├── api/
├── websocket/
├── game_engine/
├── agent_team_core/
├── llm_service/
├── database/
└── utils/

werewolf_frontend/
└── src/
    ├── stores/
    ├── utils/
    ├── views/
    └── components/
```

## Big-picture architecture constraints

### Agent system

Agents should share a common base abstraction but differ by role goals and action space.

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

Future implementations must clearly separate:

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

The simplified required loop is: night actions → day announcement → speeches → voting → win-condition check.

### Observability and logs

Structured logs are part of the product, not an afterthought. The requirements expect logs that capture:

- Game metadata such as game ID, player count, role allocation, and model configuration.
- Phase-level events and timestamps.
- Agent actions including speeches, votes, skill targets, and status changes.
- Final outcome and camp survival summary.

These logs should be suitable for real-time UI rendering, replay, evaluation, and retrospective analysis.

## WebSocket protocol requirements

Frontend → backend commands:

```json
{"cmd":"GAME_START"}
{"cmd":"GAME_PAUSE"}
{"cmd":"GAME_STOP"}
```

The requirements also mention likely future extensions such as speed control and human actions.

Backend → frontend events currently required by the documents:

- `GAME_STARTED`: sends all agents with `id`, `role`, `camp`, and `status`.
- `AGENT_SPEAK`: sends `id`, `role`, and `content` for a player speech.
- `AGENT_STATUS_CHANGE`: sends `id` and new `status` such as `dead`.
- `PHASE_CHANGE`: sends the current game phase.
- `GAME_OVER`: sends `winner`.

## Frontend expectations

The main UI is a god-view spectator dashboard after game start. It must show hidden game information rather than a player-limited perspective.

Key expectations from the requirements:

- Agent cards display player ID, true role, camp, alive/dead/exiled status, and current speech.
- A global public speech log shows timestamp, player ID, role, and content.
- Per-agent speech history or recent speech should be visible in each card.
- Layout must adapt cleanly for 6-12 players, with 6-8 fitting compactly and 9-12 using a two-row grid.
- Dead or exiled players should be visually distinct.
- UI controls should at least cover start, pause, stop, and optionally speed adjustment.

## Scope notes from the requirements

The project is expected to support pure AI matches first. Human-vs-AI mixed play, evaluation/leaderboard tooling, and self-evolving agents are described as extensions or advanced directions, not the initial baseline.
