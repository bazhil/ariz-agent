# Setup guide (Linux)

End-to-end setup of the ARIZ-Agent prototype: Docker → n8n (GigaChat) → OpenWebUI (Pipe) → optional patent ingest.

См. также: [README.md](../README.md) · [patent ingest](GOOGLE_PATENTS.en.md) · [Russian setup](SETUP_LINUX_ru.md) · [Windows](SETUP_WINDOWS.en.md) · [macOS](SETUP_MACOS.en.md) · [все ОС](SETUP.md)

---

## Prepare

1. Clone the repository:

```bash
git clone https://github.com/bazhil/ariz-agent.git
```

2. Enter the project directory:

```bash
cd ariz-agent
```

3. Create an environment file:

```bash
cp .env.example .env
```

Edit `.env` if you need custom ports or passwords. The GigaChat key is usually entered later in the n8n UI, not in `.env`.

`GIGACHAT_TIMEOUT=300` is the timeout **per** GigaChat HTTP call (seconds). A full ARIZ run takes several minutes and many such calls.

4. Start the stack:

```bash
docker compose up -d
```

`docker compose up` without `-d` streams logs in the terminal. Prefer `-d` for daily use. The first run pulls images and builds `patent_service`.

5. When containers are up, open:

| URL | Purpose |
|-----|---------|
| http://localhost:5678/setup | n8n owner account (first visit) |
| http://localhost:3000/ | OpenWebUI chat |
| http://localhost:8000/docs | patent-service Swagger (CSV upload) |

Health check: http://localhost:8000/health

---

## Configure n8n

### Owner account

Open http://localhost:5678/setup. Fill in email, name, and a password (8+ characters, at least one number and one capital letter). Click **Next**.

![n8n owner setup](images/setup/01-n8n-owner-setup.png)

### GigaChat community node

Go to **Settings → Community nodes → Install a community node**. Package name:

```text
n8n-nodes-gigachat
```

Accept the unverified-code warning and wait until **Installing** finishes. Refresh the page if the node does not appear.

![Install n8n-nodes-gigachat](images/setup/02-n8n-community-nodes.png)

### GigaChat credentials

**Credentials → Add credential**, search for `GigaChat`, click **Continue**.

![Add GigaChat credential](images/setup/03-n8n-add-credential.png)

Paste the **Authorization key** from the GigaChat console. **Scope** for a personal account is typically `GIGACHAT_API_PERS` (use the corporate scope from Sber docs if that is your contract). Leave default URLs unless you know you must change them:

- Base Auth URL: `https://ngw.devices.sberbank.ru:9443`
- Base Backend URL: `https://gigachat.devices.sberbank.ru/api/v1`

![GigaChat credential fields](images/setup/04-n8n-gigachat-fields.png)

Save. You should see **Connection tested successfully**.

![GigaChat connection tested](images/setup/05-n8n-gigachat-tested.png)

If the test fails, check the key, scope, and outbound HTTPS from the `ariz-n8n` container to Sber hosts.

### Import the workflow

**Import from File** → `n8n_workflows/ariz_85_v.json`. The canvas is the ARIZ-85-V chain; the end calls patent-service.

![ARIZ-85-V workflow](images/setup/06-n8n-workflow.png)

Select the saved GigaChat credentials on every GigaChat node. Clear remaining node warnings, save, and set the workflow **Active**.

### Webhook URL

Open the **Webhook** node. For everyday chat use the **Production URL**:

`http://localhost:5678/webhook/<uuid>`

The screenshot shows the **Test URL** (`…/webhook-test/…`). That is useful while debugging, but then you must click **Listen for test event** each time. For OpenWebUI drop `-test` so the path is `/webhook/…` and keep the workflow **Active**.

![Webhook node](images/setup/07-n8n-webhook.png)

OpenWebUI runs **on the Docker network**. In Pipe Valves use hostname `n8n`, not `localhost`:

```text
http://n8n:5678/webhook/aa3eb1a4-66a4-4f63-9354-065d103e0a0f
```

Copy the UUID from your Webhook node (**Path**), if you did not change the imported workflow.

---

## Configure OpenWebUI

1. Open http://localhost:3000 and create the first admin user.
2. In UI settings, **disable** auto-generated chat titles, follow-up suggestions, and auto tags. Otherwise those calls pollute the agent output and degrade the ARIZ report.
3. **Admin Panel → Functions** (some builds: Workspace → Functions). Create a **Pipe**.
4. Paste the full contents of `openwebui_functions/ariz_85_v.py`.
5. In **Valves**:
   - **N8N_WEBHOOK_URL** — Production URL with host `n8n` (see above), not `webhook-test`.
   - **TIMEOUT** — raise it, e.g. `600` (seconds for the whole webhook). The code default is 120, which is too short for a full ARIZ run.
6. Enable the function.
7. New chat → select the Pipe → describe a technical problem and wait (minutes).

---

## Load patents

Patent search is optional; ARIZ chat works with an empty collection. To fill Qdrant:

1. On [Google Patents](https://patents.google.com/) (a VPN is often required) run a search and use **Download (CSV)**.

![Google Patents CSV download](images/setup/08-google-patents-csv.png)

2. Open http://localhost:8000/docs, **POST /load_csv**, choose the file, **Execute**. The first request may be slow while the embedding model downloads.

![patent-service load_csv](images/setup/09-patent-load-csv.png)

3. A `202` response includes `task_id` and `status_endpoint`:

```json
{
  "message": "CSV load started",
  "task_id": "5f224275-6734-4074-bde8-b179b42aed2a",
  "status_endpoint": "/load_status/5f224275-6734-4074-bde8-b179b42aed2a"
}
```

![load_csv accepted](images/setup/10-patent-load-accepted.png)

4. Poll **GET /load_status/{task_id}**. When `"status": "completed"`, the workflow can search that collection.

![load_status completed](images/setup/11-patent-load-status.png)

Query tips and CSV fields: [GOOGLE_PATENTS.en.md](GOOGLE_PATENTS.en.md).

---

## Use the agent

Open a chat with the ARIZ function enabled and state the conflict, constraints, and what must not change.

If you see Axios `timeout of 30000ms exceeded`, that is the GigaChat node limit, not OpenWebUI. Compose already sets `GIGACHAT_TIMEOUT=300`; recreate n8n (`docker compose up -d n8n --force-recreate`) and raise TIMEOUT in Pipe Valves.

---

## Commands

```bash
docker compose up -d
docker compose ps
docker compose logs n8n --tail 50
docker compose down
```
