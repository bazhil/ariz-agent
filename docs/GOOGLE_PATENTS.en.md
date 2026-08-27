# Google Patents → CSV → Qdrant

Full step-by-step guide is in Russian: **[GOOGLE_PATENTS.md](GOOGLE_PATENTS.md)**.

Summary:

1. `docker compose up -d` (includes Qdrant and `patent_service`)
2. Search on [Google Patents](https://patents.google.com/), download results CSV.
3. Upload via http://localhost:8000/docs → `POST /load_csv` or `curl -F file=@your.csv http://localhost:8000/load_csv`
4. Check `GET /health` and `GET /search?q=...`
5. Demo only — not a legal prior-art opinion.

Service docs: [SERVICES.md](SERVICES.md).
