// Local keyword screening only: no model, reputation lookup or probability score.
const rules = [
  { label: '先付费或返利', tone: 'red', words: ['垫付', '保证金', '押金', '返现', '刷单', 'training fee', 'deposit'] },
  { label: '敏感信息', tone: 'red', words: ['验证码', '银行卡', '密码', '身份证', 'password', 'verification code'] },
  { label: '紧迫或保密话术', tone: 'amber', words: ['名额有限', '立即', '马上', '不要告诉', '保密', 'urgent', 'immediately'] },
  { label: '外部操作', tone: 'amber', words: ['屏幕共享', '下载', '私下交易', '脱离平台', 'screen sharing', 'download'] }
]

function analyzeText(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  if (!text || text.length > 800) throw new Error('请输入 1–800 字的内容')
  const lower = text.toLowerCase()
  const signals = rules.map(rule => ({
    label: rule.label,
    tone: rule.tone,
    matches: rule.words.filter(word => lower.includes(word))
  })).filter(signal => signal.matches.length)
  return {
    signals,
    count: signals.length,
    summary: signals.length ? '发现待核实词语' : '未命中当前规则',
    // Only matched keywords are passed to results; never the submitted text.
    evidence: signals.map(signal => signal.matches.join('、')).join('；'),
    explanation: '仅按本地关键词匹配，无法理解否定、引用或上下文，可能误报或漏报；未命中不代表安全。链接不会被访问，也未核验网站信誉。'
  }
}

module.exports = { analyzeText }
