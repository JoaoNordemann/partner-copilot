"""Measure the real API through loopback HTTP and persist each response."""

import argparse
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter, sleep

from benchmark_gpu_precision import append, cases


def serve(log_path):
    import uvicorn

    from partner_copilot.api import create_app
    from partner_copilot.api_runtime import Resources

    class ObservedResources(Resources):
        def start(self):
            super().start()
            if self.llm is not None:
                original = self.llm.generate

                def timed(prompt):
                    start = perf_counter()
                    try:
                        return original(prompt)
                    finally:
                        append(log_path, event="llm_interval", started=start, ended=perf_counter())

                self.llm.generate = timed

    uvicorn.run(create_app(resources_factory=ObservedResources), host="127.0.0.1", port=8765)


def measure(path):
    import httpx

    endpoint = "http://127.0.0.1:8765"
    rows = {r["question_id"]: r for r in cases()["contaminado"]}
    trace = path.with_name("api-generation-intervals.jsonl")
    server_log = path.with_name("api-server.log")
    append(path, event="configuration", api_request_timeout_s=60, generation_slots=1)
    with (
        server_log.open("x", encoding="utf-8") as log,
        subprocess.Popen(
            [sys.executable, __file__, "serve", str(trace)], stdout=log, stderr=log
        ) as server,
    ):
        try:
            deadline = perf_counter() + 240
            while perf_counter() < deadline and server.poll() is None:
                try:
                    response = httpx.get(endpoint + "/health", timeout=2)
                    append(path, event="health", status=response.status_code, body=response.json())
                    if response.is_success:
                        break
                    raise RuntimeError("API startup reported an unhealthy component")
                except httpx.TransportError:
                    sleep(1)
            else:
                raise RuntimeError("API did not become healthy")

            def request(identifier, group, barrier=None):
                row = rows[identifier]
                scope = row["filtros"].copy()
                body = {
                    "restaurant_id": scope.pop("restaurant_id"),
                    "question": row["pergunta"],
                    "filters": scope,
                    "k": 8,
                }
                with httpx.Client(timeout=75) as client:
                    if barrier:
                        barrier.wait(timeout=10)
                    started = perf_counter()
                    try:
                        reply = client.post(endpoint + "/ask", json=body)
                        record = {"http_status": reply.status_code, "response": reply.json()}
                    except (httpx.HTTPError, ValueError) as exc:
                        record = {"client_error": type(exc).__name__}
                    append(
                        path,
                        event="http",
                        group=group,
                        id=identifier,
                        started=started,
                        seconds=perf_counter() - started,
                        **record,
                    )

            for identifier in ("q22", "q23"):
                request(identifier, "warmup")
            for number in (*range(1, 13), *range(14, 22)):
                request(f"q{number:02}", "sequential")
            barrier = threading.Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(request, identifier, "concurrent", barrier)
                    for identifier in ("q24", "q25")
                ]
                for future in futures:
                    future.result()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "measure"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    if args.mode == "serve":
        serve(args.output)
    else:
        args.output.touch(exist_ok=False)
        measure(args.output)


if __name__ == "__main__":
    main()
