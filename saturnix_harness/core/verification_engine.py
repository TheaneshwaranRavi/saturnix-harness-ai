from __future__ import annotations

from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.schemas import BrainMessage, BrainRequest, Capability, IntentMap, VerificationResult


class VerificationEngine:
    """S: Self-Verification Loop."""

    def __init__(self, brain_router: BrainRouter) -> None:
        self.brain_router = brain_router

    async def verify(self, intent: IntentMap, output: str) -> VerificationResult:
        findings: list[str] = []
        score = 1.0
        goal_text = intent.original_goal.strip()
        output_lower = output.lower()

        if _is_unclear_goal(goal_text):
            findings.append("Unclear goal: the request is too short or lacks a concrete deliverable.")
            score -= 0.15
        if not output.strip():
            findings.append("Output is empty.")
            score -= 0.5
        if len(output.strip()) < 80:
            findings.append("Weak output: output may be too brief for the requested goal.")
            score -= 0.2
        for expected in intent.expected_outputs:
            token = expected.split()[0].lower()
            if token not in output_lower:
                findings.append(f"Missing requirement: expected output signal '{expected}' was not found.")
                score -= 0.05
        hallucination_risks = _hallucination_risks(output)
        if hallucination_risks:
            findings.extend(hallucination_risks)
            score -= 0.1 * len(hallucination_risks)
        security_risks = _security_risks(output)
        if security_risks:
            findings.extend(security_risks)
            score -= 0.15 * len(security_risks)
        score = max(0.0, min(1.0, score))

        if score < 0.85:
            critique = await self.brain_router.complete(
                BrainRequest(
                    messages=[
                        BrainMessage(
                            role="system",
                            content=(
                                "Verify the output against the human goal. Return concise findings only."
                            ),
                        ),
                        BrainMessage(
                            role="user",
                            content=f"Goal:\n{intent.original_goal}\n\nOutput:\n{output}",
                        ),
                    ],
                    required_capabilities=[Capability.reasoning, Capability.verification],
                    local_only=intent.local_only,
                )
            )
            findings.append(critique.content)

        ok = score >= 0.72 and not any("empty" in finding.lower() for finding in findings)
        return VerificationResult(ok=ok, score=score, findings=findings)

    async def improve(self, intent: IntentMap, output: str, verification: VerificationResult) -> str:
        response = await self.brain_router.complete(
            BrainRequest(
                messages=[
                    BrainMessage(
                        role="system",
                        content=(
                            "Improve the output so it better satisfies the goal and verification findings. "
                            "Return only the improved answer."
                        ),
                    ),
                    BrainMessage(
                        role="user",
                        content=(
                            f"Goal:\n{intent.original_goal}\n\n"
                            f"Current output:\n{output}\n\n"
                            f"Verification findings:\n{verification.findings}"
                        ),
                    ),
                ],
                required_capabilities=[Capability.reasoning, Capability.verification],
                local_only=intent.local_only,
            )
        )
        return response.content


def _is_unclear_goal(goal: str) -> bool:
    if len(goal.split()) < 3:
        return True
    vague_goals = {"help", "do it", "make it", "build something", "fix this", "improve"}
    return goal.lower().strip() in vague_goals


def _hallucination_risks(output: str) -> list[str]:
    lowered = output.lower()
    risky_phrases = [
        "guaranteed",
        "100%",
        "always",
        "never fails",
        "proven fact",
        "according to sources",
    ]
    findings = []
    if any(phrase in lowered for phrase in risky_phrases):
        findings.append(
            "Hallucination risk: output contains absolute or source-like claims that may need evidence."
        )
    if "citation" in lowered and "http" not in lowered:
        findings.append("Hallucination risk: output references citations without source links.")
    return findings


def _security_risks(output: str) -> list[str]:
    lowered = output.lower()
    risky_tokens = [
        "rm -rf",
        "curl | sh",
        "chmod 777",
        "eval(",
        "exec(",
        "api_key=",
        "password=",
        "secret=",
    ]
    if any(token in lowered for token in risky_tokens):
        return ["Security risk: output contains potentially unsafe commands or secret-handling patterns."]
    return []
