from __future__ import annotations

from langgraph_sdk import get_client


class InterrogationClient:
    """Client for the 3A Interrogation LangGraph Cloud graph.

    Manages multi-round conversation sessions via thread_id.
    """

    def __init__(self, deployment_url: str, api_key: str) -> None:
        self.lg = get_client(url=deployment_url, api_key=api_key)

    async def interrogate(self, message: str, thread_id: str | None = None) -> dict:
        """Start or continue an interrogation session.

        - No thread_id: creates new thread, sends message as hunch
        - With thread_id: resumes existing thread with message as user reply
        """
        if thread_id is None:
            thread = await self.lg.threads.create()
            thread_id = thread["thread_id"]
            await self.lg.runs.wait(
                thread_id=thread_id,
                assistant_id="interrogation",
                input={
                    "hunch": message,
                    "messages": [{"role": "user", "content": message}],
                },
            )
        else:
            await self.lg.runs.wait(
                thread_id=thread_id,
                assistant_id="interrogation",
                command={"resume": message},
            )

        state = await self.lg.threads.get_state(thread_id)
        artifact = state["values"].get("artifact")
        messages = state["values"].get("messages", [])
        ai_response = messages[-1]["content"] if messages else ""

        return {
            "thread_id": thread_id,
            "ai_response": ai_response,
            "is_complete": artifact is not None,
            **({"artifact": artifact} if artifact else {}),
        }
