import { motion } from 'motion/react';
import { AnalysisResult } from '../types';
import { Copy, Download, Code } from 'lucide-react';

interface Props {
  result: AnalysisResult;
}

export default function DebugView({ result }: Props) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-end border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-3xl font-serif font-light text-brand-dark tracking-tight flex items-center gap-3">
            <Code className="text-gray-400" size={28} /> 原始 JSON
          </h2>
          <p className="text-gray-500 font-light mt-2">查看系统最终输出的结构化字段，可用于后续实验评估与接口对接</p>
        </div>
        <div className="flex gap-4">
          <button className="px-5 py-2.5 bg-brand-bg border border-gray-200 hover:bg-gray-100 text-brand-dark text-xs font-bold tracking-widest uppercase rounded flex items-center gap-2 transition-colors">
            <Copy size={16} /> 复制
          </button>
          <button className="px-5 py-2.5 bg-gradient-to-r from-brand-primary to-brand-cyan shadow-sm shadow-brand-primary/20 hover:opacity-90 text-white text-xs font-bold tracking-widest uppercase rounded flex items-center gap-2 transition-opacity">
            <Download size={16} /> 下载报告
          </button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_300px] gap-8 flex-1 min-h-0">
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col shadow-sm">
          <div className="bg-brand-bg px-6 py-3 text-[10px] font-bold uppercase tracking-widest text-gray-500 border-b border-gray-200 flex justify-between items-center">
            <span>response.json</span>
            <span>UTF-8</span>
          </div>
          <div className="p-6 overflow-auto flex-1 text-sm font-mono text-gray-700 leading-relaxed bg-brand-bg">
            <pre className="whitespace-pre-wrap">{result.rawJson}</pre>
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-8 overflow-y-auto shadow-sm">
          <h3 className="font-bold text-[10px] uppercase tracking-[0.2em] text-gray-400 mb-6 border-b border-gray-100 pb-3">输出字段说明</h3>
          <div className="space-y-5 text-sm">
            {[
              { field: 'riskLevel', desc: '综合判定的风险等级 (low/medium/high)' },
              { field: 'riskScore', desc: '大模型与检索融合综合得分 (0-100)' },
              { field: 'fraudType', desc: '归类的具体网络诈骗类型' },
              { field: 'riskFeatures', desc: '独立抽取到的关键风险信号数组' },
              { field: 'evidence', desc: '从知识库检索到的 Top K 证据及多路分数' },
              { field: 'suggestions', desc: '多层级的立刻处置与后续核实建议' },
              { field: 'complianceRewrite', desc: '剥离风险后的安全文本' },
              { field: 'trainingQuestion', desc: '基于当前场景生成的测试题' },
            ].map((f, i) => (
              <div key={i}>
                <div className="font-mono text-brand-primary font-semibold text-xs mb-1.5">{f.field}</div>
                <div className="text-gray-500 text-xs leading-relaxed">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
