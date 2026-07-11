# AFTER JAPHY — Deployment Guide (Option A: Fly.io)

*Step-by-step setup for the private web release. Written July 2026.*

Everything below is run from this project folder:

```
cd "/Users/jeffreyorlinski/Desktop/WVP/Apps/After Japhy/AfterJaphy"
```

The shape: one always-on 1GB Fly machine in Los Angeles running the Flask
app, with the 128MB retrieval index baked into the deploy image (it never
touches git) and session logs on a 1GB persistent volume. ~$6/month.

---

## Step 0 — One-time: a dedicated Anthropic key with a spend cap

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Create a **new workspace** named `after-japhy` (Settings → Workspaces).
   A separate workspace is what lets you cap this piece's spend without
   touching your other keys.
3. In that workspace: Settings → **Limits** → set a monthly spend limit.
   **$10/month** is generous — expected soft-launch usage is $2–5.
4. Create an **API key inside that workspace**, named `after-japhy-prod`.
   Copy it somewhere safe for Step 3. It goes into Fly as a secret and
   nowhere else — never into a file in this folder.

## Step 1 — One-time: install and sign in to Fly

```bash
brew install flyctl
fly auth signup        # or: fly auth login (if you have an account)
```

Fly asks for a card at signup; the app below bills ~$6/month.

## Step 2 — One-time: create the app and its volume

```bash
fly apps create after-japhy
```

If the name is taken, pick another (e.g. `wvp-after-japhy`), and change
the `app = "..."` line at the top of `fly.toml` to match. The name becomes
the URL: `https://<name>.fly.dev`.

Then create the volume that session logs live on:

```bash
fly volumes create japhy_data --region lax --size 1
```

## Step 3 — One-time: set the secrets

```bash
fly secrets set \
  ANTHROPIC_API_KEY="paste-the-key-from-step-0" \
  GATE_WORD="your-access-word" \
  SECRET_KEY="$(openssl rand -hex 32)"
```

- `GATE_WORD` is the shared access word you publish inside the paid
  Substack post. One word or phrase; matching is case- and
  whitespace-insensitive.
- `SECRET_KEY` signs the gate cookies. You never need to know it.

Optional caps (defaults shown; only set them to change them):

```bash
fly secrets set MAX_TURNS_PER_SESSION=30 MAX_REQUESTS_PER_DAY=500
```

## Step 4 — Deploy

```bash
fly deploy
```

This uploads the local folder (including `index/` — expect a few minutes
on the first push), builds the image, and starts the machine. Every future
deploy is this one command again.

**Do not run `fly launch`** — it will try to rewrite `fly.toml`.

## Step 5 — Verify

```bash
fly status
curl https://after-japhy.fly.dev/health
# → {"status": "ok", "records": 26860, "chunks": 26860}
```

Then the real test, in a browser: open `https://after-japhy.fly.dev`,
confirm the threshold appears, confirm a wrong word does nothing, type the
gate word, and interrupt the reading.

---

## Operations

### Rotate the access word (e.g., after a subscriber cycle)

```bash
fly secrets set GATE_WORD="the-new-word"
```

The app restarts itself (~30s). Publish the new word in Substack; the old
word stops working immediately. Open sessions keep their cookie until the
browser closes.

### Rotate the API key

Create a new key in the `after-japhy` workspace at console.anthropic.com,
then:

```bash
fly secrets set ANTHROPIC_API_KEY="new-key"
```

After the app restarts and `/health` is ok, disable the old key in the
console.

### Read the session logs (private, yours)

```bash
fly ssh sftp shell
# then inside the sftp shell:
ls /data/logs
get /data/logs/<session-id>.jsonl
```

Or interactively: `fly ssh console`, then `ls /data/logs`.

### Take it down

```bash
fly scale count 0        # pause (stops billing for the machine; keeps everything)
fly scale count 1        # resume
fly apps destroy after-japhy   # permanent teardown (asks for confirmation)
```

### Watch it

```bash
fly logs                 # live server output
fly dashboard            # billing, metrics, machine state in the browser
```

---

## Costs

| Item | Monthly |
|---|---|
| Fly shared-cpu-1x, 1GB RAM, always on | ~$5.70 |
| Fly volume, 1GB | ~$0.15 |
| Anthropic API (Haiku 4.5, 2 calls/turn) | ~$2–5 at soft-launch traffic, hard-capped by the workspace limit |
| **Total** | **~$8–11, capped** |

## Notes

- The corpus and index are **never in git**. They travel inside the deploy
  image from this machine. If you deploy from a different computer, copy
  the `index/` folder there first.
- Netlify is untouched by this deploy, per the WVP credit-pool caution.
- The unlisted URL + gate word is the whole access model: no accounts, no
  email capture, no analytics, nothing remembered about visitors beyond
  the session JSON logs on the volume.
