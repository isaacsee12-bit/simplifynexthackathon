# Offline Investigation Benchmark

## Scope

This is a deterministic synthetic orchestration benchmark, **not a measurement of real-world factual accuracy, retrieval quality, or Gemini accuracy**. All claims concern a fictional Lumen observatory. Publisher URLs identify synthetic fixture sources; no assertion is made that those pages exist or contain these excerpts.

The 11 cases execute the actual `RAGVerifier.investigate` implementation. Only `gemini_client.models.generate_content` and `_fetch_json` are replaced. Claim extraction prompts, planning prompts, structured response validation, Wikipedia/DDG adapters, evidence filtering, URL deduplication, publisher independence, assessment validation, adaptive rounds, call accounting, trace emission, and verdict aggregation remain production code. Socket connections are blocked and checked. Final investigation results are never mocked.

Model extraction and semantic stance judgments are scripted inputs. The extraction case includes an opinion and question in the input and returns one invalid paraphrase plus a duplicated exact claim, testing exact-span rejection and deduplication, not natural-language extraction ability. Injection cases retain their original ignored/obeyed provider scripts and expected labels; the current instruction filter rejects their snippets before either script reaches assessment.

## Repeatable CLI

From the repository root, with backend dependencies installed:

```powershell
python backend/tests/benchmark_investigation.py --check
python backend/tests/benchmark_investigation.py --json --check
```

The measured runs used the existing repository virtual environment, without changing dependencies:

```powershell
.venv/Scripts/python.exe backend/tests/benchmark_investigation.py --check
```

Append `--json` for full per-case metrics and the budget probe. Initial dependency provisioning may access the package registry; the benchmark itself needs no network or API key. Do not use Python's `-O` option: harness invariants use assertions. With `--check`, any investigation verdict mismatch exits 1 and lists case IDs on stderr; expected baseline weaknesses remain informational. Without it, verdict mismatches are measurements only. Broken harness invariants always fail. CI runs the benchmark with `--check`.

## Baseline

The comparison is a deliberately simple **single-source/no-follow-up policy**, not the previous shipped implementation. Its own straight-line controller calls the production extraction, planning, retrieval adapter, and assessment methods through the same mocked boundaries, but does not call `investigate`. It retrieves exactly once and assesses at most the first accepted source. It applies the same publisher allowlist, minimum excerpt length, instruction-snippet rejection, exact claim span checks, and citation ID/verbatim-quote checks. It reports the first citation's stance unless assessment uncertainty requires abstention. It does not require independent corroboration or resolve conflict. Exactly one actual retrieval and at most four boundary calls are asserted, independent of whether an assessment is skipped.

The old four-call-budget technique was removed: a rejected first source can skip assessment and leave room for a second retrieval. The new baseline has no retrieval loop and no production thread/trace/budget controller overhead, so runtime is not an apples-to-apples performance comparison. Its intentionally limited checks are not a production replacement. All fixtures start with at most one unique Wikipedia result, so the baseline does not receive the second publisher and cannot recognize a later contradiction. These choices favor the investigation's independence policy and should not be generalized to other baselines.

## Measurements

Recorded on Windows 11 x64 (build 26200), Python 3.12.11, 2026-09-06, using `.venv/Scripts/python.exe`: `google-genai 1.46.0`, `pydantic 2.8.0`, `python-dotenv 1.0.1`. Two runs with `--check` produced identical verdicts, counts, and coverage; elapsed times varied. The table uses the second run. Dependency loading, imports, fixture loading, and mock setup are excluded from timed regions; investigation thread creation and orchestration are included. Other verification commands ran concurrently, so timings are illustrative, not isolated performance samples.

| Metric | Investigation | Single-source baseline |
| --- | ---: | ---: |
| Exact verdict accuracy | 11/11 (100%) | 8/11 (72.7%) |
| Decisive-verdict citation validity | 6/6 (100%) | 6/6 (100%) |
| Decisive verdicts with two validated publishers | 3/3 (100%) | 0/6 (0%) |
| Abstention accuracy on expected-abstention cases | 8/8 (100%) | 5/8 (62.5%) |
| Adaptive follow-up coverage | 11/11 (100%) | 0/11 (0%) |
| Maximum external calls per case | 6 | 4 |
| Total external calls across cases | 60 | 41 |
| Maximum measured case runtime | 2.019 ms | 0.512 ms |
| Sum of measured case runtimes | 12.552 ms | 1.712 ms |

First-run maximum/summed runtimes: investigation 2.278/13.806 ms; baseline 0.432/1.499 ms.

Definitions:

- Verdict accuracy is exact equality with the fixture's expected label; `conflicting` is distinct from `uncertain`.
- Citation validity audits public returned evidence: unique `(evidence_id, cited_quote)` pairs on sources whose `stances` include the decisive verdict. A valid quote contains at least 20 characters, is a verbatim excerpt substring, and has an allowlisted source URL. Repeated quotes count once. `Evidence.cited_quotes` retains accepted quote history and `Evidence.stances` holds effective source stances; explicit reassessment replaces prior stances, while omitted sources retain their previous assessment. These are separate lists, not paired quote/stance records. These fixtures have unambiguous decisive source stances. This is structural validity, not semantic entailment. Rejected hallucinated assessments are additionally checked to leave both lists empty.
- Independent decisive verdicts additionally require at least two publisher identities among those valid citations. These synthetic identities do not establish editorial independence or rule out syndication.
- Abstention accuracy is the fraction of eight expected `uncertain`/`conflicting` cases that return either nondecisive label. It is abstention recall, not precision or overall binary classification accuracy. All three expected-decisive cases were decisive in both policies.
- Follow-up coverage requires two actual retrieval calls with different `(tool, query)` pairs and an adaptation trace. All 11 fixtures require a second round under the investigation's two-publisher policy. This measures execution, not whether a query is semantically useful.
- External calls include extraction, planning, retrieval, and assessment; investigation trace counts are cross-checked against actual boundary calls and the configured cap. Baseline calls are counted directly at the boundaries. A separate two-call budget probe returned `uncertain` after exactly two calls. The default cap is 16; these one-claim fixtures do not saturate it.

## Per-Case Results

| Case | Expected | Investigation | Baseline | Calls, investigation / baseline |
| --- | --- | --- | --- | ---: |
| Supported | supported | supported | supported | 6 / 4 |
| Refuted | refuted | refuted | refuted | 6 / 4 |
| Irrelevant snippets | uncertain | uncertain | uncertain | 6 / 4 |
| Missing evidence | uncertain | uncertain | uncertain | 4 / 3 |
| Single publisher, distinct URLs | uncertain | uncertain | supported | 6 / 4 |
| Duplicated sources | uncertain | uncertain | supported | 6 / 4 |
| Conflicting sources | conflicting | conflicting | supported | 6 / 4 |
| Hallucinated quotes | uncertain | uncertain | uncertain | 6 / 4 |
| Prompt injection ignored by provider | uncertain | uncertain | uncertain | 4 / 3 |
| Prompt injection obeyed by provider | uncertain | uncertain | uncertain | 4 / 3 |
| Simple claim extraction | supported | supported | supported | 6 / 4 |

## Findings And Limits

The investigation improves fixture verdict accuracy by 3/11 cases (27.3 percentage points), specifically publisher duplication and conflict, at 19 extra mocked calls across the suite. It rejects fabricated quotations and retains abstention on irrelevant or missing evidence given the scripted model responses.

**Originally exposed injection failure, now fixed for these fixtures:** the original benchmark measured 10/11 investigation accuracy because malicious instruction quotes labeled `supported` by the provider passed structural gates. The engine's subsequently added `RAGVerifier.INSTRUCTION_PATTERN` now rejects both injection fixtures before assessment, producing `uncertain`; the benchmark asserts no accepted evidence and no assessment calls for these cases. Labels and source text were not changed. The baseline receives the same filter, improving from 7/11 to 8/11 as well. The conservative pattern is not a complete injection detector: obfuscated instructions, false positives, and semantically wrong but structurally valid citations remain risks. Citation checks cannot establish truth, and neither injection fixture now tests a live model's resistance.

The fixture suite is small, manually authored, and policy-oriented. It does not test live search coverage, real publisher content, source authenticity, multilingual inputs, calibrated confidence, multi-claim budget saturation, full articles, or real model resistance to injection. Runtime is local mock overhead, not network latency or a production SLA. Retrieval timestamps and runtimes are nondeterministic; verdicts and call counts are deterministic. The two-call probe tests call-budget abstention, not a wall-clock timeout guarantee.

The full backend suite was also run unchanged from the repository root:

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests -p "test_*.py"
```

Final review validation: **75 backend tests passed**, including real SDK request serialization, evidence reassessment withdrawal/conflict resolution, request-local client isolation, and the audio crash regression. Benchmark verdicts and counts remained unchanged after these fixes. Existing deprecation/media-decoder warnings were emitted. Both recorded benchmark runs passed `--check` and the two-call budget probe. An in-memory expected-label mutation confirmed `--check` returns 1, reports the case on stderr, and preserves parseable JSON stdout; fixture files were not changed for that probe.
