"""Complementarity Engine V2 for diversity-aware multi-skill selection."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations

from app.core.state import AgentPersonality, AgentStyle, SkillCategory, SkillMetadata, SkillTier
from app.memory.learning import get_skill_reliability


@dataclass
class ScoredSkill:
    """A skill annotated with relevance/diversity/synergy scores."""

    metadata: SkillMetadata
    relevance: float
    category_value: float
    diversity_bonus: float = 0.0
    redundancy_penalty: float = 0.0
    synergy_bonus: float = 0.0
    budget_cost: float = 1.0
    tier_bonus: float = 0.0
    reliability_score: float = 0.5
    uncertainty_penalty: float = 0.5
    downside_risk: float = 0.5

    @property
    def composite_score(self) -> float:
        return (
            self.relevance * 0.40
            + self.category_value * 0.15
            + self.diversity_bonus * 0.15
            + self.synergy_bonus * 0.15
            - self.redundancy_penalty * 0.10
            + self.tier_bonus * 0.05
            + self.reliability_score * 0.06
            - self.uncertainty_penalty * 0.04
            - self.downside_risk * 0.02
        )


@dataclass
class ComplementarityResult:
    """Result bundle returned by the complementarity engine."""

    selected: list[ScoredSkill]
    rejected: list[ScoredSkill]
    pairwise_scores: dict[str, float] = field(default_factory=dict)
    synergy_matrix: dict[str, float] = field(default_factory=dict)
    total_coverage: float = 0.0
    total_redundancy: float = 0.0
    diversity_shannon: float = 0.0
    diversity_simpson: float = 0.0
    ensemble_coherence: float = 0.0
    total_synergy: float = 0.0
    total_budget_used: float = 0.0
    selection_rounds: int = 0
    robust_expected_utility: float = 0.0
    robust_worst_case_utility: float = 0.0
    avg_uncertainty: float = 0.0

    @property
    def diversity_index(self) -> float:
        """Backward-compatible alias for legacy callers/tests."""

        return self.diversity_shannon


class ComplementarityEngine:
    """Complementarity skill selection engine (V2)."""

    def __init__(
        self,
        max_skills: int = 3,
        redundancy_threshold: float = 0.7,
        budget_limit: float = 5.0,
        enable_synergy: bool = True,
        enable_conflict_avoidance: bool = True,
        refinement_rounds: int = 1,
        enable_robust_selection: bool = True,
        risk_aversion: float = 0.65,
        reliability_floor: float = 0.45,
        uncertainty_tolerance: float = 0.50,
    ):
        self.max_skills = max_skills
        self.redundancy_threshold = redundancy_threshold
        self.budget_limit = budget_limit
        self.enable_synergy = enable_synergy
        self.enable_conflict_avoidance = enable_conflict_avoidance
        self.refinement_rounds = refinement_rounds
        self.enable_robust_selection = enable_robust_selection
        self.risk_aversion = max(0.0, min(float(risk_aversion), 1.0))
        self.reliability_floor = max(0.0, min(float(reliability_floor), 1.0))
        self.uncertainty_tolerance = max(0.0, min(float(uncertainty_tolerance), 1.0))

    def _score_relevance(self, skill: SkillMetadata, query: str) -> float:
        """Score how relevant a skill is to the query (0-1)."""

        query_lower = query.lower()
        tokens = set(query_lower.split())

        keyword_hits = sum(1 for kw in skill.confidence_keywords if kw in query_lower)
        keyword_score = min(keyword_hits / max(len(skill.confidence_keywords), 1), 1.0)

        strength_hits = sum(
            1
            for strength in skill.strengths
            if any(word in tokens for word in strength.lower().split())
        )
        strength_score = min(strength_hits / max(len(skill.strengths), 1), 1.0)

        desc_tokens = set(skill.description.lower().split())
        desc_overlap = len(tokens & desc_tokens) / max(len(tokens), 1)

        length_tokens = len(query.split())
        if length_tokens < skill.min_context_length:
            context_score = 0.6
        elif length_tokens > skill.max_context_length:
            context_score = 0.7
        else:
            context_score = 1.0

        return (0.50 * keyword_score + 0.30 * strength_score + 0.20 * desc_overlap) * context_score

    def _pairwise_similarity(self, a: SkillMetadata, b: SkillMetadata) -> float:
        """Similarity between two skills (0-1). Higher means more redundant."""

        cat_sim = 1.0 if a.category == b.category else 0.0

        a_strengths = set(word for item in a.strengths for word in item.lower().split())
        b_strengths = set(word for item in b.strengths for word in item.lower().split())
        if a_strengths | b_strengths:
            strength_sim = len(a_strengths & b_strengths) / len(a_strengths | b_strengths)
        else:
            strength_sim = 0.0

        output_sim = 1.0 if a.output_type == b.output_type else 0.0

        a_kw = set(a.confidence_keywords)
        b_kw = set(b.confidence_keywords)
        if a_kw | b_kw:
            kw_sim = len(a_kw & b_kw) / len(a_kw | b_kw)
        else:
            kw_sim = 0.0

        return 0.35 * cat_sim + 0.30 * strength_sim + 0.15 * output_sim + 0.20 * kw_sim

    def _compute_synergy(self, a: SkillMetadata, b: SkillMetadata) -> float:
        """Compute skill-pair synergy (0-1)."""

        declared = 1.0 if (b.name in a.synergies or a.name in b.synergies) else 0.0
        cat_complement = 0.0 if a.category == b.category else 0.7
        output_complement = 0.0 if a.output_type == b.output_type else 0.5
        return 0.5 * declared + 0.3 * cat_complement + 0.2 * output_complement

    @staticmethod
    def _risk_profile_score(skill: SkillMetadata) -> float:
        """Map textual risk profile into [0,1] risk score."""

        risk_map = {
            "very_low": 0.1,
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 1.0,
        }
        key = str(skill.risk_profile or "medium").strip().lower()
        return max(0.0, min(1.0, risk_map.get(key, 0.5)))

    def _skill_uncertainty_signals(self, skill: SkillMetadata) -> tuple[float, float, float]:
        """Return reliability, uncertainty, and downside risk signals.

        reliability: empirical + metadata confidence estimate.
        uncertainty: 1 - reliability.
        downside risk: risk-profile and cost pressure proxy.
        """

        runtime = max(0.0, min(1.0, get_skill_reliability(skill.name)))
        calibration = max(0.0, min(1.0, float(skill.calibration_score)))
        interpretability = max(0.0, min(1.0, float(skill.interpretability_score)))
        reputation = max(0.0, min(1.0, float(skill.reputation_score)))

        reliability = (
            0.45 * runtime
            + 0.25 * calibration
            + 0.20 * interpretability
            + 0.10 * reputation
        )
        reliability = max(0.0, min(1.0, reliability))
        uncertainty = 1.0 - reliability

        cost_pressure = max(0.0, min(1.0, float(skill.compute_cost) / max(self.budget_limit, 1.0)))
        risk_profile = self._risk_profile_score(skill)
        downside = max(0.0, min(1.0, 0.55 * risk_profile + 0.45 * cost_pressure))
        return reliability, uncertainty, downside

    def _robust_set_utility(self, selected: list[ScoredSkill]) -> tuple[float, float, float]:
        """Expected and lower-tail utility under independent failure approximation."""

        if not selected:
            return 0.0, 0.0, 0.0

        expected = sum(skill.composite_score * skill.reliability_score for skill in selected)
        variance = sum(
            (skill.composite_score ** 2) * skill.reliability_score * (1.0 - skill.reliability_score)
            for skill in selected
        )
        sigma = math.sqrt(max(variance, 0.0))

        # Approximate 10th percentile (z ~= 1.28) to capture downside risk.
        worst_case = expected - 1.2816 * sigma
        avg_uncertainty = sum(skill.uncertainty_penalty for skill in selected) / len(selected)
        return expected, worst_case, avg_uncertainty

    def _has_conflict(self, a: SkillMetadata, b: SkillMetadata) -> bool:
        """Check whether a skill pair has an explicit conflict."""

        return b.name in a.conflicts or a.name in b.conflicts

    def _marginal_gain(self, candidate: ScoredSkill, already_selected: list[ScoredSkill]) -> float:
        """Compute marginal value of adding `candidate` into current selection."""

        if candidate.budget_cost > self.budget_limit:
            return 0.0
        if self.enable_robust_selection and candidate.reliability_score < self.reliability_floor:
            return 0.0
        if self.enable_robust_selection and candidate.uncertainty_penalty > self.uncertainty_tolerance:
            return 0.0

        if not already_selected:
            if not self.enable_robust_selection:
                return candidate.relevance
            solo_gain = (
                candidate.composite_score
                - self.risk_aversion * candidate.downside_risk
                - max(0.0, candidate.uncertainty_penalty - self.uncertainty_tolerance)
            )
            return max(solo_gain, 0.0)

        current_budget = sum(skill.budget_cost for skill in already_selected)
        if current_budget + candidate.budget_cost > self.budget_limit:
            return 0.0

        if self.enable_conflict_avoidance:
            for selected in already_selected:
                if self._has_conflict(candidate.metadata, selected.metadata):
                    return 0.0

        max_redundancy = max(
            self._pairwise_similarity(candidate.metadata, selected.metadata)
            for selected in already_selected
        )

        synergy_bonus = 0.0
        if self.enable_synergy:
            synergy_bonus = max(
                self._compute_synergy(candidate.metadata, selected.metadata)
                for selected in already_selected
            )

        existing_categories = {skill.metadata.category for skill in already_selected}
        new_category_bonus = 0.3 if candidate.metadata.category not in existing_categories else 0.0

        existing_output_types = {skill.metadata.output_type for skill in already_selected}
        new_output_bonus = 0.15 if candidate.metadata.output_type not in existing_output_types else 0.0

        gain = (
            candidate.composite_score
            + new_category_bonus
            + new_output_bonus
            + synergy_bonus * 0.3
            - max_redundancy * 0.6
        )
        if self.enable_robust_selection:
            expected_before, worst_before, _ = self._robust_set_utility(already_selected)
            expected_after, worst_after, _ = self._robust_set_utility(already_selected + [candidate])
            gain += (expected_after - expected_before) * 0.35
            gain += (worst_after - worst_before) * (0.55 + 0.25 * self.risk_aversion)
            gain -= max(0.0, candidate.uncertainty_penalty - self.uncertainty_tolerance) * 0.4
            gain -= candidate.downside_risk * self.risk_aversion * 0.3
        return max(gain, 0.0)

    def _apply_style(
        self,
        selected: list[ScoredSkill],
        all_scored: list[ScoredSkill],
        style: AgentStyle,
    ) -> list[ScoredSkill]:
        """Adjust selected set based on agent style."""

        if not all_scored:
            return []

        if style == AgentStyle.AGGRESSIVE:
            if selected:
                return [max(selected, key=lambda skill: skill.relevance)]
            return [max(all_scored, key=lambda skill: skill.relevance)]

        if style == AgentStyle.CAUTIOUS:
            picked = list(selected)
            categories = {skill.metadata.category for skill in picked}
            for candidate in sorted(all_scored, key=lambda skill: skill.relevance, reverse=True):
                if len(picked) >= self.max_skills + 1:
                    break
                if candidate in picked:
                    continue
                if candidate.metadata.category in categories:
                    continue
                if self._marginal_gain(candidate, picked) <= 0:
                    continue
                picked.append(candidate)
                categories.add(candidate.metadata.category)
            return picked

        if style == AgentStyle.CREATIVE:
            if not selected:
                return selected
            counts: dict[SkillCategory, int] = {}
            for skill in all_scored:
                counts[skill.metadata.category] = counts.get(skill.metadata.category, 0) + 1
            rarest_category = min(counts, key=lambda category: counts[category])
            rarest = [skill for skill in all_scored if skill.metadata.category == rarest_category]
            if rarest:
                candidate = max(rarest, key=lambda skill: skill.relevance)
                if candidate not in selected:
                    worst = min(selected, key=lambda skill: skill.composite_score)
                    replaced = [skill for skill in selected if skill is not worst] + [candidate]
                    if sum(skill.budget_cost for skill in replaced) <= self.budget_limit:
                        selected = replaced
            return selected

        return selected

    def _apply_personality(
        self,
        selected: list[ScoredSkill],
        all_scored: list[ScoredSkill],
        personality: AgentPersonality,
    ) -> list[ScoredSkill]:
        """Fine-tune selected skills based on personality dimensions."""

        if not all_scored:
            return selected

        tuned = list(selected)

        if personality.confidence_threshold > 0.3:
            tuned = [skill for skill in tuned if skill.relevance >= personality.confidence_threshold]
            if not tuned:
                tuned = [max(all_scored, key=lambda skill: skill.relevance)]

        if personality.creativity_bias > 0.7:
            counts: dict[SkillCategory, int] = {}
            for skill in all_scored:
                counts[skill.metadata.category] = counts.get(skill.metadata.category, 0) + 1
            rarest_cat = min(counts, key=lambda category: counts[category])
            rarest_candidates = [skill for skill in all_scored if skill.metadata.category == rarest_cat]
            if rarest_candidates:
                rarest_best = max(rarest_candidates, key=lambda skill: skill.relevance)
                if rarest_best not in tuned:
                    if tuned:
                        tuned[-1] = rarest_best
                    else:
                        tuned.append(rarest_best)

        if personality.diversity_preference > 0.7:
            categories = {skill.metadata.category for skill in tuned}
            for candidate in sorted(all_scored, key=lambda skill: skill.relevance, reverse=True):
                if candidate in tuned:
                    continue
                if candidate.metadata.category in categories:
                    continue
                candidate_set = tuned + [candidate]
                if sum(skill.budget_cost for skill in candidate_set) > self.budget_limit:
                    continue
                tuned.append(candidate)
                break

        if personality.depth_vs_breadth < 0.3 and len(tuned) > 1:
            keep = max(1, len(tuned) // 2)
            tuned = sorted(tuned, key=lambda skill: skill.relevance, reverse=True)[:keep]

        if personality.risk_tolerance < 0.2:
            tuned = [skill for skill in tuned if skill.relevance >= 0.2] or [max(all_scored, key=lambda skill: skill.relevance)]

        return tuned

    def _selection_objective(self, selected: list[ScoredSkill]) -> float:
        """Estimate set-level objective score used in refinement."""

        if not selected:
            return 0.0
        if sum(skill.budget_cost for skill in selected) > self.budget_limit:
            return 0.0

        score = sum(skill.composite_score for skill in selected)
        for left, right in combinations(selected, 2):
            if self.enable_conflict_avoidance and self._has_conflict(left.metadata, right.metadata):
                return 0.0
            score -= self._pairwise_similarity(left.metadata, right.metadata) * 0.2
            if self.enable_synergy:
                score += self._compute_synergy(left.metadata, right.metadata) * 0.2
        if self.enable_robust_selection:
            expected, worst_case, avg_uncertainty = self._robust_set_utility(selected)
            score += expected * 0.25
            score += worst_case * (0.35 + 0.20 * self.risk_aversion)
            score -= avg_uncertainty * 0.25
        return score

    def _refine_selection(
        self,
        selected: list[ScoredSkill],
        rejected: list[ScoredSkill],
    ) -> tuple[list[ScoredSkill], int]:
        """Local-search refinement by swap attempts."""

        if self.refinement_rounds <= 0:
            return selected, 0

        working_selected = list(selected)
        working_rejected = list(rejected)
        rounds = 0
        improved = True

        while improved and rounds < self.refinement_rounds:
            improved = False
            rounds += 1
            base_score = self._selection_objective(working_selected)

            for index, current in enumerate(list(working_selected)):
                reduced = [skill for i, skill in enumerate(working_selected) if i != index]
                best_set = None
                best_score = base_score
                best_candidate = None

                for candidate in working_rejected:
                    trial = reduced + [candidate]
                    trial_score = self._selection_objective(trial)
                    if trial_score > best_score + 0.05:
                        best_score = trial_score
                        best_set = trial
                        best_candidate = candidate

                if best_set is not None and best_candidate is not None:
                    working_rejected.remove(best_candidate)
                    working_rejected.append(current)
                    working_selected = best_set
                    base_score = best_score
                    improved = True

        return working_selected, rounds

    def _simpson_diversity(self, selected: list[ScoredSkill]) -> float:
        """Simpson diversity index (higher is more diverse)."""

        if not selected:
            return 0.0
        frequencies: dict[SkillCategory, int] = {}
        for skill in selected:
            frequencies[skill.metadata.category] = frequencies.get(skill.metadata.category, 0) + 1
        total = len(selected)
        return 1.0 - sum((count / total) ** 2 for count in frequencies.values())

    def select(
        self,
        skills: list[SkillMetadata],
        query: str,
        style: AgentStyle = AgentStyle.BALANCED,
        personality: AgentPersonality | None = None,
    ) -> ComplementarityResult:
        """Run the full V2 complementarity selection pipeline."""

        if not skills:
            return ComplementarityResult(selected=[], rejected=[], selection_rounds=0)

        cat_counts: dict[SkillCategory, int] = {}
        for skill in skills:
            cat_counts[skill.category] = cat_counts.get(skill.category, 0) + 1

        tier_bonus_map = {
            SkillTier.BASIC: 0.1,
            SkillTier.ADVANCED: 0.2,
            SkillTier.EXPERT: 0.3,
            SkillTier.LEGENDARY: 0.4,
        }

        scored: list[ScoredSkill] = []
        total_cats = sum(cat_counts.values())
        for skill in skills:
            relevance = self._score_relevance(skill, query)
            category_value = 1.0 - (cat_counts[skill.category] / total_cats) if total_cats else 0.5
            reliability, uncertainty, downside = self._skill_uncertainty_signals(skill)
            scored.append(
                ScoredSkill(
                    metadata=skill,
                    relevance=relevance,
                    category_value=category_value,
                    budget_cost=skill.compute_cost,
                    tier_bonus=tier_bonus_map.get(skill.tier, 0.1),
                    reliability_score=reliability,
                    uncertainty_penalty=uncertainty,
                    downside_risk=downside,
                )
            )

        pairwise_scores: dict[str, float] = {}
        synergy_matrix: dict[str, float] = {}

        for left, right in combinations(scored, 2):
            similarity = self._pairwise_similarity(left.metadata, right.metadata)
            synergy = self._compute_synergy(left.metadata, right.metadata)
            key = f"{left.metadata.name} <-> {right.metadata.name}"
            pairwise_scores[key] = similarity
            synergy_matrix[key] = synergy

            left.redundancy_penalty = max(left.redundancy_penalty, similarity)
            right.redundancy_penalty = max(right.redundancy_penalty, similarity)
            left.synergy_bonus = max(left.synergy_bonus, synergy)
            right.synergy_bonus = max(right.synergy_bonus, synergy)

        for current in scored:
            similarities = [
                self._pairwise_similarity(current.metadata, other.metadata)
                for other in scored
                if other is not current
            ]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            current.diversity_bonus = 1.0 - avg_similarity

        remaining = sorted(scored, key=lambda skill: skill.composite_score, reverse=True)
        selected: list[ScoredSkill] = []

        while remaining and len(selected) < self.max_skills:
            best_index = 0
            best_gain = -1.0
            for idx, candidate in enumerate(remaining):
                gain = self._marginal_gain(candidate, selected)
                if gain > best_gain:
                    best_gain = gain
                    best_index = idx

            if best_gain < 0.05:
                break
            selected.append(remaining.pop(best_index))

        selected = self._apply_style(selected, scored, style)

        if len(selected) > self.max_skills + 1:
            selected = sorted(selected, key=lambda skill: skill.relevance, reverse=True)[: self.max_skills + 1]

        rejected = [skill for skill in scored if skill not in selected]
        selected, rounds = self._refine_selection(selected, rejected)

        if personality:
            selected = self._apply_personality(selected, scored, personality)

        dedup_selected: list[ScoredSkill] = []
        seen_names: set[str] = set()
        for item in selected:
            if item.metadata.name in seen_names:
                continue
            if self.enable_robust_selection and item.reliability_score < self.reliability_floor:
                continue
            if self.enable_robust_selection and item.uncertainty_penalty > self.uncertainty_tolerance:
                continue
            if self.enable_conflict_avoidance and any(
                self._has_conflict(item.metadata, chosen.metadata) for chosen in dedup_selected
            ):
                continue
            if sum(skill.budget_cost for skill in dedup_selected) + item.budget_cost > self.budget_limit:
                continue
            dedup_selected.append(item)
            seen_names.add(item.metadata.name)

        selected = dedup_selected
        rejected = [skill for skill in scored if skill not in selected]

        selected_categories = {skill.metadata.category for skill in selected}
        all_categories = {skill.metadata.category for skill in scored}
        coverage = len(selected_categories) / len(all_categories) if all_categories else 0.0

        redundancy_pairs = [
            self._pairwise_similarity(left.metadata, right.metadata)
            for left, right in combinations(selected, 2)
        ]
        avg_redundancy = sum(redundancy_pairs) / len(redundancy_pairs) if redundancy_pairs else 0.0

        if selected:
            frequencies: dict[SkillCategory, int] = {}
            for skill in selected:
                frequencies[skill.metadata.category] = frequencies.get(skill.metadata.category, 0) + 1
            total_selected = len(selected)
            diversity_shannon = -sum(
                (count / total_selected) * math.log(count / total_selected)
                for count in frequencies.values()
                if count > 0
            )
        else:
            diversity_shannon = 0.0

        diversity_simpson = self._simpson_diversity(selected)

        synergy_pairs = [
            self._compute_synergy(left.metadata, right.metadata)
            for left, right in combinations(selected, 2)
        ]
        total_synergy = sum(synergy_pairs)

        coherence = max(
            0.0,
            min(
                1.0,
                0.55 * coverage
                + 0.25 * (1.0 - avg_redundancy)
                + 0.20 * (total_synergy / max(len(synergy_pairs), 1)),
            ),
        )
        robust_expected, robust_worst_case, avg_uncertainty = self._robust_set_utility(selected)

        return ComplementarityResult(
            selected=selected,
            rejected=rejected,
            pairwise_scores=pairwise_scores,
            synergy_matrix=synergy_matrix,
            total_coverage=coverage,
            total_redundancy=avg_redundancy,
            diversity_shannon=diversity_shannon,
            diversity_simpson=diversity_simpson,
            ensemble_coherence=coherence,
            total_synergy=total_synergy,
            total_budget_used=sum(skill.budget_cost for skill in selected),
            selection_rounds=rounds,
            robust_expected_utility=robust_expected,
            robust_worst_case_utility=robust_worst_case,
            avg_uncertainty=avg_uncertainty,
        )
