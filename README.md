# Assignment Management System

Production‑ready assignment orchestration with LLM‑powered solution understanding, fast visualization, and teacher feedback workflows.

## Highlights

- **Graph intelligence**: FAISS embeddings + LLM verification dedupe and cluster solution steps; outputs both a DAG and a tree representation.
- **Teacher/Student UX**: Clean dashboards, secure uploads, inline feedback, and D3‑powered interactive graphs.
- **Live Agents view**: Real‑time SSE stream of LLM activity at `/agents`.
- **Parallel LLM pipeline**: Requests are issued concurrently end‑to‑end for high throughput with streaming updates to the UI.
- **Hybrid serving**: Qwen‑235B‑A22B‑FP8 is hosted locally via vLLM on a node of 8 H100s.
- **Adaptive reasoning**: Step granularity and output conciseness are fully configurable at runtime.

## Quickstart

1. Create env and install deps
   ```bash
   cd /home/ubuntu/hackmit2025
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the app
   ```bash
   python app.py
   ```
3. Open `http://localhost:5000`

## Configuration

Runtime behavior is controlled via `config.json`.

```json
{
  "provider": "local",
  "prompt_type": "concise",
  "step_size": "small",
  "concise_hint": "Really don't overthink too hard and be concise in your final output.",
  "models": {
    "openai": "o4-mini",
    "vllm": "Qwen/Qwen3-235B-A22B-FP8"
  }
}
```

- **step_size**: `small` or `big` for fine/coarse solution breakdown.
- **prompt_type / concise_hint**: tunes brevity of responses and UI text.
- **models**: selects remote and local backends. Local Qwen runs via vLLM; remote workloads can burst to 8× H100s on LambdaLabs.

## Architecture

- Flask backend, SQLite storage, secure uploads
- FAISS for vector search; LLM verification for semantic dedupe
- Solution views: `SolutionGraph` (DAG) and `SolutionTree` (hierarchy)
- D3.js front‑end visualizations and SSE live agent stream

## Core Routes

- Teacher: dashboard, assignment create, solution review, feedback
- Student: dashboard, assignment view, submit
- API: `GET /api/solution-graph/<assignment_id>` for graph data
- Agents: `GET /agents` live LLM telemetry

## Performance Notes

- Designed for parallel batched inference and streaming. Local vLLM serves Qwen‑235B‑A22B‑FP8; heavy jobs fan out across 8× H100s on LambdaLabs.
- Embedding search is O(log n)‑like via FAISS flat‑L2 with small candidate verification by LLM.

## Troubleshooting

- Port in use: change `app.run(..., port=5001)` in `app.py`.
- Upload errors: verify directory permissions and file size limits.
- Reset DB: delete the SQLite database file and restart.

## License

MIT
