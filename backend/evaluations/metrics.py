"""AEGIS AI — Evaluation Metrics Engine
Implements industry-standard RAG triad and agent evaluation algorithms:
  - Context Precision (Mean Precision@K of retrieved chunks)
  - Context Recall (Ground truth claims coverage)
  - Faithfulness / Groundedness (Hallucination detection in generated claims)
  - Answer Relevancy (Query intent semantic alignment)
  - Tool Accuracy & Argument Conformance
  - Task Success Rate across Agent DAGs
"""

import re
from typing import Any

STOP_WORDS = {
    "the", "and", "for", "are", "with", "from", "that", "this", "have",
    "has", "after", "which", "was", "were", "into", "our", "what", "how",
    "does", "its", "who", "all", "each", "can", "any", "such", "not", "but",
    "they", "will", "than", "then", "been", "also", "only", "well", "more",
}


def _tokenize(text: str) -> set[str]:
    """Extracts normalized alphanumeric token set from text, filtering trivial stop words."""
    words = re.findall(r"\b[a-zA-Z0-9_]{3,}\b", text.lower())
    filtered = {w for w in words if w not in STOP_WORDS}
    return filtered if filtered else set(words)


def _split_into_claims(text: str) -> list[str]:
    """Segments text into independent claim sentences."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    claims = [s.strip() for s in raw_sentences if len(s.strip()) > 8]
    return claims if claims else [text.strip()]


def compute_context_precision(
    retrieved_contexts: list[str],
    ground_truth_statements: list[str],
) -> float:
    """Computes Mean Precision@K: checks whether relevant chunks are ranked at the top.

    Precision@k is computed at each rank k where a relevant chunk is found.
    """
    if not retrieved_contexts or not ground_truth_statements:
        return 0.0

    gt_tokens = set()
    for stmt in ground_truth_statements:
        gt_tokens.update(_tokenize(stmt))

    if not gt_tokens:
        return 1.0

    relevant_count = 0
    precision_sum = 0.0

    for k, ctx in enumerate(retrieved_contexts, start=1):
        ctx_tokens = _tokenize(ctx)
        overlap = ctx_tokens.intersection(gt_tokens)
        # Relevant if at least 2 key content tokens match
        is_relevant = len(overlap) >= min(2, len(gt_tokens))

        if is_relevant:
            relevant_count += 1
            precision_at_k = relevant_count / k
            precision_sum += precision_at_k

    if relevant_count == 0:
        return 0.0

    return round(precision_sum / relevant_count, 4)


def compute_context_recall(
    retrieved_contexts: list[str],
    ground_truth_statements: list[str],
) -> float:
    """Computes the proportion of ground-truth statements covered in the retrieved contexts."""
    if not ground_truth_statements:
        return 1.0
    if not retrieved_contexts:
        return 0.0

    combined_context = " ".join(retrieved_contexts)
    ctx_tokens = _tokenize(combined_context)
    covered_statements = 0

    for stmt in ground_truth_statements:
        stmt_tokens = _tokenize(stmt)
        if not stmt_tokens:
            covered_statements += 1
            continue

        overlap = stmt_tokens.intersection(ctx_tokens)
        coverage_ratio = len(overlap) / len(stmt_tokens)

        # Covered if >= 30% of distinctive content tokens appear in retrieved contexts
        if coverage_ratio >= 0.30:
            covered_statements += 1

    return round(covered_statements / len(ground_truth_statements), 4)


def compute_faithfulness(
    answer: str,
    contexts: list[str],
) -> tuple[float, list[dict[str, Any]]]:
    """Measures hallucination rate by verifying what fraction of generated claims are grounded in context.

    Returns:
      (faithfulness_score, claim_verifications)
    """
    claims = _split_into_claims(answer)
    if not claims:
        return 1.0, []

    combined_context = " ".join(contexts)
    ctx_tokens = _tokenize(combined_context)

    verified_claims = 0
    claim_details: list[dict[str, Any]] = []

    for claim in claims:
        claim_tokens = _tokenize(claim)
        if not claim_tokens:
            claim_details.append({"claim": claim, "grounded": True, "overlap_ratio": 1.0})
            verified_claims += 1
            continue

        overlap = claim_tokens.intersection(ctx_tokens)
        overlap_ratio = len(overlap) / len(claim_tokens)

        # Grounded if at least 30% of distinct content words are substantiated in retrieved context
        is_grounded = overlap_ratio >= 0.30
        if is_grounded:
            verified_claims += 1

        claim_details.append(
            {
                "claim": claim,
                "grounded": is_grounded,
                "overlap_ratio": round(overlap_ratio, 2),
            }
        )

    score = round(verified_claims / len(claims), 4)
    return score, claim_details


def compute_answer_relevance(question: str, answer: str) -> float:
    """Computes semantic intent relevance between the user question and the generated answer."""
    q_tokens = _tokenize(question)
    a_tokens = _tokenize(answer)

    if not q_tokens or not a_tokens:
        return 0.0

    overlap = q_tokens.intersection(a_tokens)
    coverage = len(overlap) / max(1, len(q_tokens))
    score = min(1.0, coverage * 1.4 + 0.15)
    return round(score, 4)


def compute_tool_accuracy(
    predicted_tool: str,
    expected_tool: str,
    predicted_arguments: dict[str, Any],
    required_keys: list[str] | None = None,
) -> float:
    """Evaluates agent tool selection and argument schema conformance."""
    if predicted_tool.lower().strip() != expected_tool.lower().strip():
        return 0.0

    score = 0.6
    if required_keys:
        present_keys = [k for k in required_keys if k in predicted_arguments and predicted_arguments[k] is not None]
        arg_ratio = len(present_keys) / len(required_keys)
        score += 0.4 * arg_ratio
    else:
        score = 1.0

    return round(score, 4)


def compute_task_success_rate(step_statuses: list[str]) -> float:
    """Computes percentage of successful execution steps in an agent run."""
    if not step_statuses:
        return 0.0
    successful = sum(1 for s in step_statuses if s.upper() in ("SUCCESS", "COMPLETED", "OK"))
    return round(successful / len(step_statuses), 4)
