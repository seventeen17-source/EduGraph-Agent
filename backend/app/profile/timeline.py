"""成长时间轴构建引擎 —— 从已有数据实时生成时间轴事件和统计数据。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.profile import models as pm
from app.profile.schemas import (
    DailySummary,
    ForgettingNode,
    KnowledgePointMastery,
    LearningStats,
    MonthlySummary,
    ProfileUpdateRecord,
    TimelineEvent,
    TimelineResponse,
    WeeklySummary,
)

# ── 事件构建阈值 ──

SIGNIFICANT_MASTERY_CHANGE = 0.10     # 掌握度变化 >= 10% 才生成事件
MASTERY_MILESTONE = 0.60              # 突破 0.6 → "已掌握"
MASTERY_STRONG = 0.80                 # 突破 0.8 → "熟练掌握"
SAME_TYPE_MERGE_LIMIT = 5             # 同天同类型最多合并 5 条

# 事件图标
EVENT_ICONS: dict[str, str] = {
    "mastery_gain": "📈",
    "mastery_milestone": "🎯",
    "mastery_strong": "⭐",
    "exercise_done": "✏️",
    "concept_started": "▶️",
    "concept_completed": "✅",
    "profile_created": "🔰",
    "profile_updated": "🔄",
    "question_asked": "💬",
    "resource_generated": "📦",
    "feedback_given": "💡",
    "streak_milestone": "🔥",
    "forgetting_warning": "⚠️",
}


# ── 外部接口 ──


class TimelineBuilder:
    """从数据库记录构建时间轴。"""

    def __init__(
        self,
        profile_updates: list[ProfileUpdateRecord],
        node_mastery: dict[str, KnowledgePointMastery],
    ) -> None:
        self.updates = profile_updates
        self.mastery = node_mastery

    def build(
        self,
        days: int = 90,
        additional_events: list[TimelineEvent] | None = None,
    ) -> TimelineResponse:
        """构建完整时间轴响应。"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # 1. 从 ProfileUpdateRecord 生成事件
        events: list[TimelineEvent] = []
        for record in self.updates:
            ts = record.timestamp
            if ts is None:
                continue
            # 对齐时区：去掉 tzinfo 后比较
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            if ts < cutoff:
                continue
            event = self._from_profile_update(record)
            if event is not None:
                events.append(event)

        # 2. 从 node_mastery 快照生成事件
        for node_id, mastery in self.mastery.items():
            if mastery.updated_at is None or mastery.updated_at < cutoff:
                continue
            # 查找该时间点前后的 update event，避免重复
            date_str = mastery.updated_at.strftime("%Y-%m-%d")
            if not self._has_event_on_date(events, date_str, node_id, "mastery"):
                name = mastery.node_name or node_id
                if mastery.mastery_score >= MASTERY_STRONG:
                    events.append(TimelineEvent(
                        date=date_str,
                        type="mastery_strong",
                        icon=EVENT_ICONS["mastery_strong"],
                        title=f"熟练掌握「{name}」",
                        description=f"掌握度达到 {mastery.mastery_score:.0%}",
                        node_id=node_id,
                        node_name=name,
                        score_after=mastery.mastery_score,
                    ))
                elif mastery.mastery_score >= MASTERY_MILESTONE:
                    events.append(TimelineEvent(
                        date=date_str,
                        type="mastery_milestone",
                        icon=EVENT_ICONS["mastery_milestone"],
                        title=f"掌握「{name}」",
                        description=f"掌握度达到 {mastery.mastery_score:.0%}",
                        node_id=node_id,
                        node_name=name,
                        score_after=mastery.mastery_score,
                    ))

        # 3. 合并外部事件
        if additional_events:
            events.extend(additional_events)

        # 4. 按日期排序（新在前）
        events.sort(key=lambda e: (e.date, e.time or ""), reverse=True)

        # 5. 分组聚合
        daily = self._group_by_day(events)
        weeks = self._group_by_week(daily)
        months = self._group_by_month(weeks)

        # 6. 计算统计
        stats = self._compute_stats(daily)

        return TimelineResponse(
            student_id="",
            months=months,
            stats=stats,
            generated_at=datetime.utcnow().isoformat(),
        )

    # ── 事件生成 ──

    def _from_profile_update(self, record: ProfileUpdateRecord) -> TimelineEvent | None:
        """从一条 ProfileUpdateRecord 生成时间轴事件。"""
        date_str = record.timestamp.strftime("%Y-%m-%d")
        time_str = record.timestamp.strftime("%H:%M")
        trigger = record.trigger
        detail = record.trigger_detail or ""
        summary = record.summary or ""
        fields = record.updated_fields or []

        if trigger == "init_dialogue":
            return TimelineEvent(
                date=date_str, time=time_str, type="profile_created",
                icon=EVENT_ICONS["profile_created"],
                title="建立学习画像", description=summary or "通过对话建立了初始学习画像",
            )

        if trigger == "update_dialogue":
            field_names = "、".join(fields[:3]) if fields else "画像"
            return TimelineEvent(
                date=date_str, time=time_str, type="profile_updated",
                icon=EVENT_ICONS["profile_updated"],
                title=f"更新了{field_names}",
                description=summary or detail,
            )

        if trigger == "exercise_result":
            node_id = detail
            node_name = ""
            if node_id and node_id in self.mastery:
                node_name = self.mastery[node_id].node_name or node_id
            return TimelineEvent(
                date=date_str, time=time_str, type="exercise_done",
                icon=EVENT_ICONS["exercise_done"],
                title=f"完成练习「{node_name or node_id or '未知'}」",
                description=summary,
                node_id=node_id, node_name=node_name,
            )

        if trigger == "learning_progress":
            action = "开始学习" if "in_progress" in str(fields) else "完成学习"
            node_id = detail
            node_name = ""
            if node_id and node_id in self.mastery:
                node_name = self.mastery[node_id].node_name or node_id
            return TimelineEvent(
                date=date_str, time=time_str,
                type="concept_completed" if "completed" in str(fields) else "concept_started",
                icon=EVENT_ICONS["concept_completed" if "completed" in str(fields) else "concept_started"],
                title=f"{action}「{node_name or node_id or ''}」",
                description=summary,
                node_id=node_id, node_name=node_name,
            )

        if trigger == "manual_patch":
            return TimelineEvent(
                date=date_str, time=time_str, type="profile_updated",
                icon=EVENT_ICONS["profile_updated"],
                title="手动更新画像", description=detail or summary,
            )

        # 未识别的事件类型 → 仍然展示
        if summary or detail:
            return TimelineEvent(
                date=date_str, time=time_str, type="profile_updated",
                icon=EVENT_ICONS["profile_updated"],
                title=summary[:80] or detail[:80],
                description=detail,
            )

        return None

    # ── 分组聚合 ──

    def _group_by_day(self, events: list[TimelineEvent]) -> list[DailySummary]:
        by_date: dict[str, list[TimelineEvent]] = {}
        for e in events:
            by_date.setdefault(e.date, []).append(e)

        days: list[DailySummary] = []
        for date, day_events in sorted(by_date.items(), reverse=True):
            merged = self._merge_same_type(day_events)
            days.append(DailySummary(
                date=date,
                active_score=self._daily_score(merged),
                event_count=len(merged),
                top_event=merged[0] if merged else None,
                events=merged,
            ))
        return days

    def _group_by_week(self, days: list[DailySummary]) -> list[WeeklySummary]:
        by_week: dict[str, list[DailySummary]] = {}
        for d in days:
            dt = datetime.strptime(d.date, "%Y-%m-%d")
            monday = dt - timedelta(days=dt.weekday())
            week_key = monday.strftime("%Y-%m-%d")
            by_week.setdefault(week_key, []).append(d)

        weeks: list[WeeklySummary] = []
        for wk, wk_days in sorted(by_week.items(), reverse=True):
            monday = datetime.strptime(wk, "%Y-%m-%d")
            # 用周四所在的月份（ISO 周标准）而非周一月份，避免7月初显示为"6月第5周"
            thursday = monday + timedelta(days=3)
            weeks.append(WeeklySummary(
                week_start=wk,
                week_label=f"{thursday.month}月第{(thursday.day - 1) // 7 + 1}周",
                active_days=len([d for d in wk_days if d.active_score > 0]),
                total_score=sum(d.active_score for d in wk_days),
                days=sorted(wk_days, key=lambda d: d.date),
            ))
        return weeks

    def _group_by_month(self, weeks: list[WeeklySummary]) -> list[MonthlySummary]:
        by_month: dict[str, list[WeeklySummary]] = {}
        for w in weeks:
            month_key = w.week_start[:7]
            by_month.setdefault(month_key, []).append(w)

        months: list[MonthlySummary] = []
        for mk, mk_weeks in sorted(by_month.items(), reverse=True):
            year, month = mk.split("-")
            all_days: list[DailySummary] = []
            for wk in mk_weeks:
                all_days.extend(wk.days)

            months.append(MonthlySummary(
                month=mk,
                month_label=f"{year}年{int(month)}月",
                active_days=len([d for d in all_days if d.active_score > 0]),
                weeks=sorted(mk_weeks, key=lambda w: w.week_start),
                new_concepts=sum(
                    1 for d in all_days
                    for e in d.events
                    if e.type in ("concept_started", "concept_completed", "mastery_milestone")
                ),
                exercises_done=sum(
                    1 for d in all_days for e in d.events if e.type == "exercise_done"
                ),
                questions_asked=0,
            ))
        return months

    # ── 统计 ──

    def _compute_stats(self, days: list[DailySummary]) -> LearningStats:
        active_days = [d for d in days if d.active_score > 0]
        total_active = len(active_days)

        current_streak, longest_streak = 0, 0
        today = datetime.utcnow().strftime("%Y-%m-%d")
        streak = 0
        # 按日期升序遍历计算连胜
        sorted_dates = sorted(set(d.date for d in active_days))
        for i, date_str in enumerate(sorted_dates):
            if i == 0:
                streak = 1
            else:
                prev = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d")
                curr = datetime.strptime(date_str, "%Y-%m-%d")
                if (curr - prev).days == 1:
                    streak += 1
                else:
                    streak = 1
            if date_str == today or (i == len(sorted_dates) - 1 and date_str >= today):
                current_streak = streak
            longest_streak = max(longest_streak, streak)
        # 如果今天没有活动，current_streak 就是 0
        if today not in sorted_dates:
            current_streak = 0

        # 本周 vs 上周
        now = datetime.utcnow()
        this_monday = now - timedelta(days=now.weekday())
        last_monday = this_monday - timedelta(days=7)
        this_week_days = len([
            d for d in days
            if d.date >= this_monday.strftime("%Y-%m-%d") and d.active_score > 0
        ])
        last_week_days = len([
            d for d in days
            if last_monday.strftime("%Y-%m-%d") <= d.date < this_monday.strftime("%Y-%m-%d")
            and d.active_score > 0
        ])
        if this_week_days > last_week_days:
            trend = "up"
        elif this_week_days < last_week_days:
            trend = "down"
        else:
            trend = "stable"

        mastered = sum(1 for m in self.mastery.values() if m.mastery_score >= 0.6)
        strong = sum(1 for m in self.mastery.values() if m.mastery_score >= 0.8)

        return LearningStats(
            total_active_days=total_active,
            current_streak=current_streak,
            longest_streak=longest_streak,
            mastered_concepts=mastered,
            strong_concepts=strong,
            this_week_days=this_week_days,
            last_week_days=last_week_days,
            week_trend=trend,
        )

    # ── 工具 ──

    def _daily_score(self, events: list[TimelineEvent]) -> int:
        score = 0
        for e in events:
            if e.type in ("exercise_done", "concept_completed"):
                score += 2
            elif e.type in ("mastery_gain", "mastery_milestone", "mastery_strong", "concept_started"):
                score += 2
            elif e.type in ("question_asked", "feedback_given", "resource_generated"):
                score += 1
            else:
                score += 1
        return min(6, score)

    def _merge_same_type(self, events: list[TimelineEvent]) -> list[TimelineEvent]:
        """合并同类型事件（如同一练习类型的多次完成）。"""
        if len(events) <= 1:
            return events
        by_type: dict[str, list[TimelineEvent]] = {}
        for e in events:
            by_type.setdefault(e.type, []).append(e)

        merged: list[TimelineEvent] = []
        for etype, group in by_type.items():
            if etype == "exercise_done" and len(group) >= 3:
                nodes = [g.node_name or g.node_id for g in group if g.node_name or g.node_id]
                merged.append(TimelineEvent(
                    date=group[0].date, type=etype, icon=EVENT_ICONS[etype],
                    title=f"完成 {len(group)} 道练习题",
                    description="、".join(nodes[:5]) + ("等" if len(nodes) > 5 else ""),
                ))
            else:
                merged.extend(group[:SAME_TYPE_MERGE_LIMIT])
        return merged

    def _has_event_on_date(
        self, events: list[TimelineEvent], date: str, node_id: str, category: str,
    ) -> bool:
        for e in events:
            if e.date == date and e.node_id == node_id:
                if category == "mastery" and e.type.startswith("mastery"):
                    return True
                if category == "exercise" and e.type == "exercise_done":
                    return True
        return False


# ── 遗忘检测 ──


class ForgettingDetector:
    """基于掌握度和上次复习时间，检测即将遗忘的知识点。"""

    def detect(
        self,
        mastery: dict[str, KnowledgePointMastery],
        top_k: int = 5,
    ) -> list[ForgettingNode]:
        now = datetime.utcnow()
        candidates: list[ForgettingNode] = []

        for node_id, m in mastery.items():
            if m.mastery_score >= 0.85:
                continue  # 熟练掌握 → 不易遗忘
            if m.last_practiced_at is None:
                continue

            days_since = (now - m.last_practiced_at).days
            threshold = self._threshold(m.mastery_score)
            if days_since < threshold:
                continue

            urgency = "high" if days_since >= threshold * 1.5 else (
                "medium" if days_since >= threshold * 1.2 else "low"
            )
            forgetting_rate = min(0.8, (days_since - threshold) / threshold * 0.5)

            candidates.append(ForgettingNode(
                node_id=node_id,
                node_name=m.node_name or node_id,
                mastery_score=m.mastery_score,
                days_since_review=days_since,
                estimated_forgetting_rate=round(forgetting_rate, 2),
                threshold_days=threshold,
                urgency=urgency,
            ))

        candidates.sort(key=lambda x: (
            0 if x.urgency == "high" else 1 if x.urgency == "medium" else 2,
            -x.estimated_forgetting_rate,
        ))
        return candidates[:top_k]

    @staticmethod
    def _threshold(mastery_score: float) -> int:
        """动态遗忘阈值（天数）。掌握度越高，遗忘越慢。"""
        if mastery_score >= 0.7:
            return 14
        if mastery_score >= 0.5:
            return 10
        if mastery_score >= 0.3:
            return 7
        return 5
