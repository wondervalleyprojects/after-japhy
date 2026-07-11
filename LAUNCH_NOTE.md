# AFTER JAPHY — Launch Note

*Fill the two placeholders when you run the deploy (DEPLOY_GUIDE.md).
Everything else is already true.*

## The piece

- **URL:** `https://after-japhy.fly.dev` *(→ confirm after `fly apps create`;
  the app name you choose becomes the URL)*
- **Gate word:** *(whatever you set as `GATE_WORD` in Step 3)* — published
  only inside a paid Substack post. Visitors type it into the threshold
  input. Wrong word: nothing happens. No accounts, no email capture, no
  analytics, no tracking. The reader will not remember them; neither does
  the infrastructure.

## The caps

| Guard | Value | Behavior when hit |
|---|---|---|
| Turns per session | 30 | The reader stops responding; the room dims (Stillness) |
| Requests per day | 500 | Same — the reading resumes tomorrow |
| Monthly API spend | $10 hard cap at the Anthropic workspace | Model calls fail; the reader says something obstructed the reading |

## The monthly cost

~$5.85 to Fly (1GB always-on machine + 1GB log volume) + $2–5 of Haiku
usage at expected soft-launch traffic, hard-capped at $10. **Total: under
$16/month, ceiling included.**

## The runbook

To **rotate the word** (new subscriber cycle, or the word leaks):
`fly secrets set GATE_WORD="new-word"` — the app restarts in ~30 seconds,
the old word dies immediately, publish the new one in Substack. To
**rotate the key**: create a new key in the `after-japhy` Anthropic
workspace, `fly secrets set ANTHROPIC_API_KEY="..."`, confirm `/health`,
then disable the old key in the console. To **take it down**:
`fly scale count 0` pauses it (logs and config survive, machine billing
stops); `fly scale count 1` wakes it; `fly apps destroy after-japhy` ends
it permanently. Session logs are yours alone, on the volume:
`fly ssh sftp shell` → `get /data/logs/<session>.jsonl`.
