"""行为画像更新器 —— 消费反馈数据，递增式更新 LearningBehaviorProfile。"""

from __future__ import annotations

from datetime import datetime

from app.profile.schemas import (
    ComprehensionGap,
    DepthPreference,
    EngagementPattern,
    FormatEffectiveness,
    LearningBehaviorProfile,
    PerNodeStrategy,
)


class BehaviorProfileUpdater:
    """根据单条反馈更新行为画像。

    采用增量更新策略（指数移动平均），避免每次从头计算。
    """

    # 标签 → 格式信号映射
    TAG_FORMAT_SIGNALS: dict[str, dict[str, float]] = {
        # positive → +weight
        "helpful": {"diagram": 0.08, "code": 0.08, "analogy": 0.08, "formula": 0.03, "step_by_step": 0.08},
        "clear":    {"diagram": 0.06, "analogy": 0.08, "step_by_step": 0.08},
        # negative → -weight
        "dont_get":  {"formula": -0.12, "diagram": -0.05, "code": -0.05},
        "too_hard":  {"formula": -0.10, "code": -0.05},
        "too_easy":  {"step_by_step": -0.05, "analogy": -0.05},
        "too_vague": {"diagram": -0.08, "code": -0.08, "step_by_step": -0.05},
    }

    def update(
        self,
        profile: LearningBehaviorProfile,
        *,
        tags: list[str],
        reply_features: dict,
        target_node_id: str,
        intent: str,
    ) -> LearningBehaviorProfile:
        """根据一条反馈更新行为画像。"""
        profile.total_feedback_count += 1
        profile.last_updated = datetime.utcnow()

        # 1. 更新格式有效性
        self._update_formats(profile, tags, reply_features)

        # 2. 更新深度偏好
        self._update_depth(profile, tags)

        # 3. 更新理解缺口
        self._update_gaps(profile, tags, target_node_id)

        # 4. 更新知识点策略
        if target_node_id:
            self._update_node_strategies(profile, tags, target_node_id, reply_features)

        # 5. 更新交互模式
        self._update_engagement(profile, tags, intent)

        return profile

    # ── 子更新逻辑 ──

    def _update_formats(
        self,
        profile: LearningBehaviorProfile,
        tags: list[str],
        features: dict,
    ) -> None:
        """根据标签更新每种格式的有效性分数。"""
        # 从回复特征中提取存在的格式
        present_formats = set()
        if features.get("has_diagram"):
            present_formats.add("diagram")
        if features.get("has_code"):
            present_formats.add("code")
        if features.get("has_formula"):
            present_formats.add("formula")
        if features.get("has_analogy"):
            present_formats.add("analogy")
        if features.get("style") and "step" in str(features.get("style", "")):
            present_formats.add("step_by_step")

        for tag in tags:
            signals = self.TAG_FORMAT_SIGNALS.get(tag, {})
            for fmt, delta in signals.items():
                if fmt not in present_formats and delta > 0:
                    continue  # 正向信号只对实际出现的格式有效
                if fmt not in profile.format_effectiveness:
                    profile.format_effectiveness[fmt] = FormatEffectiveness(format=fmt)
                eff = profile.format_effectiveness[fmt]
                # EMA: new = old*0.9 + signal*0.1
                eff.effectiveness_score = max(0.05, min(0.95,
                    eff.effectiveness_score * 0.9 + 0.5 * 0.1 + delta * 0.5
                ))
                if delta > 0:
                    eff.positive_count += 1
                else:
                    eff.negative_count += 1
                eff.last_updated = datetime.utcnow()

    def _update_depth(
        self,
        profile: LearningBehaviorProfile,
        tags: list[str],
    ) -> None:
        dp = profile.depth_preference
        for tag in tags:
            if tag == "too_easy":
                dp.too_shallow_count += 1
            elif tag == "too_hard" or tag == "dont_get":
                dp.too_deep_count += 1
            elif tag in ("helpful", "clear"):
                dp.just_right_count += 1

        total = dp.too_shallow_count + dp.just_right_count + dp.too_deep_count
        if total >= 5:
            if dp.too_shallow_count > dp.just_right_count and dp.too_shallow_count > dp.too_deep_count:
                dp.preferred_level = "advanced"
            elif dp.too_deep_count > dp.just_right_count:
                dp.preferred_level = "basic"
            else:
                dp.preferred_level = "intermediate"

    def _update_gaps(
        self,
        profile: LearningBehaviorProfile,
        tags: list[str],
        target_node_id: str,
    ) -> None:
        if not target_node_id:
            return
        negative_tags = {"dont_get", "too_hard", "too_vague"}
        active_negatives = [t for t in tags if t in negative_tags]
        if not active_negatives:
            return

        # 查找现有缺口或新建
        gap = None
        for g in profile.comprehension_gaps:
            if g.node_id == target_node_id and not g.resolved:
                gap = g
                break
        if gap is None:
            gap = ComprehensionGap(
                node_id=target_node_id,
                detected_at=datetime.utcnow(),
            )
            profile.comprehension_gaps.append(gap)

        # 添加信号
        for tag in active_negatives:
            gap.signals.append({
                "source": "feedback",
                "type": tag,
                "timestamp": datetime.utcnow().isoformat(),
            })
        # 简易严重度：信号越多越严重，最近信号权重大
        gap.severity = min(1.0, len([s for s in gap.signals if s["source"] == "feedback"]) * 0.2)

    def _update_node_strategies(
        self,
        profile: LearningBehaviorProfile,
        tags: list[str],
        target_node_id: str,
        features: dict,
    ) -> None:
        style = features.get("style", "")
        if not style:
            return

        if target_node_id not in profile.effective_strategies:
            profile.effective_strategies[target_node_id] = PerNodeStrategy(
                node_id=target_node_id,
            )
        st = profile.effective_strategies[target_node_id]
        st.evidence_count += 1
        st.last_updated = datetime.utcnow()

        positive = any(t in ("helpful", "clear") for t in tags)
        negative = any(t in ("dont_get", "too_hard", "too_vague") for t in tags)

        if positive and not negative:
            st.best_approach = style
            st.confidence = min(0.9, st.confidence + 0.1)
        elif negative and not positive:
            st.avoid_approach = style
            st.confidence = min(0.9, st.confidence + 0.15)

    def _update_engagement(
        self,
        profile: LearningBehaviorProfile,
        tags: list[str],
        intent: str,
    ) -> None:
        eng = profile.engagement
        eng.total_feedback_given += 1

        # 追问意图 → follow_up 信号（从 intent 推断）
        if intent in ("clarify_intent",):
            eng.clarification_rate = min(1.0, eng.clarification_rate + 0.05)

        # 节奏偏好（从标签推断）
        if "too_easy" in tags:
            profile.pace_preference = "quick_overview" if profile.pace_preference == "step_by_step" else "balanced"
        elif "want_examples" in tags or "too_vague" in tags:
            profile.pace_preference = "step_by_step"
