"""Stream only the answer field, then validate the complete grounded response."""

from typing import TYPE_CHECKING

from llm_bot.schemas import HragRequest
from llm_bot.tasks.hrag import prepare_hrag
from llm_bot.tasks.llm_utils import MissingOutputTextError
from pydantic_core import from_json

from core.service.hrag.retrieval import run_inference


if TYPE_CHECKING:
    from models.hrag import HragResult

    from core.service.chat import ChatClient, ChatTurnStream


class AnswerClient:
    def __init__(self, client: "ChatClient", stream: "ChatTurnStream"):
        self.client = client
        self.stream = stream

    async def create_response(self, system_input: str, user_input: str, response_format: dict | None = None) -> dict:
        buffer = ""
        self.stream.content = ""

        def receive(delta: str) -> None:
            nonlocal buffer
            buffer += delta
            try:
                partial = from_json(buffer, allow_partial="trailing-strings")
            except ValueError:
                return
            answer = partial.get("answer") if isinstance(partial, dict) else None
            if isinstance(answer, str) and answer.startswith(self.stream.content):
                self.stream.add(answer[len(self.stream.content) :])

        return self.client.create_response(
            [{"role": "user", "content": user_input}], receive, prompt=system_input, response_format=response_format
        )


def synthesize(question: str, history: list[dict], result: "HragResult", client: "ChatClient", stream: "ChatTurnStream") -> str:
    request = HragRequest.model_validate(
        {
            "question": question,
            "conversation": [{"role": message["role"], "content": message["content"]} for message in history],
            "notices": result.notices,
            "passages": [
                {"id": evidence.citation, "source": evidence.news_item_id, "text": evidence.quote}
                for evidence in result.evidence
                if evidence.branch == "vector"
            ],
            "graph_facts": [
                {
                    "id": evidence.citation,
                    "source": evidence.news_item_id,
                    "fact": f"{evidence.description} ({evidence.assertion or 'mention'}): {evidence.quote}",
                }
                for evidence in result.evidence
                if evidence.branch == "graph"
            ],
        }
    )
    try:
        answer = run_inference(prepare_hrag(request).run(AnswerClient(client, stream)), client.deadline)
    except (ValueError, MissingOutputTextError):
        from core.service.chat import ChatProviderError

        raise ChatProviderError("HRAG provider returned an invalid grounded answer") from None
    if not answer.answer.startswith(stream.content):
        stream.content = ""
    stream.add(answer.answer[len(stream.content) :])
    return answer.answer
