import { useState } from 'react';
import { motion } from 'motion/react';
import { AnalysisResult } from '../types';
import { BookOpen, CheckCircle, XCircle, ShieldAlert } from 'lucide-react';

interface Props {
  result: AnalysisResult;
}

export default function TrainingView({ result }: Props) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [showResult, setShowResult] = useState(false);

  const { trainingQuestion, complianceRewrite } = result;

  const handleSelect = (id: string) => {
    if (showResult) return;
    setSelectedOption(id);
    setShowResult(true);
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
      
      <div className="mb-10 text-center md:text-left">
        <h2 className="text-3xl font-serif font-light text-brand-dark flex flex-wrap items-center gap-3 justify-center md:justify-start">
          <BookOpen className="text-gray-400" size={28} /> <span>反诈训练中心</span>
        </h2>
        <p className="text-gray-500 font-light mt-3">根据上传案例自动生成的情景式训练题与合规科普</p>
      </div>

      <div className="grid md:grid-cols-[1fr_350px] gap-8">
        
        {/* Main Quiz */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col shadow-sm">
          <div className="p-8 border-b border-gray-100 bg-brand-bg">
            <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] mb-4">
              情景测试题
            </div>
            <p className="text-xl text-brand-dark font-serif font-light leading-relaxed">
              {trainingQuestion.question}
            </p>
          </div>
          
          <div className="p-8 space-y-4 flex-1">
            {trainingQuestion.options.map((opt) => {
              const isSelected = selectedOption === opt.id;
              const isCorrect = opt.id === trainingQuestion.correctAnswerId;
              
              let btnClass = "border-gray-200 bg-white text-gray-700 hover:border-black";
              let icon = null;

              if (showResult) {
                if (isCorrect) {
                  btnClass = "border-brand-primary bg-brand-primary/5 text-brand-primary font-semibold";
                  icon = <CheckCircle size={20} className="text-brand-primary flex-shrink-0" />;
                } else if (isSelected) {
                  btnClass = "border-brand-red/20 bg-brand-red/5 text-brand-red";
                  icon = <XCircle size={20} className="text-brand-red flex-shrink-0" />;
                } else {
                  btnClass = "border-gray-100 bg-brand-bg text-gray-400 opacity-50";
                }
              }

              return (
                <button
                  key={opt.id}
                  onClick={() => handleSelect(opt.id)}
                  disabled={showResult}
                  className={`w-full text-left p-5 rounded-lg border-2 transition-all duration-200 flex items-start gap-4 ${btnClass}`}
                >
                  <span className="font-bold opacity-30 mt-0.5">{opt.id}.</span> 
                  <span className="flex-1 text-sm">{opt.text}</span>
                  {icon}
                </button>
              );
            })}
            
            {showResult && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }} 
                animate={{ opacity: 1, height: 'auto' }} 
                className="mt-8 pt-8 border-t border-gray-100"
              >
                <div className={`p-6 rounded-lg ${selectedOption === trainingQuestion.correctAnswerId ? 'bg-brand-bg border border-brand-primary/20' : 'bg-brand-red/5 border border-brand-red/20'}`}>
                  <h4 className="font-bold text-sm mb-3 text-black">
                    {selectedOption === trainingQuestion.correctAnswerId ? '✅ 回答正确' : '❌ 回答错误'}
                  </h4>
                  <p className="text-gray-700 text-sm leading-relaxed">
                    <span className="text-gray-400 font-bold uppercase tracking-widest text-[10px] block mb-1">解析</span>
                    {trainingQuestion.explanation}
                  </p>
                </div>
              </motion.div>
            )}
          </div>
          
          {showResult && (
             <div className="p-6 bg-brand-bg border-t border-gray-100 text-right">
               <button className="px-6 py-2 bg-gradient-to-r from-brand-primary to-brand-cyan shadow-sm shadow-brand-primary/20 hover:opacity-90 text-white rounded text-xs font-bold uppercase tracking-widest transition-opacity" onClick={() => {
                 setSelectedOption(null);
                 setShowResult(false);
               }}>再测一题</button>
             </div>
          )}
        </div>

        {/* Right Info */}
        <div className="space-y-6">
          <div className="bg-brand-bg rounded-lg border border-gray-200 p-8">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
              <ShieldAlert size={14} /> 核心科普改写
            </h3>
            <div className="space-y-6">
               <div>
                 <div className="text-[10px] text-gray-400 font-bold mb-2 uppercase tracking-widest">原始内容摘要</div>
                 <div className="text-sm text-gray-500 italic border-l-2 border-gray-300 pl-4 py-1">
                   “点击链接填写银行卡号和收到的验证码进行解封”
                 </div>
               </div>
               <div>
                 <div className="text-[10px] text-gray-400 font-bold mb-2 uppercase tracking-widest">合规安全版本</div>
                 <div className="text-sm text-brand-dark bg-white p-5 border border-gray-200 rounded-lg leading-relaxed shadow-sm">
                   {complianceRewrite}
                 </div>
               </div>
            </div>
          </div>
        </div>

      </div>
    </motion.div>
  );
}
