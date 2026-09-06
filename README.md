# VerifyAI

"See through the lies."

VerifyAI is a multimodal content-verification demo with a FastAPI backend and a React 18 / Vite dashboard. It combines text, image, video, and audio analysis with risk scores and explanations. Results are indicators for review, not proof of authenticity.

## Local Setup

Use Python 3.12 and Node.js 20 or newer. Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.

Configure backend environment variables using the root `.env.example` as a reference:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Backend-only Gemini API secret. The example intentionally contains no key. |
| `GEMINI_MODEL` | Configurable model ID; defaults to `gemini-3.8-flash`. |

Model availability depends on your account and the provider's current offerings. If the default is unavailable, set `GEMINI_MODEL` to a model your account can access. Never put the API key in a `VITE_` variable or frontend source: Vite variables are embedded in the public browser bundle.

The backend uses Google's official `google-genai` Python SDK for text analysis and retrieved claim verification. It loads `.env` from the repository root (or `backend/.env`); existing server environment variables take precedence. Without a key, text heuristics still run and Gemini analysis is reported as unavailable. Retrieved context alone is not counted as a verified claim.

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

Enter a Gemini API key and model (default `gemini-3.8-flash`), then select **Save settings**. Leaving the key blank keeps the existing key, allowing model-only updates. The password field is cleared after a successful save; only configured status and model are retrieved, never the key. The frontend uses transient React state, not browser storage.

**Clear session key** disables Gemini for the current backend session. It does not modify `.env` files or environment variables; those values are loaded again on restart. Session overrides live only in backend memory until restart (including development reloads). Use one worker so requests share the same session settings.

Settings requests always use same-origin `/api/settings/gemini`, ignore `VITE_API_URL`, and include `X-VerifyAI-Settings: 1`. Redirects are blocked to avoid forwarding the key elsewhere. Keep the local server private and never put secrets in frontend environment variables.

## Optional Vision

The base installation retains OpenCV, Pillow, NumPy, pytesseract, librosa, soundfile, and scikit-learn. The heavyweight neural image detector is optional:

```bash
python -m pip install -r backend/requirements-vision.txt
```

This includes the base requirements plus PyTorch, torchvision, and transformers. Locally, when installed, the image analyzer loads `umm-maybe/AI-image-detector` at startup and may download model weights. Allow sufficient disk space, memory, and startup time. Without these dependencies, image analysis uses the remaining forensic heuristics.

OCR additionally requires the Tesseract system executable on `PATH`; installing the `pytesseract` Python wrapper alone is not sufficient.

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
- Deployed image analysis is therefore **not equivalent to a fully configured local vision installation**. Heuristic media analysis remains, but OCR and the optional neural model are absent.
- Media dependencies remain substantial. Check the function bundle size, memory, duration, and codec support for the selected Vercel runtime and plan. Longer audio/video processing may require a dedicated worker or backend.
- Temporary media files and the audio JIT cache use writable system temporary storage. This storage is ephemeral, not persistent.

## Analysis Overview

- **Text:** Statistical and phishing indicators, with provider-backed analysis and retrieved claim verification when configured.
- **Images:** Metadata, compression, noise, frequency, and face-related heuristics, plus the optional local neural detector and OCR when available.
- **Video:** Sampled-frame and temporal analysis, subject to runtime and codec limitations.
- **Audio:** Spectral and signal heuristics through the media processing dependencies.
- **Scoring:** Findings are combined into risk levels, trust scores, and explanations. These are demonstration signals, not calibrated guarantees or forensic conclusions.

## Verification

```bash
python -c "from app import app; print(app.title)"
npm --prefix webapp run build -- --outDir ../public --emptyOutDir
python -m unittest discover -s backend/tests -p test_api.py
```

The regression suite exercises health, text and RAG responses, all three media upload endpoints, and frontend routing. Gemini and web retrieval are mocked so tests require no credentials or network. A live Gemini request and a deployed Vercel smoke test are still needed to verify account/model access and platform limits.
