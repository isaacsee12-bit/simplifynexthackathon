# VerifyAI

## SimplifyNext Agentic AI Hackathon

VerifyAI is a bounded, evidence-seeking assistant for reviewing questionable text and media before acting or sharing. A React 18 / Vite dashboard streams the work of a FastAPI backend, shows claim-level evidence and uncertainty, and recommends a human verification step. Image, video, and audio observations remain separate from factual claim investigation. Results are review aids, not proof of authenticity.

**Submission focus:** a single agent that chooses a retrieval tool and query, observes evidence gaps or disagreement, adapts its next search, and concludes or abstains under explicit budgets. This is not a multi-agent system: extraction, planning, and assessment are structured calls within one controller, not independent collaborating agents.

## Architecture

```text
React dashboard -> POST /api/analyze/{text,image,video,audio}?stream=true
  -> validation -> request-local analysis_response orchestration
     -> local checks / media preparation / Gemini media assessment
     -> text or image OCR -> RAGVerifier.investigate
        extract -> plan -> retrieve -> assess -> adapt (bounded) -> conclude
  <- NDJSON trace records -> terminal result or sanitized error
  -> evidence excerpts, publisher links, coverage, uncertainties, next action
```

| Component | Implemented responsibility |
| --- | --- |
| [`rag_verifier.py`](backend/analyzers/rag_verifier.py) | Structured exact-span claim extraction, model-selected Wikipedia or DuckDuckGo query, snippet assessment, adaptive follow-up, deterministic evidence and verdict gates. |
| [`investigation.py`](backend/models/investigation.py) | Claim verdicts (`supported`, `refuted`, `uncertain`, `conflicting`), evidence IDs/URLs/excerpts/publishers/timestamps, trace, uncertainty, recommended action. |
| [`investigation_stream.py`](backend/core/investigation_stream.py) | Shared JSON/NDJSON execution, request-local trace sequencing and elapsed times, thread offloading, terminal errors and disconnect handling. |
| [`routers/`](backend/routers) | Text investigation and independent local-check toggles; image OCR investigation plus actual image assessment; sampled video and audio assessment. |
| [`Reconstruction.jsx`](webapp/src/Reconstruction.jsx) | Live activity, cancellation, stale-request guards, evidence reports, media provenance, and local-only API settings. [`analysisStream.js`](webapp/src/utils/analysisStream.js) handles chunked UTF-8 NDJSON and rejects incomplete streams. |

### Agent Decisions And Bounds

1. Consider at most 12,000 input characters and three claims. Model-extracted claims must be exact input spans; duplicates and paraphrases are rejected. If extraction is unavailable, exact sentences are used with an explicit non-validated-extraction warning.
2. Choose `wikipedia` search or `duckduckgo` instant answers and a focused query. Retrieve snippets, not full articles. Only fixed HTTPS API endpoints are fetched; redirects are blocked and responses are capped at 256,000 bytes. Model-provided source URLs are never fetched.
3. Accept only allowlisted HTTPS publisher URLs, reject snippets matching a conservative instruction pattern, deduplicate URLs, and check cited evidence IDs and verbatim quotes of at least 20 characters. Two distinct publisher identities are required for a decisive verdict; opposing stances produce `conflicting`. Reported assessment uncertainties prevent an otherwise decisive verdict. The instruction pattern is not a complete injection detector.
4. If evidence remains insufficient or conflicting, use the assessment's follow-up tool/query; repeated plans are replaced with an alternative-tool query. Each claim gets at most two retrieval rounds. Failures and exhausted budgets retain uncertainty rather than inventing evidence.
5. Share a cap of 16 external calls and a 25-second investigation wait budget, with at most four seconds per call. These bounds cover extraction, planning, retrieval, and assessment, not upload time or the entire multimodal request. A later claim can run out of budget. Running SDK threads cannot be forcibly killed; late results are discarded.

Without a configured Gemini client, the investigator reports uncertain sentence candidates and performs no retrieval or semantic assessment. Trace events are operational summaries, not private model reasoning. Cancellation stops later stages/callback-driven investigation work, but cannot recall submitted data or stop an already-running provider/local worker. Proxy buffering can delay visible streaming.

### Originality

The contribution is the integration of adaptive snippet investigation, code-enforced corroboration and abstention, and request-local streaming into a multimodal review workflow. It is more than a single prompt with a score: the next retrieval depends on the observed evidence, and application code checks evidence structure before aggregating a verdict. It uses existing Gemini models, public retrieval APIs, and local analysis libraries; it does not introduce a new foundation model, prove semantic truth, or claim novel multi-agent coordination.

## Measured Benchmark

The [benchmark report](docs/benchmark-results.md) records 11 deterministic, synthetic, one-claim fixtures run through the production investigator with only Gemini generation and HTTP retrieval boundaries replaced. Fictional Lumen observatory snippets are not real publisher content. Socket access is blocked. **These numbers measure orchestration policy, not real-world factual accuracy, live Gemini performance, or media detection quality.**

| Recorded metric | Investigation | Single-source/no-follow-up baseline |
| --- | ---: | ---: |
| Exact fixture verdict accuracy | 11/11 (100%) | 8/11 (72.7%) |
| Abstention recall on expected-abstention cases | 8/8 (100%) | 5/8 (62.5%) |
| Structurally valid decisive citations | 6/6 (100%) | 6/6 (100%) |
| Decisive verdicts with two validated publishers | 3/3 (100%) | 0/6 (0%) |
| Adaptive follow-up coverage | 11/11 (100%) | 0/11 (0%) |
| Total external boundary calls | 60 | 41 |
| Maximum calls in a case | 6 | 4 |

The improvement is three additional correct fixture labels, or 27.3 percentage points, at 19 extra mocked calls. The baseline is a separate straight-line controller using the same provider methods and instruction filter, with exactly one retrieval and at most one source assessment; it is not the previous shipped implementation. Fixtures favor the investigation's corroboration policy. Two `.venv/Scripts/python.exe` runs produced identical verdicts and counts on Windows 11/Python 3.12.11 (`google-genai 1.46.0`, `pydantic 2.8.0`). Second-run maximum/summed case runtimes were 2.019/12.552 ms versus 0.512/1.712 ms. These exclude imports/setup and measure mock overhead, not network latency or a production SLA; the baseline also omits production thread/trace overhead. See the report for definitions and limitations.

**Originally exposed injection failure, now fixed for these fixtures:** the first benchmark returned `supported` for the obeyed-injection case, yielding 10/11 investigation accuracy. `RAGVerifier.INSTRUCTION_PATTERN` now rejects both unchanged injection fixtures before assessment, returning `uncertain` in both policies. This conservative rule is not complete injection protection. Citation validity is not semantic entailment, publisher identity is not proof of editorial independence, and these runs do not measure live-model injection resistance.

Use `--check` to exit 1 on any investigation verdict mismatch; baseline errors remain informational. Without it, mismatches are measurements only. Both measured runs passed `--check`; an in-memory label-change probe verified its failure path and JSON output. The report includes a two-call abstention probe, but no multi-claim saturation study, live-search evaluation, multilingual evaluation, calibrated confidence study, or production-scale/load test. No live provider verification or deployed smoke-test result is claimed here.

## Local Setup

Use Python 3.12 and Node.js 22 (the CI and Docker versions). Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

Create a root `.env` using [`.env.example`](.env.example) as a reference, or configure backend environment variables directly:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Backend-only Gemini API secret. The example intentionally contains no key. |
| `GEMINI_MODEL` | Configurable model ID; defaults to `gemini-3.5-flash`. |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins; defaults to localhost and 127.0.0.1 on port 5173. Same-origin deployments need no override. |

Model availability depends on your account and the provider's current offerings. If the default is unavailable, set `GEMINI_MODEL` to a model your account can access. Never put the API key in a `VITE_` variable or frontend source: Vite variables are embedded in the public browser bundle.

The backend uses Google's official `google-genai` Python SDK for actual image, sampled-video-frame, and audio requests, plus structured claim investigation. Text-route heuristics run locally with `use_llm=False`; model use is in the investigator. It loads `.env` from the repository root (or `backend/.env`); existing server environment variables take precedence. Without a key, local supplementary checks still run, but Gemini media analysis is explicitly `not_configured` and the media verdict is inconclusive. Retrieved context alone is not counted as a verified claim.

Start the backend from the root:

```bash
python -m uvicorn app:app --reload --port 8000
```

The root `app.py` adapts imports to the existing backend without changing its local module layout. Running `python main.py` from `backend/` also remains supported. API docs are at `http://localhost:8000/docs`.

In a second terminal, start the frontend from the root:

```bash
npm --prefix webapp ci
npm --prefix webapp run dev
```

Open `http://localhost:5173`. The frontend defaults to same-origin `/api`; Vite proxies `/api` to `http://localhost:8000` during development. `VITE_API_URL` is an optional public API base URL override and must include `/api`. No override is needed for the combined Vercel deployment.

For local production-style serving, run `npm --prefix webapp run build` and start the backend. FastAPI serves `webapp/dist` locally, including the SPA fallback. Vite's development proxy does not apply to `vite preview`.

## Local API Settings

Open `http://localhost:5173` using the Vite development server, or use the frontend served by the local backend. Select **API** in the navigation. Settings are enabled only for `localhost`, `127.0.0.1`, and `[::1]`; deployed and LAN hostnames send no settings requests.

Run the backend with a single Uvicorn worker, for example `python -m uvicorn app:app --port 8000 --workers 1`. The backend must implement `/api/settings/gemini`. If settings are unavailable, check that the backend is running and same-origin `/api` routing is working, then select **Retry loading status**. Standalone `vite preview` does not provide the development proxy.

Enter a Gemini API key and model (default `gemini-3.5-flash`), then select **Save settings**. Leaving the key blank keeps the existing key, allowing model-only updates. The password field is cleared after a successful save; only configured status and model are retrieved, never the key. The frontend uses transient React state, not browser storage.

Select **Test Gemini Connection** after saving. **Configured** means only that a key is present. The test makes an actual minimal text-generation request to the saved model, reports provider/model/status/duration, and may incur provider usage. A successful connection does not prove image/audio support or forensic accuracy. Unsaved input is not used. Without a key, the test returns `not_configured` without contacting Google. The test route is `POST /api/settings/gemini/test` and has the same loopback-client, loopback-host/origin, custom-header, and non-Vercel restrictions as the other settings routes. Public deployments cannot run it.

**Clear session key** disables Gemini for the current backend session. It does not modify `.env` files or environment variables; those values are loaded again on restart. Session overrides live only in backend memory until restart (including development reloads). Use one worker so requests share the same session settings.

Settings requests always use same-origin `/api/settings/gemini`, ignore `VITE_API_URL`, and include `X-VerifyAI-Settings: 1`. Redirects are blocked to avoid forwarding the key elsewhere. Keep the local server private and never put secrets in frontend environment variables.

## Optional Vision

The base installation retains OpenCV, Pillow, NumPy, pytesseract, librosa, soundfile, and scikit-learn. The heavyweight neural image detector is optional:

```bash
python -m pip install -r backend/requirements-vision.txt
```

This includes the base requirements plus PyTorch, torchvision, and transformers. Locally, when installed, the image analyzer loads `umm-maybe/AI-image-detector` at startup and may download model weights. Allow sufficient disk space, memory, and startup time. Without these dependencies, image analysis uses the remaining forensic heuristics.

OCR additionally requires the Tesseract system executable on `PATH`; installing the `pytesseract` Python wrapper alone is not sufficient.

## Docker

```bash
docker build -t verifyai .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env verifyai
```

Open `http://localhost:8000`. The multi-stage image uses Node 22 with `npm ci`, Python 3.12 with root `requirements.txt`, and one Uvicorn worker. It serves the built `webapp/dist` from FastAPI. Omit `--env-file .env` for an unconfigured run. Secrets are supplied at runtime, not baked into the image; `.dockerignore` preserves `.env.example` but excludes actual environment files. The base image does not install Tesseract or optional neural vision dependencies. Container networking may make the backend's loopback-only settings guard reject browser settings requests; use runtime environment variables rather than weakening that guard.

## Demo Script

This is a suggested five-minute walkthrough, not a claim that a live demo was verified. Start the two local servers above; use non-sensitive sample media you have permission to process.

1. **0:00, scope and settings.** Open **API** on localhost. Show configured status and the selected model. If authorized, save a key/model and optionally select **Test Gemini Connection**, explaining that this incurs a real text request and does not validate media capability. Do not expose the key on screen.
2. **0:45, investigate text.** Select Text and enter `The Moon orbits Earth.` Select **Analyze now**. Explain the live plan/act/observe/adapt/conclude events. Review the actual returned claims, evidence excerpts, publisher links, uncertainty, and next action. Do not promise a `supported` outcome: sparse snippets, timeouts, or a single publisher should leave the result uncertain.
3. **2:00, show repeatable evidence.** Run `python backend/tests/benchmark_investigation.py --check` (on Windows, use `.venv/Scripts/python.exe` if not activated). Compare 11/11 investigation labels with 8/11 for the baseline and 60 versus 41 calls. Show how the originally failing injection fixture now abstains because its snippets are rejected before assessment, while explaining the filter's limits. This synthetic CLI benchmark is separate from the live UI; it does not seed UI results.
4. **3:00, preserve multimodal coverage.** Upload a small image with readable text, a short video, and a short WAV in their respective modes. For image OCR, show either extracted-text investigation or the explicit unavailable/no-readable-text limitation. For video, inspect timestamped sampled-frame coverage, not full-video claims. For audio, show the opening-sample duration and unverified speaker identity/spoken facts.
5. **4:30, uncertainty and cancellation.** Start another analysis and select **Cancel analysis** while running. Explain in-flight work may continue. Clear the session key and rerun text or media to demonstrate explicit uncertainty/`not_configured`, not a fabricated successful verdict. End with the recommendation to review original full sources before consequential use.

## API Contract

`POST /api/analyze/text` accepts JSON with `text` (nonblank, at most 12,000 characters) and optional independent booleans `check_ai_generated`, `check_scam`, and `check_claims` (default true). Media endpoints accept multipart field `file`: image up to 15 MiB, video 50 MiB, audio 20 MiB. MIME/empty/size validation runs before streaming; these limits do not override hosting-platform limits.

Without `?stream=true`, endpoints return the ordinary JSON `AnalysisResult`. With it, the response is `application/x-ndjson`: zero or more `{"type":"trace","event":...}` records followed by one `{"type":"result","result":...}` or sanitized `{"type":"error","message":...}` record. Input validation failures remain HTTP JSON errors. Evidence returned per claim includes retrieved snippets plus `cited_quotes` and `stances` from accepted assessments. These are separate, deduplicated lists, not paired quote/stance records; uncited evidence can have empty lists, and verbatim quotes do not prove semantic support. `claims_verified` is a legacy count of `supported` labels, not an independently established truth count. See `/docs` for schemas and `/api/health` for service status.

## Vercel Deployment

1. Import the repository as a Vercel project with the **repository root** as its Root Directory, not `webapp/` or `backend/`.
2. Use the native **FastAPI** framework. `vercel.json` selects it, root `app.py` exports `app`, and `.python-version` pins Python 3.12. Root `requirements.txt` lists dependencies directly because Vercel's dependency discovery failed to parse the nested requirements include. Keep it aligned with `backend/requirements.txt`; the regression suite checks this.
3. Add `GEMINI_API_KEY` and, if needed, `GEMINI_MODEL` as backend environment variables in Vercel for the appropriate deployment environments.
4. Leave Install Command and Output Directory overrides unset. The configured Build Command is `npm --prefix webapp ci && npm --prefix webapp run build -- --outDir ../public --emptyOutDir`.
5. Deploy. Vercel serves the generated root `public/` files through its CDN, while API requests run in the native FastAPI function. FastAPI uses `public/index.html` for unmatched frontend routes and returns HTTP 404 for unknown API paths. It does not mount `public/`.

The generated `public/` directory is ignored by Git. There are no legacy `builds` entries or static-only output settings. See the [native FastAPI deployment documentation](https://vercel.com/docs/frameworks/backend/fastapi).

### Media Limitations

- Vercel Functions have a **4.5 MB request body limit**, including multipart overhead. The backend's larger upload setting does not override this limit. Large image, audio, or video uploads require a different upload/processing architecture.
- The standard deployment does not install the Tesseract executable, so OCR is unavailable even though the Python wrapper remains installed.
- The optional neural image model is not installed by the base requirements. When `VERCEL` is set, model initialization is skipped even if its dependencies are present, preventing startup downloads.
- Deployed image analysis is therefore **not equivalent to a fully configured local vision installation**. Gemini media requests work when configured and within platform limits; supplementary OCR and the optional local neural model remain absent.
- Media dependencies remain substantial. Check the function bundle size, memory, duration, and codec support for the selected Vercel runtime and plan. Longer audio/video processing may require a dedicated worker or backend.
- Temporary media files and the audio JIT cache use writable system temporary storage. This storage is ephemeral, not persistent.

## Analysis Overview

- **Text:** Local statistical and phishing indicators, with bounded retrieved claim investigation when configured. Uncertain/conflicting claims do not enter the legacy indicator score. There is no calibrated authorship or authenticity probability.
- **Images:** Gemini receives one actual JPEG preview, resized to at most 1536 pixels on either side. Only the first frame of animated input is used; source metadata is not sent. Metadata, compression, noise, frequency, and face-related heuristics, the optional local neural detector, and OCR remain supplementary checks. OCR text is not a substitute for the image request.
- **Video:** Gemini receives up to 15 actual JPEG frames (at most 768 pixels per side) with explicit timestamps. The same bounded sample is reused for local temporal checks; sampling spans the first through last source frame when decoding succeeds. The report lists prepared timestamps, source frame count, duration, and whether a request was attempted. **No video audio, continuous motion, or unsampled frames are analyzed by Gemini.** Decode failures can reduce coverage or prevent the request entirely.
- **Audio:** Gemini receives real mono PCM WAV audio at 22050 Hz, reusing the decoded opening sample capped at 60 seconds. Spectral, signal, and container checks remain supplementary. Coverage reports the sample duration, not an invented full-file duration. The remainder and speaker identity are not verified. Unsupported codecs or failed decoding produce `insufficient_media`, never a text-only imitation of audio analysis.
- **Verdicts:** Media returns `suspicious`, `no_indicators`, or `inconclusive`. `no_indicators` applies only to supplied coverage and is not an authenticity claim. Successful provider responses are schema-validated and must include limitations; a non-inconclusive verdict also requires observations. Provider output remains fallible even when valid.
- **Scoring:** Media `trust_score`, `risk_level`, and `is_authentic` are intentionally `null`: neither Gemini observations nor local heuristics justify calibrated authenticity percentages. The frontend displays observations and limitations instead. The legacy text indicator score, when evidence exists, is explicitly uncalibrated; text checks that produce no evidence are also inconclusive. Provider/retrieval errors do not contribute to scores, risk escalation, or flagged claims. Local legacy findings retain heuristic severity/confidence fields for inspection, not as calibrated conclusions.

### Provenance and Failures

Media results include `provenance` entries for **Google Gemini** and **Local supplementary checks**. Each includes `provider`, `model` (null for local checks), `status`, `duration_ms`, structured `coverage`, `message`, `verdict`, `observations`, and `limitations`. Coverage distinguishes prepared media from `submitted` (a provider request was attempted, not a guarantee that the provider received or analyzed it). `completed` means a valid response, not established authenticity. Local status is conservatively `partial` because these checks cannot provide full verification.

Missing credentials, insufficient decodable media, timeouts, authentication/access errors, quota errors, unavailable models, provider failures, safety blocks, and malformed/truncated output are separate statuses: `not_configured`, `insufficient_media`, `timeout`, `authentication_error`, `quota_exceeded`, `model_unavailable`, `provider_error`, `blocked`, and `invalid_response`. They produce an inconclusive verdict, not suspicious content findings. Error bodies and secrets are not returned or logged by the media/connection request handler. Check the saved model, permissions, and quota, then retry; there is no silent text-only fallback or automatic application retry.

Blocking SDK and local analyzer work is offloaded from FastAPI's event loop. Gemini HTTP requests have the existing 30-second timeout plus a 35-second application wait limit; an already running SDK thread cannot be forcibly stopped when that wait expires. Local decoding/heuristics are not covered by the provider timeout. A plain SDK response schema with independent Pydantic validation is tested against installed `google-genai 1.46.0` and `pydantic 2.8.0`; no dependency upgrade is required.

### Privacy And Costs

With Gemini configured, submitted text or image OCR text, claims, queries, and retrieved excerpts can be sent to Google; prepared media is also sent to Google. Search queries go to Wikipedia and/or DuckDuckGo, and opening a source link contacts that publisher. Provider retention and usage policies apply. Do not submit sensitive content without permission. The app does not persist uploads as a feature, but temporary decoding files and in-memory payloads exist during processing; this is not a secure-erasure guarantee. Session keys remain backend-memory-only, are never returned, and reset on restart. Keep local settings private and use one worker.

Gemini requests, including connection tests and adaptive follow-ups, may incur account-specific token/media charges. Retrieval has availability/rate constraints; hosting and optional model downloads also have resource costs. The 16-call investigation cap includes retrieval as well as model calls; separate media and connection-test requests are outside it. No dollar-per-analysis or free-service guarantee has been measured. CORS defaults to explicit local origins, but CORS is not access control: analysis routes have no user authentication or application rate limiting. Do not expose a paid-key-backed instance publicly without access controls, abuse limits, and an appropriate data policy.

## Verification

From the repository root in a Python 3.12 environment with Node 22:

```bash
python -m pip install -r requirements.txt
npm --prefix webapp ci
npm --prefix webapp test
npm --prefix webapp run build -- --outDir ../public --emptyOutDir
python -m unittest discover -s backend/tests -p "test_*.py"
python backend/tests/benchmark_investigation.py --check
```

These are the steps in [CI](.github/workflows/ci.yml), including the benchmark `--check` gate. Build `public` before backend discovery because API routing tests require that artifact. All `test_*.py` suites are discovered, including investigation, SDK serialization, audio regression, and streaming tests. The local suite passed 75 backend tests. Do not use Python `-O`, which disables harness assertions. For machine-readable benchmark output, run `python backend/tests/benchmark_investigation.py --json --check`.

For local production-style serving, additionally build the local static directory:

```bash
npm --prefix webapp run build
python -m uvicorn app:app --port 8000 --workers 1
```

The backend suite exercises health, text/RAG, media uploads, frontend routing, settings/connection guards, investigation validation/bounds, JSON/stream parity, live trace emission, cancellation, and sanitized errors. Media tests inspect decodable image/audio payloads, bounded timestamped video frames, schema validation, failure states, null confidence fields, off-event-loop SDK work, and installed-SDK serialization with transport mocked. Frontend Node tests exercise stream parsing, chunk boundaries, malformed/incomplete records, and cancellation; they are not a browser end-to-end or visual/mobile audit. Gemini and retrieval are mocked for offline tests; dependency installation itself needs package-registry access. Passing tests does not verify account/model access, live retrieval quality, injection resistance, deployment streaming, or platform limits.

A separate [browser smoke test](webapp/tests/browser-smoke.mjs) passed in real headless Chromium at 1440x1000 and 390x844: live events before completion, evidence reports, cancellation, all input modes, settings, and no horizontal overflow or browser errors. It uses synthetic HTTP responses, not live analysis. To rerun, install Playwright outside the application, set `PLAYWRIGHT_MODULE` to its `index.mjs` path and `PLAYWRIGHT_BROWSERS_PATH` to its Chromium cache, then run `node webapp/tests/browser-smoke.mjs`. The script starts and stops its own Vite and mock servers. Mobile coverage is emulated Chromium, not a physical device.

The review also fixed a reproducible Windows native crash in librosa's pitch interpolation path, retaining STFT-based pitch checks and the original sampled audio payload. Frontend dependency audit reports zero known vulnerabilities after the Vite 6.4.3 update. Docker was not built locally because its daemon was unavailable; live account/model access and deployed streaming still require a pre-demo smoke check.
