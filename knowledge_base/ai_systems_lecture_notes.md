# CS402: Modern Agentic AI Systems & Architecture

## Lecture 1: Core Fundamentals
Agentic AI systems transition models from passive autoregressive next-token predictors into goal-directed, autonomous software entities capable of planning, tool invocation, environment perception, and outcome verification.

### 1. The ReAct Pattern (Reason + Act)
- **Thought:** The agent reasons over user intent and current environment state.
- **Action:** The agent calls a discrete deterministic tool (e.g., calculator, database, web search).
- **Observation:** The environment returns output or error status.
- **Reflection:** The agent verifies if the observation satisfies the prompt's sub-goal.

### 2. Retrieval-Augmented Generation (RAG)
RAG addresses hallucinations and context length limits by dynamically injecting relevant domain knowledge into the model context:
- **Chunking:** Splitting raw text into bounded semantic chunks (e.g. 500-1200 characters with 100-200 character overlap).
- **Embedding:** Encoding text chunks into dense high-dimensional vectors (e.g. `all-MiniLM-L6-v2` 384 dimensions).
- **Similarity Search:** Querying vector stores using cosine similarity or Euclidean distance.
- **Citations & Grounding:** Forcing the LLM to anchor statements to indexed sources.

### 3. Verification & Guardrails
- Autonomous systems must not execute consequential or irreversible operations (e.g., file deletion, money transfer, email broadcasting) without explicit human confirmation.
- Deterministic operations (math, aggregations, unit tests) must always be executed by verified Python functions rather than pure LLM mental arithmetic.

