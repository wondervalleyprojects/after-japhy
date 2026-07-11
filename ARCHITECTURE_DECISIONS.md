# AFTER JAPHY — Architecture Decisions Record
*Web release, July 2026. For the WVP steward's corpus inbox — this deploy
is research the wider network plan learns from.*

## The decision

Deploy the working Flask application whole to a single always-on Fly.io
machine (shared-cpu-1x, 1GB RAM, Los Angeles), with the 128MB retrieval
index baked into the deploy image from the local machine and session logs
on a 1GB persistent volume. ~$6/month hosting; API spend capped at the
Anthropic workspace level.

## What the app actually was when the deploy decision landed

The deploy brief assumed Flask + Chroma + embeddings. That was v1. The
running v2 app is LazyGraphRAG: BM25 (rank_bm25 pickle) + SQLite FTS5
hybrid retrieval, per-query NetworkX mini-graphs, Claude Haiku 4.5, and
**zero embeddings anywhere**. The measured runtime footprint — 26,860
chunks, 128MB on disk, ~450MB in RAM once the BM25 pickle inflates —
is what priced the options. Lesson worth keeping: *measure the artifact,
not the architecture doc.* Hosting decisions hang on the loaded RAM
number, and it is 3.5× the on-disk size.

## What was rejected, and why

**Serverless + Turso (hosted SQLite).** Rejected on three grounds.
First, the premise was stale: "move the precomputed embeddings into
Turso" assumed artifacts that no longer exist — the rework would really
have been a retrieval rewrite (FTS5-only, since a 450MB pickle cannot
live in a function runtime), a port of four endpoints, and moving
session logs out of flat files the artist owns into a hosted database.
Second, timing: 2–3 days of rework and a re-validation of retrieval
behavior against the persona, before an end-of-September date, to save
~$6/month. Third, custody was already satisfied: corpus.db *is* one
downloadable SQLite file, and the master corpus lives on the artist's
machine with a plain-markdown export beside it.

**Render.** Builds only from git, so the index (never committed) would
need a fetch-at-boot bucket; and the $7 tier's 512MB is a memory-kill
away from a 450MB app. The old render.yaml also ran 2 gunicorn workers —
doubling RAM to ~900MB. Removed from the repo.

**Netlify (backend or frontend).** WVP's Netlify credits are a shared
pool across three public sites; ruled out for compute outright, and no
frontend split was needed — Flask already serves the one HTML file.

**Free-tier cost optimization (FTS5-only retrieval refactor).** SQLite
FTS5 has native BM25 ranking; dropping the pickle would shrink the app
to ~60MB RAM and fit any free tier. Deliberately deferred, not rejected:
it changes the retrieval path of a piece that already works, weeks
before a date. The lever exists if hosting cost ever matters. It doesn't
at $6.

## Decisions inside the deploy

- **The model seam.** All model calls go through `model_seam.py`;
  provider/endpoint/model name exist in that file only (WVP ruling,
  July 10 2026: no piece structurally dependent on one AI vendor).
  Switching engines later is editing one file — but the seam's docstring
  carries the warning that the persona is tuned against Claude's service
  tropism, and any model change re-runs the brief's adversarial tests.
- **The gate is the threshold.** Access = unlisted URL + one shared word
  published in a paid Substack post, typed into the threshold input
  itself. Wrong word: the input clears; the threshold does not explain
  itself. Signed session cookie; no accounts, no email capture, no
  analytics. Rotating the word is one command.
- **Spend guards speak Stillness.** Per-session turn cap and daily
  request cap. At a cap the server returns a non-response and the
  client's existing Stillness choreography dims the room — the brief's
  own disengagement exit ("a short, cold, or refusing reply — or simple
  non-response"). The model is never asked to narrate a budget; the
  infrastructure's limits wear the piece's own gesture.
- **No model spend on drive-bys.** The opening reflection used to fire
  on page load; it now fires only after the gate opens.
- **Amnesia preserved in the infrastructure.** Nothing about a visitor
  persists except the server-side JSON session logs the brief already
  specifies (on the volume, private, the artist's). No visitor memory,
  no registry, no cross-session continuity, no connection to
  wondervalleyusa.com systems.
- **Corpus as archive first.** `export_corpus_markdown.py` renders all
  75,816 records to plain markdown with provenance headers (source,
  date, era, tier), one file per source per year. Readable with no
  product installed, greppable, portable. The index is a derivative;
  the archive is the thing.

## Notes for the design documentation (deliverable #1)

Things this deploy surfaced that belong in the 5,000–8,000 words:

1. **The economics of refusal.** A reader that owes visitors nothing
   costs almost nothing: two Haiku calls per turn ≈ $0.001. The piece's
   entire monthly infrastructure is a bar tab. There is an argument here
   about how cheap non-servile AI is once you stop paying for the
   apparatus of engagement — no analytics, no accounts, no retention
   machinery. The absence of the growth stack is not just ethical, it is
   the cost model.
2. **The caps wear the persona.** The most interesting design moment in
   the deploy: rate limits and budget exhaustion had to be expressed
   *somehow*, and the honest options were an error message (breaks the
   room) or the Stillness (is the room). That infrastructure constraints
   can be absorbed into the piece's own vocabulary of disengagement —
   the reader was always allowed to stop — seems generalizable to the
   whole Remains series.
3. **The gate as dramaturgy.** A password field would have been a
   product gesture. The access word typed into the threshold — the same
   input that begins the reading — makes admission part of the piece.
   The word arrives inside a paid Substack post: the subscription *is*
   the invitation, without the infrastructure ever knowing who anyone is.
4. **Amnesia has an ops counterpart.** "The piece does not remember
   visitors; the infrastructure shouldn't either" turned out to be a
   checklist: no cookies beyond the gate, no analytics, no logs of IPs
   in the app layer, session ID minted client-side and discarded. Worth
   documenting as a pattern: dispositional design has infrastructure
   obligations.
5. **The stale-brief lesson.** Between brief v3 (April) and deploy
   (July), the retrieval architecture was replaced entirely and the
   model dropped a tier. The deploy held because the *experience*
   contract (threshold, exits, disposition) was the stable interface and
   the architecture underneath was allowed to churn. For the Civic
   Protocols material: specify pieces by their experiential invariants,
   not their stacks.
