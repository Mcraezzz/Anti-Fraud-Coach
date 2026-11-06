import { motion } from 'motion/react';
import { AnalysisResult, Evidence } from '../types';
import { Database, Network, Server, ArrowDown } from 'lucide-react';

interface Props {
  result: AnalysisResult;
}

export default function EvidenceView({ result }: Props) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      
      <div className="mb-10 text-center md:text-left">
        <h2 className="text-3xl font-serif font-light text-brand-dark tracking-tight">RAG 证据链与检索来源</h2>
        <p className="text-gray-500 font-light mt-2">混合检索与特征分数融合过程可视化</p>
      </div>

      <div className="grid lg:grid-cols-[250px_1fr] gap-8">
        
        {/* Left Flowchart */}
        <div className="bg-brand-bg rounded-lg border border-gray-200 p-8 flex flex-col items-center justify-between min-h-[500px]">
          <FlowStep title="用户输入" icon={Database} active />
          <FlowArrow />
          <FlowStep title="风险特征抽取" icon={Server} active />
          <FlowArrow />
          <FlowStep title="混合检索证据" icon={Network} active highlight />
          <FlowArrow />
          <FlowStep title="证据融合评分" icon={Network} active />
          <FlowArrow />
          <FlowStep title="BGE Reranker" icon={Database} active />
          <FlowArrow />
          <FlowStep title="Qwen 风险推理" icon={Server} active />
        </div>

        {/* Right Evidences */}
        <div className="space-y-6">
          <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">检索证据详情 (Top K)</h3>
          
          {result.evidence.map((ev, i) => (
            <EvidenceCard key={ev.id} evidence={ev} index={i} />
          ))}
          
        </div>
      </div>
    </motion.div>
  );
}

function FlowStep({ title, icon: Icon, active, highlight }: any) {
  return (
    <div className={`w-full p-4 rounded-lg border text-sm font-semibold text-center transition-all ${highlight ? 'bg-white border-brand-cyan text-brand-primary shadow-sm' : active ? 'bg-white border-gray-200 text-gray-700' : 'bg-transparent border-gray-200 text-gray-400 opacity-50'} flex items-center justify-center gap-3`}>
      <Icon size={18} />
      {title}
    </div>
  )
}

function FlowArrow() {
  return <ArrowDown size={16} className="text-gray-300 my-2" />
}

function EvidenceCard({ evidence, index }: { evidence: Evidence, index: number }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
      <div className="p-6 border-b border-gray-100 bg-brand-bg flex flex-col sm:flex-row sm:justify-between items-start gap-4">
        <div>
          <h4 className="font-semibold text-brand-dark flex items-center gap-3">
            <span className="text-[10px] py-1 px-2.5 bg-gradient-to-r from-brand-primary to-brand-cyan text-white rounded uppercase tracking-widest font-bold">证据 {index + 1}</span>
            {evidence.title}
          </h4>
          <p className="text-sm text-gray-500 mt-2 font-light">匹配原因：{evidence.reason}</p>
        </div>
        <div className="sm:text-right flex flex-col sm:justify-end">
          <div className="text-[10px] text-gray-400 mb-1 uppercase tracking-widest font-bold">Rerank 得分</div>
          <div className="text-2xl font-light text-brand-primary">{evidence.rerankScore.toFixed(2)}</div>
        </div>
      </div>
      
      <div className="p-6 grid md:grid-cols-2 gap-8">
        <div>
           <div className="text-[10px] font-bold text-gray-400 mb-4 uppercase tracking-widest">多路检索分数</div>
           <div className="space-y-3">
              <ScoreBar label="BM25" score={evidence.scores.bm25} />
              <ScoreBar label="Dense (BGE-M3)" score={evidence.scores.dense} />
              <ScoreBar label="URL Match" score={evidence.scores.url} />
              <ScoreBar label="Risk Keyword" score={evidence.scores.keyword} />
           </div>
        </div>
        <div>
          <div className="text-[10px] font-bold text-gray-400 mb-3 uppercase tracking-widest">匹配内容</div>
          <p className="text-sm text-gray-700 leading-relaxed bg-brand-bg p-4 rounded-lg border border-gray-100">
            {evidence.content}
          </p>
        </div>
      </div>
      <div className="px-6 py-3 bg-brand-bg border-t border-gray-100 flex justify-between items-center text-[11px] text-gray-500 uppercase tracking-wider font-semibold">
        <span>初始融合得分: {evidence.fusionScore.toFixed(2)}</span>
      </div>
    </div>
  )
}

function ScoreBar({ label, score }: { label: string, score: number }) {
  return (
    <div className="flex items-center gap-4">
      <div className="w-24 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{label}</div>
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-brand-primary to-brand-cyan rounded-full"
          style={{ width: `${score * 100}%` }}
        />
      </div>
      <div className="w-8 text-[11px] text-right font-semibold text-gray-900">{score.toFixed(2)}</div>
    </div>
  )
}
