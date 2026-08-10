# ARIZAgent

Open-source prototype: run a technical / inventive problem through **ARIZ-85-V** using a chat UI (**OpenWebUI**), an orchestration workflow (**n8n**), an LLM (e.g. **GigaChat**), and optionally a patent search demo (**Qdrant** + small FastAPI service).

> **Russian docs:** [README.ru.md](README.ru.md) · **Quick start (RU):** [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md) · **Patents:** [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md) · **Services:** [docs/SERVICES.md](docs/SERVICES.md)

This is a **prototype for learning and experiments**, not a commercial TRIZ expert system and not a substitute for a patent attorney.

Method source: [ARIZ-85-V (Official G.S. Altshuller Foundation)](https://altshuller.ru/triz/ariz85v.asp).

---

## What you get

1. Describe a technical problem in plain language in the chat.
2. n8n runs a multi-step **ARIZ-85-V** pipeline (`workflows/ariz_85_v_3.json`).
3. You receive a structured report (problem framing, IFR, solution ideas, checks).
4. Optionally, generated ideas can be matched against patents you loaded into Qdrant.

**AI does not replace human judgment.** You formulate the problem and critically review the output. The pipeline only follows the ARIZ route you configured.

---

## Architecture

```text
User → OpenWebUI (chat + Pipe)
         → n8n webhook (ARIZ-85-V steps via LLM)
              ↘ optional: patent_service → Qdrant
```

| Service | Role | Default URL |
|---------|------|-------------|
| OpenWebUI | Chat UI | http://localhost:3000 |
| n8n | Workflow engine | http://localhost:5678 |
| PostgreSQL | n8n database | internal |
| Qdrant *(optional)* | Vector DB for patents | http://localhost:6333 |
| patent_service *(optional)* | CSV load + semantic search | http://localhost:8000 |
| Ollama *(optional)* | Local LLMs for OpenWebUI | http://localhost:11435 |

Official documentation links: [docs/SERVICES.md](docs/SERVICES.md).

---

## Requirements

- Docker + **Docker Compose V2** (`docker compose`, with a space)
- ~10+ GB free disk (first pull is large)
- LLM access used by the workflow (default nodes: **GigaChat** community package in n8n)
- No programming skills required for the basic path — see the Russian quick start

---

## Quick start (core stack)

```bash
git clone https://github.com/<your-account>/ariz-agent.git
cd ariz-agent
cp .env.example .env
docker compose up -d
```

Open:

- Chat: http://localhost:3000  
- n8n: http://localhost:5678  

Then (once):

1. In n8n: install the **GigaChat** community node, import `workflows/ariz_85_v_3.json`, add API credentials, set workflow **Active**, copy the **Production Webhook URL**.
2. In OpenWebUI: Admin → Functions → create a **Pipe**, paste `openai_functions/ariz_85_v.py`, set `N8N_WEBHOOK_URL` to that webhook, enable the function.
3. New chat → select the Pipe → send a technical problem → wait for the report (may take several minutes).

Step-by-step screenshots-oriented guide (Russian): [docs/QUICKSTART_ru.md](docs/QUICKSTART_ru.md).

### Optional: patents profile

```bash
docker compose --profile patents up -d
```

Then follow [docs/GOOGLE_PATENTS.md](docs/GOOGLE_PATENTS.md) to export CSV from Google Patents and load it into Qdrant.

### Optional: local Ollama

```bash
docker compose --profile ollama up -d
# point OpenWebUI OLLAMA_BASE_URLS=http://ollama:11434 in compose/.env if needed
```

The published ARIZ workflow uses **GigaChat via n8n**, not Ollama. Ollama is only for optional local models in the UI.

---

## Repository layout

```text
docker-compose.yml          # core + optional profiles
.env.example
workflows/ariz_85_v_3.json  # main ARIZ-85-V workflow
openai_functions/ariz_85_v.py
prompts/                    # readable copies of step prompts
patent_service/             # FastAPI + embeddings → Qdrant (vibe-coded demo)
patents/example.csv
docs/
```

`patent_service` is intentionally a **vibe-coded demo**: good enough for experiments, not an enterprise prior-art search.

---

## Feedback / research questionnaire

Russian questionnaire ready for Google Forms (TAM-oriented, usable for product feedback and pilot studies): [docs/questionnaire_ru.md](docs/questionnaire_ru.md).

---

## Disclaimer

- ARIZ methodology belongs to the legacy of G.S. Altshuller / the Official Foundation; this repo ships a **software wrapper and prompts**, with a link to the original text.
- Outputs may be wrong or shallow — always review.
- Patent matching is illustrative only.

## License

MIT — see [LICENSE](LICENSE).
