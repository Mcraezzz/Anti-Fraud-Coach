import { AnalysisResult } from './types';

export const mockResult: AnalysisResult = {
  id: 'REQ-20260615-001',
  date: '2026-06-15 14:30:00',
  inputType: 'text',
  originalText: '同学你好，我是淘宝客服。由于系统升级，你的账户涉嫌违规被冻结。请点击以下链接 t.cn/fake_url 填写银行卡号和收到的验证码进行解封，否则将影响个人征信。',
  riskLevel: 'high',
  riskScore: 89,
  fraudType: '冒充客服 / 钓鱼链接 / 诱导转账',
  riskFeatures: ['可疑链接', '要求转账', '验证码', '银行卡信息', '冒充客服', '紧急话术'],
  evidence: [
    {
      id: 'E1',
      title: '校园刷单返利与冒充客服诈骗规则',
      reason: '包含“系统升级”“银行卡号”“验证码”等关键词',
      scores: {
        bm25: 0.82,
        dense: 0.76,
        url: 0.00,
        keyword: 0.90
      },
      fusionScore: 0.81,
      rerankScore: 0.88,
      content: '冒充淘宝、京东等平台客服，以系统升级、账户冻结、购买会员等为由，诱导用户点击钓鱼链接，填写银行账户密码及验证码，从而盗刷资金。'
    },
    {
      id: 'E2',
      title: '短链接黑名单库匹配',
      reason: '匹配到高危短网址域名模式 t.cn/*',
      scores: {
        bm25: 0.00,
        dense: 0.45,
        url: 0.95,
        keyword: 0.60
      },
      fusionScore: 0.75,
      rerankScore: 0.85,
      content: '诈骗分子常利用 t.cn, bit.ly 等短链接服务隐藏真实的钓鱼网址，伪装成官方页面进行诈骗。'
    }
  ],
  suggestions: {
    immediate: [
      '绝对不要点击短信中的任何陌生链接',
      '绝对不要输入验证码或银行卡信息',
      '不要进行任何转账操作',
      '保存当前聊天记录和截图作为证据'
    ],
    verify: [
      '通过淘宝 App 内的官方客服联系核实',
      '不相信对方提供的任何电话号码或链接'
    ],
    followUp: [
      '如已点击链接或填写信息，请立即联系银行冻结卡片',
      '向学校辅导员或保卫处反馈情况',
      '下载安装国家反诈中心 App'
    ]
  },
  complianceRewrite: '请勿点击短信或聊天记录中的陌生链接，不要向任何人提供银行卡号、密码或验证码。真正的平台客服不会以“系统升级”为由要求您提供短信验证码。如需核实账号状态，请直接登录官方 App 查看。',
  trainingQuestion: {
    question: '如果陌生短信自称是“淘宝客服”，要求你点击链接填写银行卡号和收到的验证码以解冻账户，你应该怎么做？',
    options: [
      { id: 'A', text: '按照要求填写，尽快解冻账户以免影响购物' },
      { id: 'B', text: '加对方微信问清楚到底是怎么回事' },
      { id: 'C', text: '拒绝点击链接并提供信息，直接登录淘宝 App 官方客服核实' },
      { id: 'D', text: '把收到的验证码发给对方帮忙处理' }
    ],
    correctAnswerId: 'C',
    explanation: '银行卡号、验证码和陌生链接同时出现时，通常属于高风险诈骗信号。官方客服绝对不会要求用户提供短信验证码。'
  },
  rawJson: ''
};

mockResult.rawJson = JSON.stringify(mockResult, null, 2);

export const mockHistory: AnalysisResult[] = [
  mockResult,
  {
    ...mockResult,
    id: 'REQ-20260614-002',
    date: '2026-06-14 09:12:00',
    inputType: 'url',
    originalText: 'http://taobao-security-update.com/login',
    riskLevel: 'medium',
    riskScore: 67,
    fraudType: '可疑钓鱼链接',
    riskFeatures: ['仿冒域名', '要求登录'],
  }
];
