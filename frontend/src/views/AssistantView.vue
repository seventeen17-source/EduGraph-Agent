<template>
  <div class="page assistant-page">
    <!-- 顶部状态栏 -->
    <div class="assistant-header">
      <div class="header-left">
        <h1>🧠 学习助手</h1>
        <p class="muted">通过对话完成画像更新、知识点讲解、AI 备课、路径规划和学习评估</p>
      </div>
      <div class="header-right">
        <el-tag v-if="assistantStore.running" type="primary" effect="dark" :class="{'pulse-tag': assistantStore.streaming}">
          {{ assistantStore.statusText || '处理中...' }}
        </el-tag>
      </div>
    </div>

    <div class="assistant-layout">
      <!-- 左侧：学生上下文 -->
      <aside class="assistant-sidebar">
        <el-card class="section-card context-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><User /></el-icon>
              <span>我的学习概况</span>
            </div>
          </template>
          <div v-if="profileStore.profile" class="context-content">
            <!-- 完整度 -->
            <div class="completeness-widget">
              <el-progress type="circle" :width="100" :percentage="Math.round(profileStore.completeness * 100)" :stroke-width="8">
                <div class="progress-text">
                  <span class="progress-value">{{ Math.round(profileStore.completeness * 100) }}%</span>
                  <span class="progress-label">完整度</span>
                </div>
              </el-progress>
            </div>

            <!-- 学习目标 -->
            <div class="info-section">
              <div class="info-label">学习目标</div>
              <div class="info-value">{{ profileStore.profile.learning_goal.description || '未设置' }}</div>
            </div>

            <!-- 资源偏好 -->
            <div class="info-section">
              <div class="info-label">偏好资源</div>
              <div class="tag-row">
                <el-tag v-for="type in profileStore.profile.preferences.resource_ranking.slice(0,3)" :key="type" size="small" effect="plain">
                  {{ resourceLabel(type) }}
                </el-tag>
              </div>
            </div>

            <!-- 薄弱点 -->
            <div v-if="profileStore.dashboard?.weak_point_rank.length" class="info-section">
              <div class="info-label">需要加强</div>
              <div class="weak-tags">
                <el-tag v-for="item in profileStore.dashboard.weak_point_rank.slice(0,4)" :key="item.node_id || item.label" type="warning" size="small">
                  {{ displayNodeLabel(item.label || item.node_id) }}
                </el-tag>
              </div>
            </div>

            <!-- 正在学习 -->
            <div v-if="profileStore.profile.progress.in_progress_node_ids.length" class="info-section">
              <div class="info-label">正在学习</div>
              <div class="tag-row">
                <el-tag v-for="uid in profileStore.profile.progress.in_progress_node_ids.slice(0,3)" :key="uid" type="primary" size="small">
                  {{ displayNodeLabel(uid) }}
                </el-tag>
              </div>
            </div>
          </div>
          <el-skeleton v-else :rows="4" />

          <el-divider />
          <div class="quick-actions">
            <el-button size="small" @click="$router.push('/profile/panel')">
              <el-icon><User /></el-icon> 查看画像
            </el-button>
            <el-button size="small" type="primary" plain @click="$router.push('/profile/chat')">
              <el-icon><ChatDotRound /></el-icon> 补充信息
            </el-button>
          </div>
        </el-card>

        <!-- 快捷入口 -->
        <el-card class="section-card quick-entry-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Lightning /></el-icon>
              <span>快捷入口</span>
            </div>
          </template>
          <div class="quick-entry-grid">
            <div class="entry-item" @click="$router.push('/graph')">
              <el-icon :size="24"><Share /></el-icon>
              <span>知识图谱</span>
            </div>
            <div class="entry-item" @click="$router.push('/learning-path')">
              <el-icon :size="24"><Guide /></el-icon>
              <span>学习路径</span>
            </div>
            <div class="entry-item" @click="$router.push('/resources')">
              <el-icon :size="24"><Document /></el-icon>
              <span>生成资源</span>
            </div>
            <div class="entry-item" @click="$router.push('/exercise')">
              <el-icon :size="24"><EditPen /></el-icon>
              <span>开始练习</span>
            </div>
          </div>
        </el-card>
      </aside>

      <!-- 中间：主对话区 -->
      <main class="assistant-main">
        <el-card class="section-card chat-card" shadow="never">
          <!-- 消息列表 -->
          <div class="messages-area" ref="messagesRef" @scroll="onScroll">
            <div v-if="loadingMore" class="loading-more">
              <span class="loading-text">正在加载历史...</span>
            </div>
            <div v-if="!assistantStore.messages.length" class="welcome-area">
              <div class="welcome-icon">🧠</div>
              <h2>你好！我是你的 AI 学习助手</h2>
              <p class="muted">我可以帮你完成以下学习任务：</p>
              <div class="suggestion-list">
                <div class="suggestion-item" @click="quickAsk('讲解反向传播')">
                  <span class="suggestion-icon">📖</span>
                  <span>讲解知识点（如反向传播）</span>
                </div>
                <div class="suggestion-item" @click="quickAsk('生成神经网络学习资源')">
                  <span class="suggestion-icon">📊</span>
                  <span>生成学习资源</span>
                </div>
                <div class="suggestion-item" @click="quickAsk('帮我规划学习路径')">
                  <span class="suggestion-icon">🗺️</span>
                  <span>规划学习路径</span>
                </div>
                <div class="suggestion-item" @click="quickAsk('查看我的薄弱点')">
                  <span class="suggestion-icon">🎯</span>
                  <span>诊断薄弱点</span>
                </div>
              </div>
              <el-collapse v-if="authStore.isDemoUser" class="demo-guide">
                <el-collapse-item title="🎬 7分钟演示路线（点击展开）" name="demo">
                  <div class="demo-steps">
                    <div class="demo-step" @click="quickAsk('我想学习机器学习，但对梯度下降不太理解')">
                      <span class="step-num">1</span>
                      <span>向助手提问 → 触发画像更新与概念讲解</span>
                    </div>
                    <div class="demo-step" @click="$router.push('/graph')">
                      <span class="step-num">2</span>
                      <span>进入知识图谱 → 查看知识点前置关系与状态</span>
                    </div>
                    <div class="demo-step" @click="quickAsk('请为梯度下降生成学习资源')">
                      <span class="step-num">3</span>
                      <span>生成多类型备课内容 → 自动存入知识中心</span>
                    </div>
                    <div class="demo-step" @click="$router.push('/exercise')">
                      <span class="step-num">4</span>
                      <span>进入练习测试 → 做题并查看反馈</span>
                    </div>
                    <div class="demo-step" @click="$router.push('/learning-path')">
                      <span class="step-num">5</span>
                      <span>查看学习路径 → 智能诊断 + 拓扑排序推荐</span>
                    </div>
                    <div class="demo-step" @click="$router.push('/assessment')">
                      <span class="step-num">6</span>
                      <span>查看评估报告 → 掌握度雷达图 + 趋势分析</span>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>

            <!-- 对话消息 -->
            <div v-for="msg in assistantStore.messages" :key="msg.id" class="message-wrapper" :class="msg.role">
              <el-avatar v-if="msg.role === 'assistant'" :size="36" class="message-avatar assistant">
                🧠
              </el-avatar>
              <div class="message-bubble">
                <div class="bubble-header">
                  <span class="sender-name">{{ msg.role === 'user' ? profileStore.displayName : '学习助手' }}</span>
                  <span class="message-time">{{ formatTime(msg.created_at) }}</span>
                </div>
                <div class="bubble-content markdown-body" v-html="renderMarkdown(
                  msg.role === 'assistant' && msg === assistantStore.messages[assistantStore.messages.length - 1]
                    ? (typewriterActive ? typewriterDisplay : msg.content)
                    : msg.content
                )"></div>
                <div v-if="msg.role === 'assistant' && msg.agent_trace?.length" class="bubble-trace">
                  <span class="trace-count">✓ 已完成 {{ nodeCount(msg.agent_trace) }} 个处理步骤</span>
                </div>
                <div v-if="msg.role === 'assistant' && msg.resource_record_id" class="bubble-resource-link">
                  <div>
                    <div class="resource-link-title">本次生成的学习资源已保存</div>
                    <div class="resource-link-desc">
                      {{ msg.resource_has_exercises ? '已生成练习题，可以直接开始作答。' : '可在知识中心查看题目、答案、解析和证据来源。' }}
                    </div>
                  </div>
                  <div class="resource-link-actions">
                    <el-button v-if="msg.resource_has_exercises" type="primary" size="small" @click="startExerciseFromAssistant(msg.resource_record_id)">
                      立即开始作答
                    </el-button>
                    <el-button type="primary" plain size="small" @click="openResourceRecord(msg.resource_record_id)">
                      查看资源
                    </el-button>
                  </div>
                </div>

                <!-- 下一步建议 -->
                <div
                  v-if="msg.role === 'assistant' && msg.suggested_next_actions && msg.suggested_next_actions.length"
                  class="bubble-next-actions"
                >
                  <div class="next-actions-title">💡 下一步建议</div>
                  <div class="next-actions-list">
                    <template v-for="(action, idx) in msg.suggested_next_actions" :key="idx">
                      <el-button
                        v-if="action.route"
                        size="small"
                        type="primary"
                        plain
                        @click="handleSuggestedAction(action)"
                      >
                        {{ action.label }}
                      </el-button>
                      <span v-else class="next-action-hint">
                        {{ action.label }}
                      </span>
                    </template>
                  </div>
                </div>

                <!-- 快速反馈标签（仅 assistant 消息，回复完成后显示） -->
                <div
                  v-if="msg.role === 'assistant' && !assistantStore.running"
                  class="feedback-row"
                >
                  <div class="feedback-tags">
                    <span
                      v-for="tag in quickFeedbackTags"
                      :key="tag.key"
                      class="feedback-tag"
                      :class="{
                        active: isFeedbackTagActive(msg.id, tag.key),
                        submitted: feedbackState(msg.id)?.submitted,
                      }"
                      @click="toggleFeedback(msg.id, tag.key, msg.intent, msg.target_node_id)"
                    >
                      <span class="tag-icon">{{ tag.icon }}</span>
                      <span class="tag-label">{{ tag.label }}</span>
                    </span>
                  </div>
                  <!-- 自由文本（选了标签后展开） -->
                  <div
                    v-if="showFeedbackText(msg.id)"
                    class="feedback-text-row"
                  >
                    <input
                      v-model="feedbackTextInputs[msg.id]"
                      class="feedback-text-input"
                      placeholder="补充说明（可选）..."
                      @keyup.enter="toggleFeedback(msg.id, '', msg.intent, msg.target_node_id, true)"
                    />
                    <el-button
                      size="small"
                      type="primary"
                      text
                      @click="toggleFeedback(msg.id, '', msg.intent, msg.target_node_id, true)"
                    >
                      提交
                    </el-button>
                  </div>
                  <div v-if="feedbackState(msg.id)?.submitted" class="feedback-done">
                    已反馈 — {{ (feedbackState(msg.id)?.tags || []).map(t => quickFeedbackTags.find(q => q.key === t)?.label).join('、') }}
                  </div>
                  <div v-if="feedbackState(msg.id)?.adaptationSummary" class="feedback-adaptation">
                    {{ feedbackState(msg.id)?.adaptationSummary }}
                  </div>
                  <div v-if="feedbackState(msg.id)?.actionResult" class="feedback-action-response">
                    <span class="action-icon">🔄</span>
                    <span class="action-text">{{ feedbackState(msg.id)?.actionResult }}</span>
                  </div>
                </div>
              </div>
              <el-avatar v-if="msg.role === 'user'" :size="36" class="message-avatar user">
                {{ profileStore.displayName?.charAt(0) || '我' }}
              </el-avatar>
            </div>

            <!-- 流式处理中 -->
            <div v-if="assistantStore.streaming" class="message-wrapper assistant">
              <el-avatar :size="36" class="message-avatar assistant">🧠</el-avatar>
              <div class="message-bubble streaming-bubble">
                <div class="bubble-header">
                  <span class="sender-name">学习助手</span>
                  <el-tag v-if="assistantStore.currentStreamNode" type="primary" size="small" class="pulse-tag">
                    {{ traceNodeLabel(assistantStore.currentStreamNode) }}
                  </el-tag>
                </div>
                <!-- 实时节点进度条 -->
                <div class="stream-progress">
                  <div
                    v-for="item in assistantStore.activeLiveNodes"
                    :key="item.node"
                    class="stream-node-dot"
                    :class="item.status"
                    :title="item.label"
                  />
                </div>
                <div class="bubble-content typing">
                  <span class="typing-dots">{{ assistantStore.statusText }}</span>
                </div>
              </div>
            </div>

            <!-- 非流式处理中 -->
            <div v-else-if="assistantStore.running && !assistantStore.streaming" class="message-wrapper assistant">
              <el-avatar :size="36" class="message-avatar assistant">🧠</el-avatar>
              <div class="message-bubble">
                <div class="bubble-header">
                  <span class="sender-name">学习助手</span>
                </div>
                <div class="bubble-content typing">
                  <span class="typing-dots">{{ assistantStore.statusText || '思考中...' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 错误提示 -->
          <ErrorAlert v-if="assistantStore.error" :message="assistantStore.error" />

          <!-- 澄清选项 -->
          <div v-if="assistantStore.needsClarification && assistantStore.clarificationOptions.length" class="clarification-area">
            <div class="clarify-title"><el-icon><QuestionFilled /></el-icon> {{ assistantStore.clarificationQuestion || '请选择一个选项：' }}</div>
            <div class="clarify-options">
              <div
                v-for="opt in assistantStore.clarificationOptions"
                :key="opt.value"
                class="clarify-option"
                @click="clarifyAnswer(opt)"
              >
                <span class="clarify-label">{{ opt.label }}</span>
                <span class="clarify-desc">{{ opt.description }}</span>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="input-area">
            <el-input
              v-model="inputText"
              type="textarea"
              :rows="2"
              resize="none"
              :disabled="assistantStore.running"
              placeholder="输入你的学习需求，如：帮我讲解反向传播，最好有图解和代码"
              @keydown.ctrl.enter.prevent="streamSend"
            />
            <div class="input-actions">
              <el-button
                v-if="assistantStore.streaming"
                type="danger"
                size="large"
                @click="assistantStore.cancelStream()"
              >
                <el-icon><Close /></el-icon> 取消
              </el-button>
              <el-button
                v-else
                type="primary"
                size="large"
                :loading="assistantStore.running"
                @click="streamSend"
              >
                <el-icon><VideoPlay /></el-icon> 发送（流式）
              </el-button>
              <el-button
                v-if="!assistantStore.running"
                size="large"
                @click="send"
              >
                <el-icon><Promotion /></el-icon> 普通发送
              </el-button>
            </div>
          </div>
        </el-card>
      </main>

      <!-- 右侧：动态行动面板 -->
      <aside class="assistant-panel">
        <!-- LangGraph 实时编排流程 -->
        <AgentTracePanel
          v-if="assistantStore.streaming || assistantStore.activeLiveNodes.length > 0"
          :nodes="assistantStore.liveTrace"
          :is-running="assistantStore.streaming"
          :current-running-node="assistantStore.currentStreamNode"
        />

        <!-- 非流式静态处理过程（兼容） -->
        <el-card v-else-if="assistantStore.agentTrace.length" class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Cpu /></el-icon>
              <span>处理过程</span>
            </div>
          </template>
          <div class="trace-timeline">
            <div v-for="item in assistantStore.agentTrace" :key="item.node + item.created_at" class="trace-step">
              <div class="step-dot" :class="item.status"></div>
              <div class="step-content">
                <span class="step-name">{{ traceNodeLabel(item.node) }}</span>
                <span class="step-summary">{{ traceSummaryLabel(item.summary) }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 流式实时质量评分 -->
        <el-card v-if="assistantStore.streaming && (assistantStore.partialEvidenceScore !== null || assistantStore.partialResourceScore !== null)" class="section-card quality-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>实时质量</span>
              <span class="live-dot" />
            </div>
          </template>
          <div class="score-row" v-if="assistantStore.partialEvidenceScore !== null">
            <span class="score-label">证据质量</span>
            <el-progress :percentage="Math.round(assistantStore.partialEvidenceScore * 100)" :stroke-width="8" :color="scoreColor(assistantStore.partialEvidenceScore)" :text-inside="true" />
          </div>
          <div class="score-row" v-if="assistantStore.partialResourceScore !== null">
            <span class="score-label">资源质量</span>
            <el-progress :percentage="Math.round(assistantStore.partialResourceScore * 100)" :stroke-width="8" :color="scoreColor(assistantStore.partialResourceScore)" :text-inside="true" />
          </div>
        </el-card>

        <!-- 证据包 -->
        <EvidencePanel v-if="assistantStore.evidence" :evidence="assistantStore.evidence" />

        <!-- 本轮生成资源 -->
        <el-card v-if="assistantStore.resourceRecordId || generatedResourceSummary.length" class="section-card generated-resource-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>本轮生成资源</span>
            </div>
          </template>
          <div v-if="generatedResourceSummary.length" class="generated-resource-list">
            <div v-for="item in generatedResourceSummary" :key="item.label" class="generated-resource-item">
              <span class="resource-kind">{{ item.label }}</span>
              <span class="resource-count">{{ item.count }}</span>
            </div>
          </div>
          <div v-else class="resource-link-desc">资源已保存到知识中心，可继续查看详情。</div>
          <el-button
            v-if="assistantStore.resourceRecordId"
            type="primary"
            class="open-resource-button"
            @click="openResourceRecord(assistantStore.resourceRecordId)"
          >
            打开刚生成的资源
          </el-button>
        </el-card>

        <!-- 历史记忆 -->
        <MemoryPanel
          v-if="assistantStore.relevantMemories.length > 0"
          :memories="assistantStore.relevantMemories"
        />

        <!-- 路径计划 -->
        <el-card v-if="assistantStore.pathPlan" class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Guide /></el-icon>
              <span>{{ localizeText(assistantStore.pathPlan.title) }}</span>
              <el-tag size="small" type="primary">{{ pathModeLabel(assistantStore.pathPlan.mode) }}</el-tag>
            </div>
          </template>
          <div class="path-nodes">
            <div v-for="node in assistantStore.pathPlan.nodes" :key="node.node_id" class="path-node-item" :class="node.status">
              <el-tag :type="pathStatusTag(node.status)" size="small">{{ displayNodeLabel(node.label || node.node_id) }}</el-tag>
              <span class="node-reason">{{ localizeText(node.reason) }}</span>
            </div>
          </div>
          <el-divider />
          <div class="path-reasons">
            <div v-for="reason in assistantStore.pathPlan.reasons" :key="reason" class="reason-item">
              {{ localizeText(reason) }}
            </div>
          </div>
        </el-card>

        <!-- 行动卡片 -->
        <el-card v-if="assistantStore.actions.length" class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><Promotion /></el-icon>
              <span>可执行的操作</span>
            </div>
          </template>
          <div class="action-cards">
            <div
              v-for="action in assistantStore.actions"
              :key="action.type"
              class="action-card-item"
              @click="handleAction(action)"
            >
              <div class="action-label">{{ action.label }}</div>
              <div class="action-desc">{{ action.description }}</div>
            </div>
          </div>
        </el-card>

        <!-- 质量评分 -->
        <el-card v-if="assistantStore.evidenceQualityScore !== null || assistantStore.resourceQualityScore !== null" class="section-card quality-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>质量评分</span>
            </div>
          </template>
          <div class="score-row" v-if="assistantStore.evidenceQualityScore !== null">
            <span class="score-label">证据质量</span>
            <el-progress :percentage="Math.round(assistantStore.evidenceQualityScore * 100)" :stroke-width="8" :color="scoreColor(assistantStore.evidenceQualityScore)" :text-inside="true" />
          </div>
          <div class="score-row" v-if="assistantStore.resourceQualityScore !== null">
            <span class="score-label">资源质量</span>
            <el-progress :percentage="Math.round(assistantStore.resourceQualityScore * 100)" :stroke-width="8" :color="scoreColor(assistantStore.resourceQualityScore)" :text-inside="true" />
          </div>
        </el-card>

        <!-- 反思结果 -->
        <el-card v-if="assistantStore.reflection" class="section-card reflection-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><RefreshRight /></el-icon>
              <span>学习反思</span>
              <el-tag v-if="assistantStore.needsRefinement" type="warning" size="small">需改进</el-tag>
              <el-tag v-else type="success" size="small">已满足</el-tag>
            </div>
          </template>
          <p class="reflection-text">{{ assistantStore.reflection }}</p>
          <div v-if="assistantStore.needsRefinement" class="refinement-action">
            <el-button type="warning" size="small" @click="retryResources">🔄 重新生成资源</el-button>
          </div>
        </el-card>

        <!-- 练习反馈 -->
        <el-card v-if="assistantStore.exerciseFeedback" class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><EditPen /></el-icon>
              <span>练习讲解</span>
            </div>
          </template>
          <p>{{ assistantStore.exerciseFeedback.summary }}</p>
          <div v-if="assistantStore.exerciseFeedback.likely_causes.length" class="feedback-section">
            <div class="section-title">可能原因</div>
            <ul>
              <li v-for="cause in assistantStore.exerciseFeedback.likely_causes" :key="cause">{{ cause }}</li>
            </ul>
          </div>
          <div v-if="assistantStore.exerciseFeedback.hints.length" class="feedback-section">
            <div class="section-title">学习提示</div>
            <ul>
              <li v-for="hint in assistantStore.exerciseFeedback.hints" :key="hint">{{ hint }}</li>
            </ul>
          </div>
        </el-card>

        <!-- 画像更新 -->
        <el-card v-if="Object.keys(assistantStore.profileDelta).length" class="section-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon><CircleCheck /></el-icon>
              <span>画像更新</span>
            </div>
          </template>
          <div v-if="assistantStore.profileDelta.updated_dimensions?.length" class="tag-row">
            <el-tag v-for="dim in assistantStore.profileDelta.updated_dimensions" :key="dim" type="success">
              {{ dim }}
            </el-tag>
          </div>
          <div v-if="assistantStore.profileDelta.completeness" class="muted small">
            画像完整度：{{ Math.round(assistantStore.profileDelta.completeness * 100) }}%
          </div>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import {
  ChatDotRound,
  CircleCheck,
  Close,
  Cpu,
  DataAnalysis,
  Document,
  EditPen,
  Guide,
  Lightning,
  Promotion,
  QuestionFilled,
  RefreshRight,
  Share,
  User,
  VideoPlay
} from '@element-plus/icons-vue'

import EvidencePanel from '@/components/graphrag/EvidencePanel.vue'
import AgentTracePanel from '@/components/assistant/AgentTracePanel.vue'
import MemoryPanel from '@/components/assistant/MemoryPanel.vue'
import ErrorAlert from '@/components/common/ErrorAlert.vue'
import { useAssistantStore } from '@/stores/assistant'
import { useAuthStore } from '@/stores/auth'
import { useProfileStore } from '@/stores/profile'
import { displayNodeLabel, displaySourceLabel, localizeText, resourceLabel } from '@/utils/format'

const authStore = useAuthStore()
import type { AssistantAction, AssistantTraceItem, SuggestedNextAction } from '@/types/assistant'

const router = useRouter()
const assistantStore = useAssistantStore()
const profileStore = useProfileStore()
const inputText = ref('')
const messagesRef = ref<HTMLElement>()
const loadingMore = ref(false)

// === 打字机效果 ===
const typewriterActive = ref(false)
const typewriterTarget = ref('')
const typewriterDisplay = ref('')
let typewriterTimer: ReturnType<typeof setInterval> | null = null

function scrollToBottom(smooth = true) {
  if (!messagesRef.value) return
  if (smooth) {
    messagesRef.value.scrollTo({
      top: messagesRef.value.scrollHeight,
      behavior: 'smooth'
    })
  } else {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

function startTypewriter(fullText: string) {
  stopTypewriter()
  typewriterTarget.value = fullText
  typewriterDisplay.value = ''
  typewriterActive.value = true
  const charsPerTick = 4
  let pos = 0
  typewriterTimer = setInterval(() => {
    pos += charsPerTick
    if (pos >= fullText.length) {
      typewriterDisplay.value = fullText
      stopTypewriter()
    } else {
      typewriterDisplay.value = fullText.slice(0, pos)
    }
    scrollToBottom(false)
  }, 16)
}

function stopTypewriter() {
  typewriterActive.value = false
  if (typewriterTimer) {
    clearInterval(typewriterTimer)
    typewriterTimer = null
  }
}

// 监听最后一条 assistant 消息的内容，触发打字机
watch(
  () => {
    const msgs = assistantStore.messages
    if (msgs.length === 0) return ''
    const last = msgs[msgs.length - 1]
    return last.role === 'assistant' ? last.content : ''
  },
  (content, _old) => {
    // 流式结束 + 有新内容 → 启动打字机
    if (content && !assistantStore.streaming && !assistantStore.running) {
      startTypewriter(content)
    }
  },
)

// 流式进行中 → 取消打字机（因为还没有最终回复）
watch(() => assistantStore.streaming, (streaming) => {
  if (streaming) {
    stopTypewriter()
    typewriterDisplay.value = ''
  }
})

const md = new MarkdownIt({
  html: false,
  breaks: false,
  linkify: true,
  typographer: true,
})

function renderMarkdown(content: string) {
  const cleaned = localizeText(content).replace(/\n{3,}/g, '\n\n')
  return md.render(cleaned)
}

// 最后一条 assistant 消息的显示内容（打字机或完整）
const lastAssistantContent = computed(() => {
  const msgs = assistantStore.messages
  if (msgs.length === 0) return ''
  const last = msgs[msgs.length - 1]
  if (last.role !== 'assistant') return ''
  if (typewriterActive.value) return typewriterDisplay.value
  return last.content
})

const hasMore = computed(() => assistantStore.hasMoreMessages)

const generatedResourceSummary = computed(() => {
  const resources = assistantStore.resources
  if (!resources) return []
  const items: Array<{ label: string; count: string }> = []
  if (resources.exercises?.length) items.push({ label: '练习题', count: `${resources.exercises.length} 道` })
  if (resources.document) items.push({ label: '讲解文档', count: '1 份' })
  if (resources.mindmap) items.push({ label: '思维导图', count: '1 张' })
  if (resources.video_script) items.push({ label: '视频脚本', count: '1 份' })
  if (resources.code_case) items.push({ label: '代码案例', count: '1 个' })
  if (resources.image) items.push({ label: '教学图片', count: '1 张' })
  return items
})

const preferredResourceTab = computed(() => {
  const resources = assistantStore.resources
  if (resources?.exercises?.length) return 'exercise'
  if (resources?.document) return 'document'
  if (resources?.mindmap) return 'mindmap'
  if (resources?.video_script) return 'video'
  if (resources?.code_case) return 'code'
  if (resources?.image) return 'image'
  return 'exercise'
})

// 页面加载时加载历史
if (authStore.isAuthenticated && !profileStore.profile) {
  profileStore.studentId = authStore.studentId
  profileStore.displayName = authStore.displayName
  profileStore.loadCurrentStudent().catch(() => {})
}
assistantStore.loadHistory(authStore.studentId || profileStore.studentId)

// 自动滚动
watch(() => assistantStore.messages.length, async () => {
  await nextTick()
  scrollToBottom()
})

// 上划加载更多历史
async function onScroll(e: Event) {
  const el = e.target as HTMLElement
  const atTop = el.scrollTop < 100
  if (atTop && !loadingMore.value && hasMore.value) {
    loadingMore.value = true
    const beforeHeight = el.scrollHeight
    await assistantStore.loadMoreHistory(profileStore.studentId)
    await nextTick()
    if (messagesRef.value) {
      const newHeight = messagesRef.value.scrollHeight
      messagesRef.value.scrollTop = newHeight - beforeHeight
    }
    loadingMore.value = false
  }
}

async function send() {
  const text = inputText.value.trim()
  if (!text || assistantStore.running) return
  inputText.value = ''
  stopTypewriter()
  try {
    await assistantStore.sendMessage(profileStore.studentId, text)
  } catch {}
}

async function streamSend() {
  const text = inputText.value.trim()
  if (!text || assistantStore.running) return
  inputText.value = ''
  stopTypewriter()
  try {
    await assistantStore.streamMessage(profileStore.studentId, text)
  } catch {}
}

function quickAsk(text: string) {
  inputText.value = text
  send()
}

onMounted(() => {
  const prefill = sessionStorage.getItem('assistant_prefill')
  if (prefill) {
    inputText.value = prefill
    sessionStorage.removeItem('assistant_prefill')
  }
})

function handleAction(action: AssistantAction) {
  if (!action.route) return
  const query: Record<string, string> = {}
  if (action.node_id) query.node_id = action.node_id
  if (action.resource_record_id) query.record_id = action.resource_record_id
  for (const [k, v] of Object.entries(action.query)) {
    if (v !== undefined && v !== null) query[k] = String(v)
  }
  router.push({ path: action.route, query })
}

function handleSuggestedAction(action: SuggestedNextAction) {
  if (!action.route) return
  const query: Record<string, string> = {}
  for (const [k, v] of Object.entries(action.query || {})) {
    if (v !== undefined && v !== null && v !== '') query[k] = String(v)
  }
  router.push({ path: action.route, query })
}

function openResourceRecord(recordId?: string | null) {
  if (!recordId) return
  router.push({
    path: '/knowledge-center',
    query: {
      record_id: recordId,
      tab: preferredResourceTab.value,
    },
  })
}

function startExerciseFromAssistant(resourceId: string) {
  router.push({ path: '/exercise', query: { resource_id: resourceId } })
}

function nodeCount(trace: AssistantTraceItem[]) {
  return trace.filter((t) => t.status === 'done').length
}

function formatTime(timeStr: string) {
  if (!timeStr) return ''
  // 数据库存的是 UTC naive datetime，浏览器当本地解析差了 8 小时
  // 手动加 8 小时对齐北京时间
  const date = new Date(timeStr)
  date.setHours(date.getHours() + 8)
  const now = new Date()
  now.setHours(now.getHours() + 8)
  const todayStr = now.toDateString()
  const dateStr = date.toDateString()
  if (dateStr === todayStr) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const _nodeLabels: Record<string, string> = {
  load_context: '加载画像',
  understand_intent: '意图识别',
  retrieve_evidence: '检索证据',
  evaluate_evidence: '评估证据',
  expand_evidence: '扩展证据',
  generate_resources: '生成资源',
  reflect_on_resources: '资源反思',
  plan_learning_path: '规划路径',
  compose_response: '整理回复',
  update_profile: '更新画像',
  record_progress: '记录进度',
  explain_exercise: '讲解练习',
  review_assessment: '评估复盘',
  general_tutor: '答疑',
  error_recovery: '错误恢复',
  'hybrid_rag:prepare_query': '整理检索问题',
  'hybrid_rag:resolve_learning_target': '定位学习目标',
  'hybrid_rag:retrieve_graph_context': '检索图谱证据',
  'hybrid_rag:retrieve_semantic_context': '检索课程语义证据',
  'hybrid_rag:retrieve_memory_context': '检索学生记忆',
  'hybrid_rag:fuse_canonical_evidence': '融合规范证据',
  'hybrid_rag:grade_evidence': '评估证据质量',
  'hybrid_rag:finalize_evidence': '生成证据包',
}

function traceNodeLabel(node: string) {
  return _nodeLabels[node] || localizeTraceText(node)
}

function traceSummaryLabel(summary?: string) {
  return localizeTraceText(summary || '')
}

function localizeTraceText(value: string) {
  let text = value || ''
  const replacements: Array<[RegExp, string]> = [
    [/concept_explain/g, '知识点讲解'],
    [/resource_generate/g, '资源生成'],
    [/exercise_help/g, '练习辅导'],
    [/path_plan/g, '路径规划'],
    [/general_learning_chat/g, '学习问答'],
    [/profile_update/g, '画像更新'],
    [/assessment_review/g, '评估复盘'],
    [/retrieve_memory/g, '检索记忆'],
    [/hybrid_rag:/g, '混合检索：'],
    [/prepare_query/g, '整理问题'],
    [/resolve_learning_target/g, '定位学习目标'],
    [/retrieve_graph_context/g, '检索图谱证据'],
    [/retrieve_semantic_context/g, '检索课程语义证据'],
    [/retrieve_memory_context/g, '检索学生记忆'],
    [/fuse_canonical_evidence/g, '融合规范证据'],
    [/grade_evidence/g, '评估证据质量'],
    [/finalize_evidence/g, '生成证据包'],
    [/ml_backpropagation/g, '反向传播'],
    [/ml_gradient_descent/g, '梯度下降'],
    [/ml_multilayer_neural_network/g, '多层神经网络'],
    [/ml_kmeans/g, 'K-Means'],
    [/code_backprop_demo/g, '反向传播代码案例'],
    [/Neo4j canonical evidence/g, 'Neo4j 规范证据'],
    [/canonical evidence/g, '规范证据'],
    [/EvidencePackage/g, '证据包'],
    [/HybridRAG/g, '混合检索'],
    [/FAQ/g, '常见问题'],
    [/coverage/g, '覆盖度'],
    [/relevance/g, '相关性'],
  ]
  for (const [pattern, replacement] of replacements) {
    text = text.replace(pattern, replacement)
  }
  return localizeText(text)
}

function pathModeLabel(mode: string) {
  const labels: Record<string, string> = {
    current_goal: '当前目标',
    gap_filling: '查漏补缺',
    exam_review: '考前复习',
    project_practice: '项目实战',
    free_exploration: '自由探索',
  }
  return labels[mode] || displaySourceLabel(mode, '路径模式')
}

function pathStatusTag(status: string) {
  const tags: Record<string, string> = {
    recommended: 'primary',
    in_progress: 'warning',
    mastered: 'success',
    needs_review: 'danger',
    added_by_mistake: 'info',
    skipped_by_student: 'info',
  }
  return tags[status] || 'primary'
}

function clarifyAnswer(opt: any) {
  // 选择澄清选项后，用选项 label 作为消息发送
  inputText.value = opt.label
  send()
}

// === 快速反馈 ===
const quickFeedbackTags = [
  { key: 'helpful',  label: '有帮助', icon: '✅' },
  { key: 'clear',    label: '很清楚', icon: '💡' },
  { key: 'dont_get', label: '没看懂', icon: '🤔' },
  { key: 'too_hard', label: '太难',   icon: '😰' },
  { key: 'too_easy', label: '太简单', icon: '🥱' },
  { key: 'want_examples', label: '想要例子', icon: '📋' },
  { key: 'want_summary',  label: '想要总结', icon: '📝' },
  { key: 'too_vague', label: '不够具体', icon: '🔍' },
]

const feedbackTextInputs = ref<Record<string, string>>({})

function feedbackState(msgId: string) {
  return assistantStore.messageFeedback[msgId]
}

function isFeedbackTagActive(msgId: string, tag: string) {
  const fb = assistantStore.messageFeedback[msgId]
  return fb?.tags.includes(tag) || false
}

function showFeedbackText(msgId: string) {
  const fb = assistantStore.messageFeedback[msgId]
  return fb && fb.tags.length > 0 && !fb.submitted
}

function toggleFeedback(msgId: string, tag: string, intent: string, targetNodeId: string, submitText = false) {
  if (submitText) {
    const text = feedbackTextInputs.value[msgId]?.trim() || ''
    if (text) assistantStore.setFeedbackText(msgId, text)
    assistantStore.submitMessageFeedback(msgId, intent, targetNodeId)
    return
  }
  if (tag) {
    assistantStore.toggleFeedbackTag(msgId, tag)
    // 选了标签后自动聚焦文本输入
    if (!feedbackTextInputs.value[msgId]) feedbackTextInputs.value[msgId] = ''
  }
}

function scoreColor(score: number) {
  if (score >= 0.8) return '#10b981'
  if (score >= 0.5) return '#f59e0b'
  return '#ef4444'
}

function retryResources() {
  const nodeId = assistantStore.evidence?.resolved_uid || ''
  const refineMsg = `请重新生成关于${displayNodeLabel(nodeId)}的更详细的学习资源`
  inputText.value = refineMsg
  send()
}
</script>

<style scoped>
.assistant-page {
  max-width: 1600px;
}

.assistant-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.assistant-header h1 {
  margin: 0 0 6px;
  font-size: 28px;
}

.pulse-tag {
  animation: pulse 1s infinite;
}

.assistant-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 380px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 1400px) {
  .assistant-layout {
    grid-template-columns: 240px minmax(0, 1fr) 320px;
    gap: 16px;
  }
}

@media (max-width: 1200px) {
  .assistant-layout {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
  .assistant-sidebar {
    display: none;
  }
}

@media (max-width: 768px) {
  .assistant-layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .assistant-panel {
    display: none;
  }
}

.assistant-sidebar,
.assistant-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.context-card :deep(.el-card__body) {
  padding: 20px;
}

.completeness-widget {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.progress-text {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.progress-value {
  font-size: 26px;
  font-weight: 700;
  color: #4f46e5;
}

.progress-label {
  font-size: 11px;
  color: #94a3b8;
}

.info-section {
  margin-top: 16px;
}

.info-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.info-value {
  font-size: 14px;
  color: #1e293b;
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.quick-entry-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.entry-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 12px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.entry-item:hover {
  background: #eef2ff;
  transform: translateY(-2px);
}

.entry-item span {
  font-size: 12px;
  color: #64748b;
}

.chat-card {
  min-height: 600px;
  display: flex;
  flex-direction: column;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  max-height: 500px;
  scrollbar-width: thin;
  scrollbar-color: #c4b5fd #f1f5f9;
}

.messages-area::-webkit-scrollbar {
  width: 6px;
}

.messages-area::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.messages-area::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #c4b5fd, #8b5cf6);
  border-radius: 3px;
}

.messages-area::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, #a78bfa, #7c3aed);
}

.welcome-area {
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.welcome-area h2 {
  margin: 0 0 12px;
  color: #1e293b;
}

.suggestion-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-width: 500px;
  margin: 24px auto 0;
  text-align: left;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-item:hover {
  background: #eef2ff;
  transform: translateX(4px);
}

.suggestion-icon {
  font-size: 20px;
}

.message-wrapper {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}

.message-wrapper.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  font-size: 14px;
}

.message-avatar.assistant {
  background: linear-gradient(135deg, #818cf8, #4f46e5);
}

.message-bubble {
  max-width: 75%;
  padding: 16px 20px;
  border-radius: 20px;
  background: linear-gradient(145deg, #ffffff, #f1f5f9);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  animation: bubbleIn 0.3s ease-out;
}

.message-wrapper.user .message-bubble {
  background: linear-gradient(145deg, #6366f1, #4f46e5);
  color: #fff;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3), 0 1px 3px rgba(79, 70, 229, 0.2);
}

.message-wrapper.assistant .message-bubble {
  border-bottom-left-radius: 6px;
}

.message-wrapper.user .message-bubble {
  border-bottom-right-radius: 6px;
}

.message-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06);
}

.message-wrapper.user .message-bubble:hover {
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4), 0 2px 4px rgba(79, 70, 229, 0.25);
}

@keyframes bubbleIn {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.bubble-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sender-name {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.7;
}

.message-time {
  font-size: 11px;
  opacity: 0.5;
}

.bubble-content {
  line-height: 1.65;
  white-space: pre-wrap;
}

/* Markdown 渲染样式 */
.markdown-body {
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
}

.message-wrapper.user .markdown-body {
  color: #fff;
}

.message-wrapper.user .markdown-body :deep(strong) {
  color: #c7d2fe;
}

.message-wrapper.user .markdown-body :deep(em) {
  color: #ddd6fe;
}

.message-wrapper.user .markdown-body :deep(code) {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.message-wrapper.user .markdown-body :deep(blockquote) {
  color: #e0e7ff;
  background: rgba(255, 255, 255, 0.08);
  border-color: #c7d2fe;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 8px 0 4px;
  font-weight: 600;
  color: #1e293b;
}

.markdown-body :deep(h1) { font-size: 17px; }
.markdown-body :deep(h2) { font-size: 15px; }
.markdown-body :deep(h3) { font-size: 14px; }

.markdown-body :deep(p) {
  margin: 3px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}

.markdown-body :deep(li) {
  margin: 2px 0;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
  font-family: monospace;
}

.markdown-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-body :deep(strong) {
  color: #4f46e5;
  font-weight: 600;
}

.markdown-body :deep(em) {
  color: #6366f1;
  font-style: italic;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #818cf8;
  padding: 8px 12px;
  margin: 8px 0;
  color: #64748b;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 10px 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 13px;
  margin: 8px 0;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(table th) {
  background: #f8fafc;
  font-weight: 600;
}

.bubble-trace {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0,0,0,0.08);
}

.trace-count {
  font-size: 11px;
  opacity: 0.6;
}

.bubble-resource-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
}

.resource-link-title {
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
}

.resource-link-desc {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}

.resource-link-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

/* 下一步建议 */
.bubble-next-actions {
  margin-top: 12px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
  border: 1px solid #bbf7d0;
  border-radius: 10px;
}

.next-actions-title {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
  margin-bottom: 8px;
}

.next-actions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.next-action-hint {
  font-size: 12px;
  color: #16a34a;
  padding: 3px 8px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: 10px;
}

.loading-more {
  text-align: center;
  padding: 10px;
  font-size: 13px;
  color: #94a3b8;
}

.loading-text {
  background: #f1f5f9;
  padding: 4px 12px;
  border-radius: 12px;
}

.input-area {
  padding: 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.input-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  justify-content: flex-end;
}

.typing-dots {
  color: #94a3b8;
  animation: pulse 1.5s infinite;
}

.demo-guide {
  max-width: 600px;
  margin: 20px auto 0;
  text-align: left;
  border: 1px dashed #c7d2fe;
  border-radius: 12px;
  overflow: hidden;
}

.demo-guide :deep(.el-collapse-item__header) {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  color: #4f46e5;
  background: #f5f3ff;
}

.demo-steps {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.demo-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;
  font-size: 13px;
}

.demo-step:hover {
  background: #f5f3ff;
}

.step-num {
  width: 24px;
  height: 24px;
  background: #4f46e5;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* 右侧面板 */
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.trace-timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.trace-step {
  display: flex;
  gap: 12px;
}

.step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}

.step-dot.done { background: #10b981; }
.step-dot.failed { background: #ef4444; }
.step-dot.started { background: #3b82f6; }

.step-content {
  display: flex;
  flex-direction: column;
}

.step-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.step-summary {
  font-size: 12px;
  color: #94a3b8;
}

.path-nodes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.path-node-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 10px;
}

.path-node-item.mastered { border-left: 3px solid #10b981; }
.path-node-item.in_progress { border-left: 3px solid #3b82f6; }
.path-node-item.needs_review { border-left: 3px solid #f59e0b; }

.node-reason {
  font-size: 12px;
  color: #94a3b8;
}

.action-cards {
  display: grid;
  gap: 10px;
}

.action-card-item {
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.action-card-item:hover {
  background: #fff;
  border-color: #818cf8;
  transform: translateX(4px);
}

.action-label {
  font-weight: 600;
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: #94a3b8;
}

.generated-resource-card {
  border: 1px solid #bfdbfe;
}

.generated-resource-list {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
}

.generated-resource-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f8fafc;
}

.resource-kind {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.resource-count {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
}

.open-resource-button {
  width: 100%;
}

.feedback-section {
  margin-top: 14px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.feedback-section ul {
  padding-left: 18px;
  margin: 0;
}

.feedback-section li {
  font-size: 13px;
  color: #64748b;
  margin: 6px 0;
}

/* 澄清选项 */
.clarification-area {
  padding: 16px 20px;
  background: #f0f9ff;
  border: 1px solid #93c5fd;
  border-radius: 12px;
  margin: 0 20px 16px;
}

.clarify-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e40af;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.clarify-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.clarify-option {
  padding: 12px 16px;
  background: #fff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clarify-option:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  transform: translateX(4px);
}

.clarify-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  display: block;
  margin-bottom: 4px;
}

.clarify-desc {
  font-size: 12px;
  color: #64748b;
}

/* 质量评分 */
.quality-card .score-row {
  margin-bottom: 12px;
}

.quality-card .score-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 6px;
  display: block;
}

/* 反思卡片 */
.reflection-card .reflection-text {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
  margin: 0 0 12px;
}

.reflection-card .refinement-action {
  text-align: center;
}

/* === 流式可视化 === */

/* 流式气泡 */
.streaming-bubble {
  border-left: 3px solid #3b82f6;
  background: #f8faff;
}

/* 节点进度条 */
.stream-progress {
  display: flex;
  gap: 4px;
  margin: 8px 0 12px;
  flex-wrap: wrap;
}

.stream-node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e2e8f0;
  transition: all 0.3s ease;
}

.stream-node-dot.running {
  background: #3b82f6;
  box-shadow: 0 0 6px #3b82f6;
  animation: pulse 0.8s infinite;
}

.stream-node-dot.done {
  background: #10b981;
}

.stream-node-dot.failed {
  background: #ef4444;
}

/* 实时评分区域 */
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  margin-left: auto;
  animation: pulse 1s infinite;
}

/* 打字机光标 */
.typewriter-cursor::after {
  content: '|';
  animation: blink 1s step-end infinite;
  color: #4f46e5;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* === 快速反馈标签 === */
.feedback-row {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.feedback-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.feedback-tag {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 10px;
  border-radius: 14px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid transparent;
  user-select: none;
}

.feedback-tag:hover {
  background: #e2e8f0;
  color: #334155;
}

.feedback-tag.active {
  background: #eef2ff;
  color: #4f46e5;
  border-color: #c7d2fe;
}

.feedback-tag.submitted {
  cursor: default;
  opacity: 0.6;
}

.tag-icon {
  font-size: 13px;
}

.tag-label {
  font-weight: 500;
}

.feedback-text-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
}

.feedback-text-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  background: #f8fafc;
}

.feedback-text-input:focus {
  border-color: #818cf8;
  background: #fff;
}

.feedback-done {
  margin-top: 6px;
  font-size: 11px;
  color: #94a3b8;
}

.feedback-adaptation {
  margin-top: 6px;
  padding: 7px 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.feedback-action-response {
  margin-top: 6px;
  padding: 8px 12px;
  border-radius: 8px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border: 1px solid #c7d2fe;
  color: #3730a3;
  font-size: 12px;
  line-height: 1.5;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.feedback-action-response .action-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.feedback-action-response .action-text {
  font-weight: 500;
}

.typing-dots::after {
  content: '';
  animation: dots 1.5s steps(3, end) infinite;
}

@keyframes dots {
  0% { content: ''; }
  33% { content: '.'; }
  66% { content: '..'; }
  100% { content: '...'; }
}
</style>
