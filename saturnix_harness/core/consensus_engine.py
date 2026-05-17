from __future__ import annotations

import asyncio
import logging
import re
from itertools import combinations

from saturnix_harness.brains.base import BrainProvider
from saturnix_harness.brains.router import BrainRouter
from saturnix_harness.schemas import (
    BrainComparison,
    BrainMessage,
    BrainName,
    BrainRequest,
    Capability,
    ConsensusRequest,
    ConsensusResult,
)

logger = logging.getLogger(__name__)


class ConsensusEngine:
    """Multi-brain consensus layer for hallucination reduction.

    SATURNIX never treats one provider as truth. The consensus engine queries
    configured reasoning brains independently, compares claims, flags conflicts,
    estimates confidence, and returns a validated synthesis.
    """

    target_brains = (
        BrainName.openai,
        BrainName.claude,
        BrainName.gemini,
        BrainName.ollama_gemma,
        BrainName.ollama_coding,
    )

    def __init__(self, brain_router: BrainRouter) -> None:
        self.brain_router = brain_router

    async def run_consensus(self, request: ConsensusRequest) -> ConsensusResult:
        providers = self._select_providers(request)
        comparisons = await asyncio.gather(
            *(self._ask_provider(provider, request) for provider in providers)
        )

        if not comparisons:
            comparisons = [self._unavailable_comparison("No consensus brains were enabled.")]

        detected_conflicts = self._detect_conflicts(comparisons)
        comparisons = self._attach_conflicts(comparisons, detected_conflicts)
        confidence = _overall_confidence(comparisons, detected_conflicts, request.min_brains)
        consensus_result = _merge_strongest_reasoning(comparisons, detected_conflicts)
        final_reasoning = _final_reasoning(
            comparisons=comparisons,
            conflicts=detected_conflicts,
            confidence=confidence,
            min_brains=request.min_brains,
        )
        return ConsensusResult(
            consensus_result=consensus_result,
            brain_comparisons=comparisons,
            confidence_score=confidence,
            detected_conflicts=detected_conflicts,
            final_reasoning=final_reasoning,
        )

    def _select_providers(self, request: ConsensusRequest) -> list[BrainProvider]:
        providers: list[BrainProvider] = []
        for brain in self.target_brains:
            if not request.include_local and brain in {
                BrainName.ollama_gemma,
                BrainName.ollama_coding,
            }:
                continue
            provider = self.brain_router.providers.get(brain)
            if provider and provider.enabled:
                providers.append(provider)
            if len(providers) >= request.max_brains:
                break
        if providers:
            return providers

        mock = self.brain_router.providers.get(BrainName.mock)
        if mock and mock.enabled:
            logger.warning("Consensus fallback is using mock provider only.")
            return [mock]
        return []

    async def _ask_provider(
        self,
        provider: BrainProvider,
        request: ConsensusRequest,
    ) -> BrainComparison:
        brain_request = BrainRequest(
            messages=[
                BrainMessage(
                    role="system",
                    content=(
                        "You are one independent SATURNIX consensus brain. "
                        "Answer the task, list assumptions, avoid unsupported claims, "
                        "and state uncertainty when evidence is weak."
                    ),
                ),
                BrainMessage(role="user", content=_consensus_prompt(request)),
            ],
            required_capabilities=[Capability.reasoning],
            preferred_brain=provider.name,
            local_only=provider.name in {BrainName.ollama_gemma, BrainName.ollama_coding},
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            metadata={
                "consensus": True,
                "task_type": request.task_type,
                "output_format": request.output_format,
            },
        )
        try:
            response = await provider.timed_complete(brain_request)
        except Exception as exc:  # pragma: no cover - provider adapter boundary
            logger.warning("Consensus provider %s failed: %s", provider.name.value, exc)
            return BrainComparison(
                brain=provider.name.value,
                model=provider.model,
                ok=False,
                confidence_score=0.0,
                error=str(exc),
            )

        key_claims = _extract_key_claims(response.content)
        return BrainComparison(
            brain=response.provider.value,
            model=response.model,
            ok=True,
            output=response.content,
            confidence_score=_response_confidence(response.content, key_claims),
            key_claims=key_claims,
        )

    def _detect_conflicts(self, comparisons: list[BrainComparison]) -> list[str]:
        conflicts: list[str] = []
        successful = [comparison for comparison in comparisons if comparison.ok]
        for left, right in combinations(successful, 2):
            conflicts.extend(_pairwise_conflicts(left, right))
        if len(successful) < 2:
            conflicts.append("Consensus had fewer than two successful brains; verify manually.")
        return _dedupe(conflicts)

    def _attach_conflicts(
        self,
        comparisons: list[BrainComparison],
        conflicts: list[str],
    ) -> list[BrainComparison]:
        updated: list[BrainComparison] = []
        for comparison in comparisons:
            brain_conflicts = [
                conflict
                for conflict in conflicts
                if comparison.brain in conflict or "fewer than two" in conflict
            ]
            updated.append(comparison.model_copy(update={"contradictions": brain_conflicts}))
        return updated

    @staticmethod
    def _unavailable_comparison(error: str) -> BrainComparison:
        return BrainComparison(
            brain="none",
            model="none",
            ok=False,
            confidence_score=0.0,
            error=error,
        )


def _consensus_prompt(request: ConsensusRequest) -> str:
    context = f"\n\nContext:\n{request.context}" if request.context else ""
    return (
        f"Task: {request.task}\n"
        f"Task type: {request.task_type}\n"
        f"Privacy level: {request.privacy_level}\n"
        f"Output format: {request.output_format}\n"
        "Return the strongest answer you can justify. Include caveats for uncertain claims."
        f"{context}"
    )


def _extract_key_claims(output: str) -> list[str]:
    normalized = output.replace("\r\n", "\n")
    candidates: list[str] = []
    for line in normalized.split("\n"):
        cleaned = re.sub(r"^\s*[-*0-9.)]+\s*", "", line).strip()
        if 18 <= len(cleaned) <= 240:
            candidates.append(cleaned)
    if not candidates:
        candidates = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if 18 <= len(sentence.strip()) <= 240
        ]
    return _dedupe(candidates[:8])


def _response_confidence(output: str, key_claims: list[str]) -> float:
    text = output.lower()
    score = 0.45
    if len(output.strip()) >= 120:
        score += 0.15
    if len(key_claims) >= 2:
        score += 0.1
    if any(marker in text for marker in ("because", "therefore", "evidence", "assumption")):
        score += 0.1
    if any(marker in text for marker in ("maybe", "unclear", "unknown", "cannot verify")):
        score -= 0.05
    if any(marker in text for marker in ("guaranteed", "100%", "always", "never fails")):
        score -= 0.2
    return _clamp(score)


def _pairwise_conflicts(left: BrainComparison, right: BrainComparison) -> list[str]:
    conflicts: list[str] = []
    for left_claim in left.key_claims:
        for right_claim in right.key_claims:
            if _claims_conflict(left_claim, right_claim):
                conflicts.append(
                    f"{left.brain} conflicts with {right.brain}: "
                    f"'{left_claim}' vs '{right_claim}'"
                )
    return conflicts


def _claims_conflict(left: str, right: str) -> bool:
    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens.intersection(right_tokens))
    union = len(left_tokens.union(right_tokens))
    if union == 0 or overlap / union < 0.25:
        return False
    return _claim_polarity(left) * _claim_polarity(right) < 0


def _meaningful_tokens(text: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "into",
        "should",
        "would",
        "could",
        "there",
        "their",
        "about",
        "task",
        "output",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", text.lower())
        if token not in stopwords
    }


def _claim_polarity(text: str) -> int:
    normalized = text.lower()
    negative_phrases = {
        "do not",
        "cannot",
        "can't",
        "should not",
        "must not",
        "never",
    }
    if any(phrase in normalized for phrase in negative_phrases):
        return -1

    negative = {
        "not",
        "avoid",
        "unsafe",
        "false",
        "invalid",
        "fail",
        "failed",
        "no",
    }
    positive = {
        "can",
        "should",
        "safe",
        "true",
        "valid",
        "works",
        "recommended",
        "use",
        "yes",
    }
    words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_'-]*", normalized))
    score = len(words.intersection(positive)) - len(words.intersection(negative))
    if score == 0:
        return 0
    return 1 if score > 0 else -1


def _overall_confidence(
    comparisons: list[BrainComparison],
    conflicts: list[str],
    min_brains: int,
) -> float:
    successful = [comparison for comparison in comparisons if comparison.ok]
    if not successful:
        return 0.0
    average = sum(comparison.confidence_score for comparison in successful) / len(successful)
    agreement = _agreement_score(successful)
    confidence = average * 0.65 + agreement * 0.35
    confidence -= min(0.35, 0.08 * len(conflicts))
    if len(successful) < min_brains:
        confidence -= 0.25
    return _clamp(confidence)


def _agreement_score(comparisons: list[BrainComparison]) -> float:
    if len(comparisons) < 2:
        return 0.35
    scores: list[float] = []
    for left, right in combinations(comparisons, 2):
        left_tokens = _meaningful_tokens(" ".join(left.key_claims) or left.output)
        right_tokens = _meaningful_tokens(" ".join(right.key_claims) or right.output)
        if not left_tokens or not right_tokens:
            scores.append(0.0)
            continue
        overlap = len(left_tokens.intersection(right_tokens))
        scores.append(overlap / len(left_tokens.union(right_tokens)))
    return sum(scores) / len(scores) if scores else 0.0


def _merge_strongest_reasoning(
    comparisons: list[BrainComparison],
    conflicts: list[str],
) -> str:
    successful = sorted(
        [comparison for comparison in comparisons if comparison.ok],
        key=lambda comparison: comparison.confidence_score,
        reverse=True,
    )
    if not successful:
        return "Consensus could not be generated because no brain returned a usable answer."

    strongest = successful[0]
    shared_claims = _shared_claims(successful)
    sections = [
        "Consensus synthesis:",
        strongest.output.strip(),
    ]
    if shared_claims:
        sections.extend(
            ["", "Cross-brain agreed claims:", *[f"- {claim}" for claim in shared_claims]]
        )
    if conflicts:
        sections.extend(
            ["", "Conflict handling:", *[f"- {conflict}" for conflict in conflicts[:5]]]
        )
    return "\n".join(sections)


def _shared_claims(comparisons: list[BrainComparison]) -> list[str]:
    shared: list[str] = []
    for comparison in comparisons:
        for claim in comparison.key_claims:
            claim_tokens = _meaningful_tokens(claim)
            if not claim_tokens:
                continue
            matches = 0
            for other in comparisons:
                if other is comparison:
                    continue
                other_tokens = _meaningful_tokens(" ".join(other.key_claims))
                if other_tokens and len(claim_tokens.intersection(other_tokens)) >= 3:
                    matches += 1
            if matches:
                shared.append(claim)
    return _dedupe(shared[:6])


def _final_reasoning(
    comparisons: list[BrainComparison],
    conflicts: list[str],
    confidence: float,
    min_brains: int,
) -> str:
    successful = [comparison for comparison in comparisons if comparison.ok]
    failed = [comparison for comparison in comparisons if not comparison.ok]
    reasoning = [
        f"Queried {len(comparisons)} brain(s); {len(successful)} succeeded.",
        f"Minimum requested successful brains: {min_brains}.",
        f"Confidence score: {confidence:.2f}.",
    ]
    if conflicts:
        reasoning.append(
            "Contradictions were detected, so conflicting claims were not treated as settled."
        )
    else:
        reasoning.append("No direct claim contradictions were detected by heuristic comparison.")
    if failed:
        reasoning.append(
            "Unavailable or failed brains: "
            + ", ".join(f"{comparison.brain} ({comparison.error})" for comparison in failed)
        )
    reasoning.append("Final answer is based on highest-confidence output plus shared claims.")
    return " ".join(reasoning)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 2)
