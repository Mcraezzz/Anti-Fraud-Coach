const API = "http://127.0.0.1:8000";
const answers = {};

const $ = (id) => document.getElementById(id);

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function uploadImage(path, file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API}${path}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function riskClass(level) {
  if (level === "高风险") return "high";
  if (level === "中风险") return "mid";
  return "low";
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return entities[char];
  });
}

function legacyHighlightSegments(text = "") {
  const segments = [];
  const pattern = /【风险:([^】]+)】/g;
  let cursor = 0;
  let match;
  while ((match = pattern.exec(text)) !== null) {
    if (cursor < match.index) {
      segments.push({ text: text.slice(cursor, match.index), risk: false, label: "", signal_id: "" });
    }
    segments.push({ text: match[1], risk: true, label: "风险信号", signal_id: "" });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), risk: false, label: "", signal_id: "" });
  }
  return segments.length ? segments : [{ text, risk: false, label: "", signal_id: "" }];
}

function renderHighlightedText(data) {
  const segments = Array.isArray(data.highlighted_segments) && data.highlighted_segments.length
    ? data.highlighted_segments
    : legacyHighlightSegments(data.highlighted_text || "");

  return segments
    .map((item) => {
      const text = escapeHtml(String(item.text || "").replace(/【风险:([^】]+)】/g, "$1"));
      if (!item.risk) return text;
      const label = item.label ? ` title="${escapeHtml(item.label)}"` : "";
      return `<mark class="risk-fragment"${label}><span class="risk-fragment-mark">!</span>${text}</mark>`;
    })
    .join("");
}

function renderAnalysis(data) {
  $("analysis").classList.remove("empty");
  $("analysis").innerHTML = `
    <div class="risk ${riskClass(data.risk_level)}">${data.risk_level}</div>
    <p class="muted">${data.scam_type} · 风险分 ${data.risk_score} · 可信度 ${data.confidence}%</p>
    <p>${data.summary}</p>
    <div class="highlight">${renderHighlightedText(data)}</div>
    <div class="chips">
      ${data.signal_summary.map((item) => `<span class="chip">${item.label} ${item.count}次</span>`).join("")}
    </div>
    ${
      data.model_insights?.length
        ? `<h3>模型辅助判断</h3>
          <div class="case-list">
            ${data.model_insights
              .map(
                (item) => `
                  <div class="model-card">
                    <strong>${item.model} · ${item.status}</strong>
                    <p>${item.label || ""}${item.score ? ` · ${item.score}` : ""}</p>
                    <small>${item.detail || ""}</small>
                  </div>
                `,
              )
              .join("")}
          </div>`
        : ""
    }
    ${data.enhanced_advice ? `<div class="advice-panel"><strong>Qwen 增强建议</strong><p>${data.enhanced_advice}</p></div>` : ""}
    ${data.signals
      .map(
        (item) => `
          <div class="signal">
            <strong>${item.label}：${item.keyword}</strong>
            <div class="muted">${item.explanation}</div>
          </div>
        `,
      )
      .join("")}
  `;
}

function renderOcr(data) {
  $("ocrResult").classList.remove("empty");
  $("ocrResult").innerHTML = `
    <h2>OCR 多模态处理</h2>
    <p class="muted">${data.engine} · 文本区域 ${data.regions.length} 个 · 还原消息 ${data.messages.length} 条 · 已自动脱敏</p>
    <div class="timeline">
      ${data.messages
        .map(
          (item) => `
            <div class="timeline-item ${item.speaker === "self" ? "self" : ""}">
              <strong>${item.timestamp || ""} ${item.speaker === "self" ? "我方" : item.speaker === "other" ? "对方" : "系统"}</strong>
              <p>${item.text}</p>
            </div>
          `,
        )
        .join("")}
    </div>
    <div class="highlight">${data.sanitized_text}</div>
  `;
}

function renderAnswer(data) {
  $("answer").classList.remove("empty");
  const version = data.knowledge_version?.active_version || "local";
  const cases = data.case_citations || [];
  $("answer").innerHTML = `
    <div class="rag-meta">
      <span>检索方式：${data.retrieval_method || "lexical"}</span>
      <span>知识库版本：${version}</span>
    </div>
    <p>${data.answer}</p>
    ${
      cases.length
        ? `<h3>相似案例</h3>
          <div class="case-list">
            ${cases
              .map(
                (item) => `
                  <div class="case-card">
                    <strong>${item.title}</strong>
                    <p>${item.scene}</p>
                    <div class="chips">${(item.risk_points || []).map((point) => `<span class="chip">${point}</span>`).join("")}</div>
                    <small>${item.handling || ""}</small>
                  </div>
                `
              )
              .join("")}
          </div>`
        : ""
    }
    <h3>知识来源</h3>
    <div class="chips">
      ${data.references
        .map((item) => `<span class="chip">${item.title} · ${item.source_type || "knowledge"} · ${item.score}</span>`)
        .join("")}
    </div>
  `;
}

async function loadQuestions() {
  const questions = await request("/api/training/questions");
  $("questions").innerHTML = questions
    .map(
      (q, index) => `
        <div class="question">
          <strong>${index + 1}. ${q.title}</strong>
          <div class="muted">${q.scene} · ${q.difficulty}</div>
          <p>${q.prompt}</p>
          <div class="options">
            ${q.options
              .map(
                (option) => `
                  <label class="option">
                    <input type="radio" name="${q.id}" value="${option.id}" />
                    ${option.id}. ${option.text}
                  </label>
                `,
              )
              .join("")}
          </div>
        </div>
      `,
    )
    .join("");

  document.querySelectorAll("input[type=radio]").forEach((input) => {
    input.addEventListener("change", (event) => {
      answers[event.target.name] = event.target.value;
    });
  });
}

function renderTrainingResult(data) {
  $("trainingResult").classList.remove("empty");
  $("trainingResult").innerHTML = `
    <div class="risk ${data.score >= 80 ? "low" : data.score >= 60 ? "mid" : "high"}">得分 ${data.score}</div>
    <p class="muted">答对 ${data.correct} / ${data.total}</p>
    <div class="chips">${data.weak_types.map((item) => `<span class="chip">${item}</span>`).join("") || '<span class="chip">无明显薄弱类型</span>'}</div>
  `;
}

async function loadReport() {
  const [dashboard, resources] = await Promise.all([request("/api/dashboard"), request("/api/resources")]);
  const sampleStats = dashboard.high_risk_sample_stats || {};
  const topErrors = dashboard.top_error_types || [];
  const advice = dashboard.education_advice || [];
  $("dashboard").innerHTML = `
    <h2>管理后台</h2>
    <div class="cards">
      <div class="card">平均分<strong>${dashboard.average_score}</strong></div>
      <div class="card">训练次数<strong>${dashboard.training_count}</strong></div>
      <div class="card">高风险案例<strong>${dashboard.high_risk_cases}</strong></div>
      <div class="card">完成率<strong>${dashboard.completion_rate || 0}%</strong></div>
    </div>
    <h3>易错类型排行</h3>
    <div class="case-list">
      ${topErrors
        .map(
          (item, index) => `
            <div class="case-card">
              <strong>${index + 1}. ${item.label} · 错误率 ${item.value}%</strong>
              <p>${item.common_mistake || ""}</p>
              <small>错题 ${item.wrong_count || 0} / 作答 ${item.attempt_count || 0} · ${item.action || ""}</small>
            </div>
          `,
        )
        .join("")}
    </div>
    <h3>高风险样本统计</h3>
    <div class="cards">
      <div class="card">今日新增<strong>${sampleStats.today_new || 0}</strong></div>
      <div class="card">待复核<strong>${sampleStats.pending_review || 0}</strong></div>
      <div class="card">已归档<strong>${sampleStats.verified || 0}</strong></div>
    </div>
    <div class="chips">${(sampleStats.by_type || []).map((item) => `<span class="chip">${item.label} ${item.count}条</span>`).join("")}</div>
    <h3>教育建议</h3>
    <div class="case-list">
      ${advice
        .map(
          (item) => `
            <div class="advice-panel">
              <strong>${item.title}</strong>
              <p>${item.reason}</p>
              <small>${(item.actions || []).join("；")}</small>
            </div>
          `,
        )
        .join("")}
    </div>
    <div class="chips">${Object.entries(dashboard.radar).map(([k, v]) => `<span class="chip">${k} ${v}</span>`).join("")}</div>
  `;
  $("resources").innerHTML = `
    <h2>本地模型资源</h2>
    ${resources.models
      .map((item) => `<div class="resource"><strong>${item.label}</strong><div class="muted">${item.exists ? `${item.size_gb}GB` : "缺失"} · ${item.path}</div></div>`)
      .join("")}
  `;
}

async function boot() {
  try {
    await request("/health");
    $("status").textContent = "后端已连接";
    $("status").className = "status ok";
    await Promise.all([loadQuestions(), loadReport()]);
  } catch (error) {
    $("status").textContent = "后端未连接";
    $("status").className = "status bad";
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab, .view").forEach((node) => node.classList.remove("active"));
    tab.classList.add("active");
    $(tab.dataset.tab).classList.add("active");
  });
});

$("sample").addEventListener("click", () => {
  $("content").value = "兼职群任务：先垫付 300 元完成刷单，返利 60 元。名额有限，马上加微信私聊，不要告诉老师。";
});

$("analyze").addEventListener("click", async () => {
  renderAnalysis(await request("/api/analyze", { method: "POST", body: JSON.stringify({ content: $("content").value, input_type: "text" }) }));
});

$("ocrAnalyze").addEventListener("click", async () => {
  const file = $("ocrFile").files[0];
  if (!file) {
    alert("请先选择聊天截图");
    return;
  }
  const data = await uploadImage("/api/ocr/chat", file);
  renderOcr(data);
  renderAnalysis(data.risk_analysis);
});

$("ask").addEventListener("click", async () => {
  renderAnswer(await request("/api/ask", { method: "POST", body: JSON.stringify({ question: $("question").value }) }));
});

$("submit").addEventListener("click", async () => {
  renderTrainingResult(await request("/api/training/submit", { method: "POST", body: JSON.stringify({ answers }) }));
});

boot();
