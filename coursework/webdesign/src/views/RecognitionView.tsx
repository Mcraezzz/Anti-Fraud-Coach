import { useState } from 'react';
import { motion } from 'motion/react';
import { AnalysisResult } from '../types';
import { ShieldAlert, AlertTriangle, CheckCircle, UploadCloud, Info } from 'lucide-react';

interface Props {
  result: AnalysisResult;
}

export default function RecognitionView({ result }: Props) {
  const [inputText, setInputText] = useState(result.originalText);
  const [activeTab, setActiveTab] = useState('text');
  
  const tabs = [
    { id: 'text', label: '文本' },
    { id: 'image', label: '聊天截图' },
    { id: 'sms', label: '短信' },
    { id: 'email', label: '邮件' },
    { id: 'url', label: 'URL / 社交媒体' },
  ];

  return (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} 
      className="h-full flex flex-col gap-6"
    >
      <div className="flex justify-between items-end border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-3xl font-serif font-light text-brand-dark tracking-tight">待识别媒体内容</h2>
          <p className="text-gray-500 font-light mt-2">上传或输入可疑内容进行风险诊断</p>
        </div>
        <button className="px-6 py-2.5 bg-gradient-to-r from-brand-primary to-brand-cyan text-white text-xs font-semibold rounded uppercase tracking-widest hover:opacity-90 transition-opacity shadow-md shadow-brand-primary/20">
          分析风险
        </button>
      </div>

      <div className="grid lg:grid-cols-2 gap-8 flex-1 min-h-0">
        
        {/* Left Panel: Input */}
        <div className="flex flex-col gap-4 bg-brand-bg rounded-lg border border-gray-200 p-6">
          <div className="flex gap-2 border-b border-gray-200 pb-3 overflow-x-auto">
            {tabs.map(t => (
              <button 
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`px-4 py-2 text-xs font-semibold rounded uppercase tracking-wider whitespace-nowrap transition-colors ${
                  activeTab === t.id ? 'bg-white border border-gray-200 text-brand-primary shadow-sm' : 'text-gray-400 hover:text-brand-dark hover:bg-white'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {activeTab === 'image' ? (
            <div className="flex-1 border-2 border-dashed border-gray-300 bg-white rounded-lg flex flex-col items-center justify-center text-center p-8 hover:bg-gray-50 transition-colors cursor-pointer">
              <UploadCloud size={48} className="text-gray-300 mb-4" />
              <p className="text-gray-700 font-medium text-sm">点击或拖拽上传截图</p>
              <p className="text-gray-400 text-xs mt-1">支持聊天截图、短信截图、邮件截图、网页截图</p>
            </div>
          ) : (
            <textarea 
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              className="flex-1 bg-white border border-gray-200 rounded-lg p-6 text-gray-700 focus:outline-none focus:ring-1 focus:ring-black focus:border-black resize-none text-sm leading-relaxed"
              placeholder="请粘贴可疑短信、聊天记录、邮件内容、社交媒体文案或 URL 描述，例如：“客服要求我点击链接填写银行卡号并输入验证码……”"
            />
          )}

          {activeTab === 'image' && (
            <div className="text-xs text-gray-500 flex justify-end">
              <button className="hover:text-brand-dark underline">可手动修正 OCR 识别文本</button>
            </div>
          )}
        </div>

        {/* Right Panel: Results */}
        <div className="flex flex-col gap-6 bg-white border border-gray-200 rounded-lg p-8 overflow-y-auto shadow-sm">
          
          {/* Risk Card */}
          <div className="p-6 rounded-lg border border-brand-red/20 bg-brand-red/5 flex flex-col gap-4">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2 text-brand-red font-bold text-lg">
                <ShieldAlert size={20} />
                高风险
              </div>
              <div className="bg-white text-brand-red px-3 py-1 rounded border border-brand-red/20 text-xs font-mono flex items-center gap-2 shadow-sm">
                风险评分: <span className="font-bold text-base">{result.riskScore}</span> / 100
              </div>
            </div>
            <div>
              <p className="text-gray-700 text-sm"><span className="text-gray-500 mr-2">疑似诈骗类型:</span>{result.fraudType}</p>
            </div>
            <div className="bg-brand-red/10 text-brand-red px-4 py-3 rounded text-sm font-medium flex items-center gap-2">
               <AlertTriangle size={16} />
               存在明显诈骗特征，建议立即停止操作
            </div>
          </div>

          {/* Features */}
          <div>
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">识别到的风险特征</h3>
            <div className="flex flex-wrap gap-2">
              {result.riskFeatures.map((tag, i) => {
                let colorClass = "bg-brand-bg text-gray-600 border-gray-200";
                if (tag.includes('转账') || tag.includes('银行卡')) colorClass = "bg-brand-red/10 text-brand-red border-brand-red/20";
                if (tag.includes('链接')) colorClass = "bg-brand-blue/10 text-brand-blue border-brand-blue/20";
                if (tag.includes('冒充')) colorClass = "bg-purple-50 text-purple-600 border-purple-200";
                if (tag.includes('验证码')) colorClass = "bg-brand-orange/10 text-brand-orange border-brand-orange/20";

                return (
                  <span key={i} className={`px-3 py-1.5 text-xs font-semibold rounded border ${colorClass}`}>
                    [{tag}]
                  </span>
                )
              })}
            </div>
            <p className="text-xs text-gray-500 mt-4 flex items-start gap-2 bg-brand-bg p-4 rounded-lg border border-gray-200 leading-relaxed">
              <Info size={14} className="flex-shrink-0 mt-0.5" />
              “验证码”通常与账号接管、支付验证或身份验证风险相关，任何要求你提供验证码的陌生人都存在较高诈骗风险。
            </p>
          </div>

          {/* Suggestions */}
          <div>
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-5 mt-6 border-b border-gray-100 pb-2">反诈处置建议</h3>
            <div className="space-y-6">
              <div>
                <h4 className="text-xs font-bold text-brand-red mb-3 flex items-center gap-2"><AlertTriangle size={14} /> 立即操作</h4>
                <ul className="text-sm space-y-2.5">
                  {result.suggestions.immediate.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 text-gray-700">
                      <span className="text-brand-red mt-0.5">•</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
              
              <div>
                <h4 className="text-xs font-bold text-brand-orange mb-3 flex items-center gap-2"><ShieldAlert size={14} /> 核实方式</h4>
                <ul className="text-sm space-y-2.5">
                  {result.suggestions.verify.map((s, i) => (
                    <li key={i} className="flex items-start gap-3 text-gray-700">
                      <span className="text-brand-orange mt-0.5">•</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </motion.div>
  );
}
