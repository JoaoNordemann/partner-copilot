"""Start the CPU MVP API plus Gradio at /demo; build the RAG index on first use."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from partner_copilot.api_models import APISettings  # noqa: E402


class LocalSettings(APISettings):
    # Explicit CPU entrypoint defaults; environment and .env still take precedence.
    llm_backend: Literal["real", "fake", "replay"] = "fake"
    api_allow_model_download: bool = True


def main():
    os.chdir(ROOT)
    api = LocalSettings()
    if api.llm_backend == "real":
        raise SystemExit("CPU MVP accepts fake/replay. See docs/demo.md for the GPU API.")
    if sys.argv[1:] == ["--prepare-index"]:
        from partner_copilot.api_runtime import profile
        from partner_copilot.config import Settings
        from partner_copilot.container import prepare_index

        try:
            prepare_index(profile(Settings(), api), api)
        except Exception as exc:
            raise SystemExit(f"Index initialization failed: {type(exc).__name__}") from None
        return
    if sys.argv[1:]:
        raise SystemExit("Unknown argument")
    # Release the bootstrap encoder before API startup owns its model instances.
    subprocess.run([sys.executable, str(Path(__file__).resolve()), "--prepare-index"], check=True)
    import gradio as gr
    import uvicorn

    from partner_copilot.api import create_app
    from partner_copilot.demo import DemoClient, build_demo

    port = int(os.environ.get("API_PORT", "8000"))
    if not 1 <= port <= 65535:
        raise SystemExit("Invalid API_PORT")
    app = create_app(api_settings=api)
    demo = build_demo(DemoClient(f"http://127.0.0.1:{port}"))
    app = gr.mount_gradio_app(app, demo, path="/demo")
    uvicorn.run(app, host=os.environ.get("API_HOST", "127.0.0.1"), port=port, workers=1)


if __name__ == "__main__":
    main()
