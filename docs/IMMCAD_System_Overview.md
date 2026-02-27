# IMMCAD System Overview

## Table of Contents

- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Core Mission](#core-mission)
- [Jurisdictional Scope](#jurisdictional-scope)
- [Key Features](#key-features)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)
- [Compliance and Security](#compliance-and-security)

- [Introduction](#introduction)
- [Core Mission](#core-mission)
- [Jurisdictional Scope](#jurisdictional-scope)
- [Key Features](#key-features)
- [Technical Stack](#technical-stack)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)
- [Compliance and Security](#compliance-and-security)

## Introduction

**IMMCAD** is an AI-powered legal assistant specifically designed to navigate the complexities of **Canadian Immigration Law**. Transitioning from the legacy LawGlance architecture, IMMCAD implements a robust Retriever-Augmented Generation (RAG) pipeline to provide accurate, cited information regarding paths to permanent residency, study permits, and work authorizations.

## Core Mission

The mission of IMMCAD is to democratize access to high-quality legal information. By leveraging large language models (LLMs) grounded in official statutes and regulations, we aim to reduce the information asymmetry faced by prospective immigrants.

## Jurisdictional Scope

Unlike its predecessor which focused on Indian statutes, IMMCAD is exclusively focused on:
- **Immigration and Refugee Protection Act (IRPA)**
- **Immigration and Refugee Protection Regulations (IRPR)**
- **Citizenship Act**
- **IRCC Program Delivery Instructions**
- **Federal Court Decisions (Canadian Jurisprudence)**

## Key Features

- **Jurisdiction-Aware RAG**: Responses are grounded in Canadian legal artifacts.
- **Citation-First Policy**: Every claim is backed by a reference to specific sections of the IRPA or IRPR.
- **Provider Abstraction**: A modular backend that supports OpenAI (Primary) with Gemini (Fallback) to ensure high availability.
- **CanLII Integration**: Direct case search capabilities for legal research.
- **Privacy-Centric**: Strict data minimization and audit logging for legal compliance.

## Technical Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI backend + Next.js frontend (production), Streamlit thin client (legacy dev-only)
- **AI/NLP**: OpenAI GPT-4o-mini & Gemini 2.0 Flash
- **Vector Intelligence**: ChromaDB-backed retrieval pipeline with Canada-focused source governance
- **Orchestration**: Custom Modular API (`src/immcad_api`)
- **Observability**: Trace ID-centric logging and telemetry.

## Observability and Ingestion Checkpoints

- **Trace logging**: Trace ID propagation across ingest jobs, chat requests, and export flows makes it easier to diagnose production issues end-to-end.
- **Checkpoint sharing**: The ingestion pipelines (`scripts/run_ingestion_jobs.py`, Cloudflare schedulers, `OfficialCaseLawClient`) and the `/api/sources/transparency` router all read/write the same checkpoint state file (`.cache/immcad/ingestion-checkpoints.json` by default or the one configured via `INGESTION_CHECKPOINT_STATE_PATH`). Keeping every deployment wired to the same path ensures the frontend dashboard reflects the latest Federal/FCA/SCC RSS fetch status and policy flags.

## Project Structure

- `src/immcad_api/`: The next-generation FastAPI backend.
- `docs/architecture/`: Technical design documents and ADRs.
- `scripts/`: Maintenance, ingestion, and deployment utilities.
- `frontend-web/`: Production chat interface.
- `app.py`: Legacy Streamlit dev client that forwards requests to `/api/chat` only.

## Future Enhancements

- **Bilingual Support**: Full English/French parity for official Canadian compliance.
- **Grounding Checks**: Automated verification of LLM responses against retrieved snippets.
- **Authorized Representative Portal**: Specific workflows for lawyers and RCICs.

## Compliance and Security

IMMCAD is NOT a replacement for legal advice. All responses include a mandatory legal disclaimer. The system follows PIPEDA-oriented data controls to ensure user privacy and confidentiality.
