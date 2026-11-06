"""Local Gradio client; inference stays in the API and history stays explicitly recorded."""

import html
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import httpx

from partner_copilot.api_models import MESSAGES, AskRequest, AskResponse


def escape(value):
    return html.escape(str(value), quote=True)


def cards(claims, reviews):
    by_id = {review["id"]: review for review in reviews}
    result = []
    for claim in claims:
        sources = claim.get("fontes") or [{"review_id": i} for i in claim.get("review_ids", [])]
        texts = []
        for source in sources:
            review = by_id.get(source["review_id"])
            if review is None:
                texts.append("<p>Fonte completa indisponível; não confirmar sustentação.</p>")
                continue
            text = escape(review["text"]).replace("\n", "<br>")
            texts.append(
                f"<article><strong>{escape(review['id'])}</strong> · "
                f"nota {escape(review['rating'])} · {escape(review['created_at'])}"
                f"<p><b>Review completa</b></p><p>{text}</p></article>"
            )
        result.append(
            '<section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));'
            'gap:20px;border:1px solid #999;border-radius:10px;padding:16px;margin:12px 0">'
            f"<div><b>Afirmação</b><p>{escape(claim['texto'])}</p></div>"
            f"<div>{''.join(texts)}</div></section>"
        )
    return "".join(result)


def render_answer(answer):
    value = AskResponse.model_validate(answer)
    meta = value.metadata
    mode = "RESPOSTA GRAVADA — REPLAY" if meta.is_replay else meta.mode_label
    state = "ABSTENÇÃO — sem evidência suficiente" if value.abstained else "Resposta com fontes"
    return (
        f"<p><b>DADOS SINTÉTICOS · {escape(mode)}</b></p>"
        f"<p>Prompt: {escape(meta.prompt_version)} · Parser: {escape(meta.parser_version)}</p>"
        f"<h3>{state}</h3><p>{escape(value.answer)}</p>"
        + cards(
            value.result.model_dump()["afirmacoes"],
            [r.model_dump(mode="json") for r in value.source_reviews],
        )
        + "<p>Formato e citações válidas não garantem sustentação factual. "
        "Leia a review inteira.</p>"
    )


def load_history(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value["schema_version"] != "demo-history-v1" or value["new_inference"]:
        raise ValueError("Invalid demo history")
    return {entry["id"]: entry for entry in value["examples"]}


def render_history(entry):
    row = entry["record"]
    structured, _ = json.JSONDecoder().raw_decode(row["raw_response"].lstrip())
    accepted = row.get("status") == "ok" and row.get("answer") is not None
    return (
        "<p><b>DADOS SINTÉTICOS · RESPOSTA GRAVADA · REGISTRO HISTÓRICO</b></p>"
        "<p>Não é geração ao vivo nem uma entrada aprovada do backend replay.</p>"
        f"<h3>{escape(entry['title'])}</h3><p>{escape(entry['note'])}</p>"
        f"<p>Pergunta: {escape(row['pergunta'])}</p>"
        f"<p>Prompt: {escape(row['prompt_version'])} · "
        f"ID: {escape(row['question_id'])} · "
        f"Aceita pelo parser histórico: {'sim' if accepted else 'não'}</p>"
        f"<h3>{'ABSTENÇÃO' if structured['abstem'] else 'Resposta registrada'}</h3>"
        + cards(structured["afirmacoes"], entry["full_context_reviews"])
        + "<details><summary>Reviews completas do contexto</summary>"
        + "".join(
            f"<p><b>{escape(r['id'])}</b>: {escape(r['text'])}</p>"
            for r in entry["full_context_reviews"]
        )
        + f"</details><p>Origem: {escape(entry['source_file'])} · "
        f"SHA256: {escape(entry['source_sha256'])}</p>"
        + '<details><summary>Saída bruta histórica</summary><pre style="white-space:pre-wrap">'
        + escape(row["raw_response"])
        + "</pre></details>"
    )


class DemoClient:
    def __init__(self, base_url, *, transport=None):
        url = urlparse(base_url)
        if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password:
            raise ValueError("DEMO_API_URL must be an HTTP URL without credentials")
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def request(self, method, path, **kwargs):
        with httpx.Client(base_url=self.base_url, timeout=70, transport=self.transport) as client:
            return client.request(method, path, **kwargs)

    def menu(self):
        try:
            health = self.request("GET", "/health")
            data = health.json()
            response = self.request("GET", "/restaurants")
            if response.status_code != 200:
                return (
                    [],
                    "API degradada: menus indisponíveis. "
                    "Registros históricos continuam disponíveis.",
                )
            mode = data.get("mode_label", "Modo indisponível")
            if data.get("backend") == "replay":
                mode = "RESPOSTA GRAVADA — REPLAY; perguntas e filtros devem coincidir exatamente."
            return response.json()[
                "restaurants"
            ], f"Dados sintéticos · {mode} · saúde HTTP {health.status_code}"
        except (httpx.HTTPError, ValueError, KeyError):
            return [], "API indisponível. Inicie o serviço ou explore os registros históricos."

    def ask(self, restaurant, question, start, end, aspect, item, k):
        try:
            filters = {
                key: value
                for key, value in {
                    "start_date": start,
                    "end_date": end,
                    "aspect": aspect,
                    "item": item,
                }.items()
                if value
            }
            payload = AskRequest(
                restaurant_id=restaurant, question=question, filters=filters or None, k=int(k)
            )
            response = self.request("POST", "/ask", json=payload.model_dump(mode="json"))
            data = response.json()
            if response.status_code != 200:
                code = data.get("error", {}).get("code", "internal_error")
                message = MESSAGES.get(code, "A API recusou a resposta.")
                return f"<h3>Resposta indisponível</h3><p>{escape(message)}</p>", {
                    "error": code,
                    "http_status": response.status_code,
                }
            return render_answer(data), data
        except (httpx.HTTPError, ValueError, TypeError):
            return (
                "<h3>Resposta indisponível</h3><p>Confira os campos e a conexão com a API.</p>",
                {"error": "demo_request_failed"},
            )


def build_demo(client=None, history_path=None):
    import gradio as gr

    client = client or DemoClient(os.environ.get("DEMO_API_URL", "http://127.0.0.1:8000"))
    history = load_history(
        history_path or os.environ.get("DEMO_EXAMPLES_PATH", "configs/demo-examples.json")
    )
    with gr.Blocks(title="PartnerCopilot", analytics_enabled=False) as demo:
        gr.Markdown(
            "# PartnerCopilot\nExplore avaliações com fontes. "
            "**Dados sintéticos; sem dados reais do iFood.**"
        )
        with gr.Tab("Consultar API"):
            status = gr.Textbox(label="Estado e modo da API", interactive=False)
            menu_state = gr.State([])
            refresh = gr.Button("Atualizar conexão e restaurantes")
            restaurant = gr.Dropdown(label="Restaurante", choices=[])
            question = gr.Textbox(label="Pergunta", lines=3, max_lines=5)
            with gr.Row():
                start = gr.Textbox(label="Data inicial (AAAA-MM-DD)")
                end = gr.Textbox(label="Data final (AAAA-MM-DD)")
            with gr.Row():
                aspect = gr.Dropdown(
                    label="Aspecto negativo (opcional)",
                    choices=[
                        "sabor",
                        "tempo_entrega",
                        "temperatura",
                        "embalagem",
                        "atendimento",
                        "preco",
                    ],
                    value=None,
                )
                item = gr.Dropdown(label="Item (opcional)", choices=[], value=None)
                k = gr.Slider(
                    1, 12, value=8, step=1, label="Documentos recuperados (contexto até 8)"
                )
            submit = gr.Button("Consultar", variant="primary")
            output = gr.HTML(label="Resposta e reviews completas")
            with gr.Accordion("Resposta estruturada e metadados", open=False):
                structured = gr.JSON()

            def refresh_menu():
                menu, message = client.menu()
                return (
                    menu,
                    message,
                    gr.Dropdown(
                        choices=[(r["name"], r["restaurant_id"]) for r in menu], value=None
                    ),
                    gr.Dropdown(choices=[], value=None),
                )

            def change_restaurant(identifier, menu):
                choices = next((r["items"] for r in menu if r["restaurant_id"] == identifier), [])
                return gr.Dropdown(choices=choices, value=None)

            refresh.click(refresh_menu, outputs=[menu_state, status, restaurant, item])
            demo.load(refresh_menu, outputs=[menu_state, status, restaurant, item])
            restaurant.change(change_restaurant, inputs=[restaurant, menu_state], outputs=item)
            submit.click(
                client.ask,
                inputs=[restaurant, question, start, end, aspect, item, k],
                outputs=[output, structured],
            )
        with gr.Tab("Três casos históricos"):
            gr.Markdown(
                "**Respostas gravadas.** Exemplos expostos, escolhidos para demonstração; "
                "não são avaliação nova nem geração ao vivo."
            )
            selector = gr.Dropdown(
                label="Exemplo",
                choices=[(entry["title"], key) for key, entry in history.items()],
                value="success",
            )
            historical = gr.HTML(render_history(history["success"]))
            selector.change(
                lambda key: render_history(history[key]), inputs=selector, outputs=historical
            )
    return demo


def main():
    demo = build_demo()
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        share=False,
    )


if __name__ == "__main__":
    main()
