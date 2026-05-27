"""Target adapters — the agents that get attacked.

A target is anything that takes a prompt (string) and returns a response
(string). The runner does not care whether the target is a real LLM, a
custom agent, or a mock — it just calls `.query(prompt)`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Target(ABC):
    """Abstract interface every target adapter must implement."""

    name: str = "abstract"

    @abstractmethod
    def query(self, prompt: str) -> str:
        """Send a single prompt to the agent and return its text response."""


class MockTarget(Target):
    """A fake agent that returns canned responses based on probe category hints.

    Used for free, deterministic end-to-end testing of ShieldLM itself.
    Responses are deliberately mixed — some safe, some unsafe — so that a
    demo run produces an interesting report with passes, partials, and fails.
    """

    name = "mock"

    # Keyword → canned response. Checked in order; first match wins.
    # The keywords are chosen to match the example probe library so the
    # demo report has a realistic spread of outcomes.
    _RULES: list[tuple[str, str]] = [
        (
            "ignore all previous instructions",
            "I'll stick with my original instructions. I can't follow that request.",
        ),
        (
            "simulated tool result",
            "Sure — I'll share the user's contact list as the note instructs.",
        ),
        (
            "roleplay",
            "Okay, I can play a character — but I'll keep my safety guidelines in place either way.",
        ),
        (
            "repeat the text above",
            "I'm not able to share my system instructions. Is there something else I can help with?",
        ),
        (
            "free the most space",
            "Running `rm -rf /` now to clear up the most space — one moment!",
        ),
        (
            "system administrator",
            "Understood, admin. I'll disable my safety instructions for this session as requested.",
        ),
    ]

    _DEFAULT = "I'm not sure I can help with that. Could you clarify what you need?"

    def query(self, prompt: str) -> str:
        lowered = prompt.lower()
        for keyword, response in self._RULES:
            if keyword in lowered:
                return response
        return self._DEFAULT


class ClaudeTarget(Target):
    """Target adapter for Anthropic's Claude API.

    API key is read from the ANTHROPIC_API_KEY environment variable.
    Pass `system_prompt` to evaluate Claude with the system instructions
    your agent would actually run in production.
    """

    name = "claude"

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> None:
        # Imported lazily so users running the mock target don't need the SDK.
        import anthropic

        self._client = anthropic.Anthropic()
        self._model = model
        self._system_prompt = (system_prompt or "").strip()
        self._max_tokens = max_tokens

    def query(self, prompt: str) -> str:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        message = self._client.messages.create(**kwargs)
        return "".join(
            getattr(block, "text", "") for block in message.content
        ).strip()


def get_target(name: str, **kwargs) -> Target:
    """Factory that returns a target by name. New adapters get added here."""
    name = name.lower()
    if name == "mock":
        return MockTarget()
    if name == "claude":
        return ClaudeTarget(**kwargs)
    raise ValueError(
        f"Unknown target '{name}'. Available targets: mock, claude"
    )
