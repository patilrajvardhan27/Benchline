# Item normalization (with LiteLLM)

## The problem

Benchmarks are only as good as the groups behind them. Until now a group was every NDC with the same
description text ([ADR 0005](adr/0005-item-grouping.md)). Real NADAC descriptions are messy: store brands
(`ALLERGY 25 MG TABLET`, `ALL DAY PAIN RELIEF 220 MG CAPLET`), brand names (`ZYPREXA`, `DROXIA`), salt
abbreviations (`HCL`, `MAG`, `SULF`) and release codes (`ER`, `XR`, `SR`). The same drug lands in several
groups, and brand and generic prices cannot be compared at all. This is the item-master quality problem in
miniature.

## How it works: cheapest trustworthy source first

```
NDC ──► 1. openFDA lookup by NDC ──► 2. rules on the description ──► 3. LLM through LiteLLM ──► 4. a person
         free, authoritative          free, deterministic             only for what is left      flagged rows
```

Each layer only handles what the one above could not. An LLM is the last resort on purpose: where a free,
authoritative lookup exists, a model adds cost and risk and nothing else.

## What happened on the real data

All 36,056 NDCs in the 2025 and 2026 NADAC files, against the openFDA NDC directory dated 2026-11-06
(253,343 NDCs, 2,933 distinct ingredient names):

| Layer | NDCs | Share |
|---|---|---|
| openFDA lookup | 28,966 | 80.3% |
| Rules | 4,658 | 12.9% |
| Left for the model | 2,432 (1,498 distinct descriptions) | 6.7% |

How good the deterministic layers are, scored on the 28,966 NDCs openFDA knows:

- The rules recognised the drug name for **76.4%**, and were right **99.33%** of the time.
- Form agreed with openFDA on **97.3%** (24,513 of 25,182). The 670 disagreements are flagged for review.
- Of 2,485 brand-name NDCs the rules correctly **abstained on 2,200**. Brands are what the rules cannot do.

Effect on grouping: **6,934 groups by raw description become 6,673 groups by product** (ingredient, release
modifier, strength, form, brand or generic). It is a modest drop, and the merges that matter are store brands
joining their generic: 16 differently worded diphenhydramine 25 mg tablets, 12 naproxen 220 mg, 13 insulin
lispro products. Brand and generic stay in separate groups, now by an explicit flag instead of by accident of wording.

## The model, measured

Run on 2026-11-10 with `anthropic/claude-haiku-5-5` at its default temperature, through the Anthropic API. It was
asked about 200 NDCs that openFDA knows and the rules did not recognise (mostly brand names). 174 got a usable
answer, covering 162 distinct descriptions; 26 got none. Each answer is scored once per distinct description
against openFDA's own ingredient.

| Measure (162 answers) | Result |
|---|---|
| Exact match with openFDA's ingredient | **82.7%** |
| Same drug, ignoring salt and ester names | **95.1%** |
| Ingredient named in the description (generic names) | 54 answers |
| Ingredient from the model's own knowledge (brand names) | 108 answers, **96.3%** same drug |
| Flagged for review | all 108 brand-name answers, by design |
| Cost of the run | $0.0355, 214,479 tokens, about $0.0002 per call |

What the misses look like: `SIMETHICONE` where openFDA says `DIMETHICONE`; multivitamin products where openFDA lists
eight or more ingredients and the model names one or a few; electrolyte solutions; `THYROID` for a desiccated
thyroid product that openFDA lists as levothyroxine plus liothyronine; and word order (`CONJUGATED ESTROGENS`
against `ESTROGENS, CONJUGATED`). Most are naming differences, not a wrong drug. The exact figure is the
conservative one; the lenient figure is generous to those cases.

Read these numbers with care:

- **One run, one model, 162 answers.** It shows the approach works, not how accurate it will be in general.
- **26 of the 200 were declined.** The model answered `UNKNOWN`, as the prompt asks when it is not sure. All 26 are
  listed in the fixture: store-brand and OTC products with no drug name in the text (`FT PAIN RELIEF 500 MG GELCAP`,
  `ARTIFICIAL TEARS DROPS`, `GNP ACID REDUCER 20 MG TABLET`) and two obscure brands. In at most two of them does the
  description contain the drug name, so declining was the right call. Declines are not in the accuracy figures.
- **openFDA is the answer key and is not hand-checked.** Some of its entries are odd (it lists Creon as three separate
  enzyme ingredients).
- **Scored on a stand-in population.** The model's real job is the 1,498 descriptions openFDA does *not* know,
  which cannot be scored automatically. On cheap surface features the two populations look alike (store-brand
  prefix 15% of the scored sample against 17% of the real workload; no number in the text 11% against 13%;
  OTC-style words 15% against 13%), so there is no evidence the real workload is harder, and none that it is not.
  The honest reading is "about this good on descriptions of this kind".
- **The scoring was corrected once.** A first scoring of these same answers gave 67.8% exact, because the salt list
  was missing six ester names (`PIDOLATE`, `ACETONIDE`, `MEDOXOMIL` and others), so right answers counted as wrong.
  The words were added and the saved answers re-scored; no new calls were made.
- **Sampling error.** With 162 answers the 95% confidence interval (Wilson) is 90.6% to 97.5% for "same drug",
  76.2% to 87.8% for exact, and 90.9% to 98.6% for the 108 brand-name answers.

**Check it yourself, for free.** Every answer from the run, with openFDA's ingredient beside it, is committed as
`pipelines/tests/fixtures/model_eval_claude_haiku_5_5.csv` (188 rows: 162 answered, 26 declined). The test
`pipelines/tests/test_model_eval_fixture.py` recomputes the verdicts from the raw strings and asserts the numbers
above, so `uv run pytest tests/test_model_eval_fixture.py` reproduces them with no key, no network and no cost.
The eight "wrong" rows are in the same file for anyone to judge.

To repeat the run with a key: `normalize-eval --llm --sample 200 --silver data/full/silver/nadac.parquet`
(`--export file.csv` writes the per-case rows). To re-score saved answers with no key:
`normalize-eval --offline --silver data/full/silver/nadac.parquet`.

## Guardrails on the model

| Risk | Defence |
|---|---|
| Invents an ingredient | Prompt says to answer `UNKNOWN` rather than guess; an unusable answer leaves the item in its old group |
| Names a brand's ingredient from its own knowledge | Allowed, but the row is marked for review: the name is not in the description |
| Invents a strength | Any number not in the description is thrown away |
| Provider outage, rate limit, budget refusal, bad JSON | The call fails soft and the item goes to review. After 5 failures in a row (`BENCHLINE_LLM_MAX_FAILURES`) the model is left alone for the rest of the run, so a refusing gateway is not asked 2,439 times |
| Runaway cost | `BENCHLINE_LLM_MAX_USD` stops calls once the run has spent that much; `--max-llm N` caps how many descriptions are tried, refusals included; the gateway adds its own key budget |
| Re-running costs money and changes answers | Every answer is cached by prompt version, model and description, so a re-run is free and identical |
| Silent changes | Each result records its method, so a group built from a model answer can be found and checked |

## Using LiteLLM

Two ways, same code:

**Direct (the Python library).** The pipeline builds a LiteLLM `Router` with the primary model, an optional
fallback model, retries and a timeout. Good for one service.

```bash
export BENCHLINE_LLM_MODEL=openai/gpt-4o-mini
export BENCHLINE_LLM_FALLBACK_MODEL=anthropic/claude-haiku-5-5   # optional
export OPENAI_API_KEY=...  ANTHROPIC_API_KEY=...
export BENCHLINE_LLM_MAX_USD=2.00
```

**Using a Claude (Anthropic) key instead of OpenAI.** Get a key in the Anthropic Console (a chat subscription does not
include API access), then:

```bash
read -s "ANTHROPIC_API_KEY?Paste key, then press Enter: "
export ANTHROPIC_API_KEY
export BENCHLINE_LLM_MODEL=anthropic/claude-haiku-5-5 BENCHLINE_LLM_MAX_USD=1
```

LiteLLM 1.108.4 knows the price of `claude-haiku-5-5`, so the spend cap works. The newest Claude models accept only
their default temperature, so the client sends `temperature=0` once, sees it rejected, drops it, and carries on. The
consequence is that answers can differ between runs; the answer cache makes a re-run identical. Set
`BENCHLINE_LLM_TEMPERATURE=none` to skip the first rejected attempt. Confirmed with a live run on 2026-11-10 (see "The model, measured").

**Through the LiteLLM gateway.** One OpenAI-compatible endpoint in front of the providers, with virtual keys,
budgets, rate limits and spend tracking per key. Good when several services or people need different
limits. The config is [deploy/litellm/config.yaml](../deploy/litellm/config.yaml).

Two requirements from LiteLLM's [virtual keys page](https://docs.litellm.ai/docs/proxy/virtual_keys): the master
key must start with `sk-`, and key management needs a PostgreSQL database. Compose creates a separate `litellm`
database for it (see `deploy/docker/postgres-init`).

```bash
# .env: set LITELLM_MASTER_KEY (starts with sk-), NORMALIZER_API_KEY and, optionally, NORMALIZER_FALLBACK_API_KEY
docker compose --profile llm up -d litellm

# a key for the pipeline only: one model, a hard budget, a rate limit
curl -s http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"key_alias": "benchline-normalizer", "models": ["benchline-normalizer"],
       "max_budget": 2, "budget_duration": "30d", "rpm_limit": 60}'
# the reply contains the new key (it starts with sk-). Copy it.

export BENCHLINE_LLM_MODEL=openai/benchline-normalizer
export BENCHLINE_LLM_API_BASE=http://localhost:4000
export BENCHLINE_LLM_API_KEY=<the new key>

# what has it spent? the amount, in USD, is info.spend in the reply
curl -s "http://localhost:4000/key/info?key=$BENCHLINE_LLM_API_KEY" -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# switch it off if it leaks or you are done
curl -s http://localhost:4000/key/block -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" -d '{"key": "'"$BENCHLINE_LLM_API_KEY"'"}'
```

### Prove the budget works

**Needs Docker Desktop.** Install it with `brew install --cask docker-desktop`, open the Docker app once, and wait until
its menu-bar icon stops animating. Check with `docker --version` and `docker compose version`. The gateway's key
database needs Prisma; the official image has it built in. The Docker image is the supported way to run the gateway; a plain `pip` install also needs
`prisma generate` and a local Postgres.

If an old Docker install left dead links behind, `docker` says "command not found" and Homebrew refuses to install
over them. Check with `ls -la /usr/local/bin | grep Docker.app`; if the targets are missing, remove those links
(`sudo rm` them one by one), then install again.

Pasting commands into zsh: run `setopt interactive_comments` once (and add it to `~/.zshrc`), otherwise a trailing
`# comment` is passed to the command as arguments.

**No provider key? Use the mock model.** [deploy/litellm/config.mock.yaml](../deploy/litellm/config.mock.yaml) makes the
gateway answer with a canned reply while still counting tokens, spend and budgets. Start it with
`LITELLM_CONFIG=./deploy/litellm/config.mock.yaml docker compose --profile llm up -d postgres litellm`. You can skip
`NORMALIZER_API_KEY` in step 1. If the spend stays at 0 with the mock, use a real key instead. The mock config
loads without error in LiteLLM 1.108.4 and its spend counting works (see the budget test below).

About ten minutes and under a cent. You need Docker Desktop running and an OpenAI key (set a spending limit on it
in OpenAI's dashboard first). LiteLLM's page does not say what a key gets once it passes `max_budget`, so this
finds out for your version.

1. **Create `.env`.** The copy already has working local values for `POSTGRES_PASSWORD` and `DEV_JWT_SECRET`. The
   gateway's admin key must start with `sk-`; this makes a random one and puts it in your shell:
   ```bash
   cp .env.example .env
   sed -i '' "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=sk-$(openssl rand -hex 16)|" .env
   export LITELLM_MASTER_KEY=$(grep '^LITELLM_MASTER_KEY=' .env | cut -d= -f2)
   ```
   (Do not `source .env`: a value with a space in it breaks. On Linux use `sed -i` without the `''`.)
   With the real config (`config.yaml`) also set `NORMALIZER_API_KEY` to your OpenAI key and leave
   `NORMALIZER_FALLBACK_API_KEY` empty; if the gateway will not start with it empty, delete the fallback model and the
   `fallbacks:` line from `deploy/litellm/config.yaml`. With the mock config you need no provider key at all.
2. **Start the gateway** (it only needs Postgres):
   ```bash
   docker compose --profile llm up -d postgres litellm
   # only if your Postgres volume already existed before the litellm database was added:
   docker compose exec postgres createdb -U benchline litellm && docker compose restart litellm
   docker compose logs --tail 30 litellm            # look for errors, then:
   curl -s http://localhost:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"   # lists benchline-normalizer
   ```
3. **Make a key with almost no budget.** This stores it in `BENCHLINE_LLM_API_KEY` for you, so there is nothing to
   copy. (Do not type a placeholder such as `<the key>`: zsh reads `<` as a redirect.) Key aliases must be unique,
   so use a new one each time:
   ```bash
   export BENCHLINE_LLM_API_KEY=$(curl -s http://localhost:4000/key/generate -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" -d '{"key_alias": "budget-test-1", "models": ["benchline-normalizer"], "max_budget": 0.0001}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["key"])')
   echo ${BENCHLINE_LLM_API_KEY:0:7}
   ```
4. **Send eight brand names through it.** `--fresh` ignores the answer cache so every call really goes out:
   ```bash
   export BENCHLINE_LLM_MODEL=openai/benchline-normalizer BENCHLINE_LLM_API_BASE=http://localhost:4000 BENCHLINE_LLM_MAX_FAILURES=3
   uv run --project pipelines python -m benchline_pipelines normalize-probe --fresh "ZYPREXA 15 MG TABLET" "DROXIA 400 MG CAPSULE" "KERENDIA 20 MG TABLET" "FETZIMA 20 MG CAPSULE" "AMNESTEEM 10 MG CAPSULE" "CAMRESE LO TABLET" "SYNTHROID 50 MCG TABLET" "DESCOVY 120-15 MG TABLET"
   ```
   With the mock model, expect two answers (about $0.000066 each, so the $0.0001 budget is gone after the second),
   then three `FAILED` lines, then `skipped (too many failures in a row)`. The mock gives the same canned reply to every
   description, so every answer says OLANZAPINE: that is the mock, not a bug, and the checks flag the mismatches.
5. **Check the books.** `info.spend` should be at or just over the budget. It is written a minute or two after the calls, so it can read `0.0` at first:
   ```bash
   curl -s "http://localhost:4000/key/info?key=$BENCHLINE_LLM_API_KEY" -H "Authorization: Bearer $LITELLM_MASTER_KEY"
   ```
6. **Optional: see the pipeline cope with it on real data.** The 12-drug subset in `data/silver` has almost nothing for
   the model, so build a full silver file first, then cap the run at five descriptions:
   ```bash
   mkdir -p data/full && ln -s ../bronze data/full/bronze
   uv run --project pipelines python -m benchline_pipelines --data-dir data/full silver
   uv run --project pipelines python -m benchline_pipelines normalize --silver data/full/silver/nadac.parquet --llm --max-llm 5
   ```
   The printed `llm` block shows calls, failures and the error text; `data/full/silver/needs_review.csv` lists the items
   that kept their old group.
7. **Clean up.** Switch the test key off, stop the gateway, and remove the symlink:
   ```bash
   curl -s http://localhost:4000/key/block -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" -d '{"key": "'"$BENCHLINE_LLM_API_KEY"'"}'
   docker compose --profile llm down && rm -rf data/full
   ```

**What this showed (LiteLLM 1.108.4, mock model, run on 2026-11-10).**

| Observation | Detail |
|---|---|
| The refusal | HTTP **422**, `error.type` `budget_exceeded`, message `Budget has been exceeded! Key=budget-test-agent (sk-...SkfA) Current cost: 0.000132, Max budget: 0.0001` |
| What the Python library raises | `BadRequestError` carrying that message (LiteLLM maps the 422 to it) |
| How soon it bites | The gateway refused from the third call. The pipeline's own cost estimate ($0.000066 a call) matched the gateway's total of $0.000132 |
| Spend visible in `key/info` | Not at once: `0.0` straight after the calls, `0.000132` a few minutes later. Enforcement did not wait for it |
| Surprise 1 | Setting the global `litellm.drop_params = True` made the Router return `None` instead of raising the refusal. The pipeline no longer sets it, and treats a `None` as a failed call |
| Surprise 2 | With one deployment, the client Router's cooldown turned one failure into several fake "no deployments available" errors that hid the real one. Cooldown is now off unless there is a fallback model |

**Write down:** the LiteLLM image version (`docker compose images litellm`), the exact refusal text and HTTP status,
how many calls succeeded before it started, the spend against the budget, and how long the delay was. That is the
finding.

Verified against the page: `sk-` master key, Postgres requirement, the fields `models`, `max_budget`,
`budget_duration` (for example `30d`), `rpm_limit`, `key_alias`, `/key/info` and `/key/block`. Not shown on the
page: the exact `/key/generate` reply shape and the over-budget error, which is why the steps above say to check.
The page points to the gateway's own Swagger UI for the full field list.

The gateway handles retries and the fallback model, so the client sets only the alias.

## Running it

```bash
# 1. Measure the free layers (no key needed)
uv run --project pipelines python -m benchline_pipelines normalize-eval

# 2. Measure the model on hard cases, scored against openFDA's own answers (needs a key; costs a few cents).
#    Use the FULL silver file: the 12-drug subset has almost no brand names, so it barely tests the model.
mkdir -p data/full && ln -s ../bronze data/full/bronze
uv run --project pipelines python -m benchline_pipelines --data-dir data/full silver
uv run --project pipelines python -m benchline_pipelines normalize-eval --llm --sample 200 --silver data/full/silver/nadac.parquet

# 3. Build the group map. Without --llm, unresolved items simply keep their old group and are flagged.
uv run --project pipelines python -m benchline_pipelines normalize --llm --max-llm 2000

# 4. Look at what a person should check
# open data/silver/needs_review.csv in a spreadsheet

# 5. Replay with the new groups into a FRESH database
uv run --project pipelines python -m benchline_pipelines replay --group-map data/silver/item_groups.parquet
```

Before any `--llm` run, check the first line it prints. It says whether calls go "through the gateway at ..." or
"directly at its provider". If you tested the gateway earlier in the same terminal, run
`unset BENCHLINE_LLM_API_BASE BENCHLINE_LLM_API_KEY` (or open a new tab), or the run will ask the gateway for a model it
does not have and fail with a bare `APIError`.

Step 5 needs an empty database: an NDC already stored keeps the group it was first stored under. After
changing groups, run `docker compose down -v` and load again.

Outputs in `data/silver/`: `item_groups.parquet` (one row per NDC with its group, method and review reason),
`needs_review.csv`, `normalize_report.json`. The model cache is `data/cache/llm.jsonl`.

## Limits you should know

- **Same ingredient is not the same drug.** Putting a brand and a generic under one ingredient makes them
  candidates for a comparison. Therapeutic equivalence needs an Orange Book rating, which is not used here.
  Brand and generic groups are kept apart and labelled `(BRAND)`.
- **Salts are merged.** `ATORVASTATIN CALCIUM` and `ATORVASTATIN` group together. Ester names are stripped only when they appear in real mismatches (`ACETONIDE`, `MEDOXOMIL`...); `FUROATE` is kept because fluticasone furoate and propionate are different drugs. Salt forms that differ in
  route or use of the same base are separated by form, not by salt.
- **Percent strengths** (`1% CREAM`) are kept as written. openFDA states them as mg per gram, so they are not
  cross-checked.
- **Evaluation bias.** Rules and model are scored on NDCs openFDA knows. The ones it does not know may be harder.
- **LiteLLM details to confirm.** The gateway config uses keys from LiteLLM's documentation. The image tag is
  `latest`; pin a release. Key-creation field names should be checked against the gateway's own Swagger page
  after any upgrade.
- **Privacy.** Only public product descriptions are sent to a provider; no visitor data is. The Privacy Policy says so.
