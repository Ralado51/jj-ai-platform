# JJ AI Platform

Core platform and Creator OS for the JJ Network AI ecosystem.

## Vision

The JJ AI Platform centralizes projects, agents, tasks, executions, assets, memory and integrations. The first product is Creator OS.

## MVP

### Core Platform
- Projects
- Agents
- Tasks
- Executions
- Assets
- Memory
- API ↔ n8n

### Creator OS
- Video upload
- Whisper transcription
- AI analysis
- FFmpeg clip generation
- Review

## Architecture

```text
Next.js
   ↓
FastAPI
   ↓
PostgreSQL + pgvector
   ↓
n8n
   ↓
Whisper + FFmpeg + OpenAI
```

## Initial structure

```text
apps/
packages/
modules/
infrastructure/
docs/
n8n-workflows/
```

## Sprint 1
- Architecture
- Docker Compose
- PostgreSQL
- FastAPI
- Next.js
- Core models
- API ↔ n8n contract
