"""Shared request-local orchestration for JSON and live NDJSON responses."""

import asyncio
import json
import threading
import time
from contextvars import ContextVar

from fastapi.responses import StreamingResponse
from models.investigation import TraceEvent
from models.schemas import AnalysisDetail, RiskLevel


_sink = ContextVar("investigation_trace_sink", default=None)


def emit(event):
    sink = _sink.get()
    if sink:
        sink(event)


async def stage(phase, message, function, *args, threaded=True, **kwargs):
    emit(TraceEvent(sequence=0, phase=phase, message=message, elapsed_ms=0))
    if threaded:
        result = await asyncio.to_thread(function, *args, **kwargs)
    else:
        result = await function(*args, **kwargs)
    emit(TraceEvent(sequence=0, phase=phase, message=message + " Completed.", elapsed_ms=0))
    return result


async def investigate(verifier, text):
    investigation = await stage("investigation", "Investigate extracted claims.",
                                verifier.investigate, text, emit)
    details = [AnalysisDetail(
        category="Claim Verification",
        finding=f"{claim.verdict.title()}: '{claim.text[:100]}' - {claim.reasoning[:240]}",
        confidence=0.8 if claim.verdict in ("supported", "refuted") else 0.5,
        severity=RiskLevel.LOW if claim.verdict == "supported" else
        RiskLevel.HIGH if claim.verdict == "refuted" else RiskLevel.MEDIUM,
    ) for claim in investigation.claims]
    return details, investigation


async def analysis_response(operation, stream=False):
    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    loop_thread = threading.get_ident()
    stopped = threading.Event()
    lock = threading.Lock()
    trace = []
    started = time.perf_counter()

    def sink(event):
        # CancelledError bypasses the verifier's callback Exception handler, stopping
        # its next call. An already-running provider/local worker cannot be killed.
        with lock:
            if stopped.is_set():
                raise asyncio.CancelledError()
            item = event.model_copy(update={"sequence": len(trace) + 1,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)})
            trace.append(item)
            if stream:
                record = {"type": "trace", "event": item.model_dump(mode="json")}
                if threading.get_ident() == loop_thread:
                    queue.put_nowait(record)
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, record)

    async def run():
        token = _sink.set(sink)
        try:
            result = await operation()
            if result.investigation:
                result.investigation.trace = list(trace)
                result.recommended_action = result.investigation.recommended_action
                result.uncertainties.extend(result.investigation.uncertainties)
                for claim in result.investigation.claims:
                    result.uncertainties.extend(claim.uncertainties)
            if result.content_type != "text":
                result.uncertainties.append("Media checks do not verify origin, identity, or factual claims outside extracted text.")
                for provider in result.provenance:
                    result.uncertainties.extend(provider.limitations)
                    if provider.status != "completed":
                        result.uncertainties.append(provider.message)
                action = ("Do not rely on this media until its original source is independently verified."
                          if result.verdict == "suspicious" else
                          "Obtain the original media and verify its source; absence of indicators is not proof of authenticity.")
                result.recommended_action = action + (" " + result.recommended_action if result.investigation else "")
            result.uncertainties = list(dict.fromkeys(result.uncertainties))
            return result
        finally:
            stopped.set()
            _sink.reset(token)

    if not stream:
        return await run()

    async def records():
        async def produce():
            try:
                result = await run()
                await queue.put({"type": "result", "result": result.model_dump(mode="json")})
            except Exception:
                await queue.put({"type": "error", "message": "Analysis failed. Please retry."})

        task = asyncio.create_task(produce())
        try:
            while True:
                record = await queue.get()
                yield json.dumps(record, ensure_ascii=True) + "\n"
                if record["type"] != "trace":
                    break
        finally:
            stopped.set()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(records(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
