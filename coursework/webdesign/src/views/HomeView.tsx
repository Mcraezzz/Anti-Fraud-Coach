import { motion } from 'motion/react';
import { ArrowRight, ShieldCheck, Database, Zap, BookOpen } from 'lucide-react';

interface Props {
  onNavigate: (tab: any) => void;
}

export default function HomeView({ onNavigate }: Props) {
  const features = [
    {
      title: '多类型输入识别',
      desc: '支持短信、聊天文本、邮件、社交媒体内容、URL 与截图上传',
      icon: Database,
    },
    {
      title: '风险特征感知',
      desc: '自动识别链接、转账、验证码、冒充身份、紧急话术等风险信号',
      icon: Zap,
    },
    {
      title: '混合 RAG 检索',
      desc: '融合 BM25、BGE-M3、FAISS、URL 精确匹配和风险关键词匹配',
      icon: ShieldCheck,
    },
    {
      title: '反诈训练生成',
      desc: '输出风险解释、反诈建议、合规改写和情境式训练题',
      icon: BookOpen,
    }
  ];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-16"
    >
      <div className="flex flex-col md:flex-row gap-12 items-center justify-between p-12 bg-brand-bg border border-gray-200 rounded-lg relative overflow-hidden">
        <div className="max-w-2xl z-10">
          <h1 className="text-4xl md:text-5xl font-serif font-light text-brand-dark mb-6 tracking-tight leading-tight">
            大学生 <span className="font-semibold text-transparent bg-clip-text bg-gradient-to-r from-brand-primary to-brand-cyan">AI 反诈媒体</span><br />
            内容识别与训练平台
          </h1>
          <p className="text-gray-500 font-light leading-relaxed text-lg mb-10 max-w-xl">
            支持短信、聊天截图、邮件、社交媒体文本与 URL 描述输入，结合风险特征抽取、混合检索、证据融合与大模型推理，生成可解释的反诈分析报告。
          </p>
          <div className="flex flex-wrap gap-4">
            <button 
              onClick={() => onNavigate('recognition')}
              className="px-8 py-4 bg-gradient-to-r from-brand-primary to-brand-cyan text-white text-xs font-bold rounded uppercase tracking-[0.2em] flex items-center gap-3 hover:opacity-90 transition-opacity shadow-lg shadow-brand-primary/20"
            >
              开始媒体内容识别 <ArrowRight size={16} />
            </button>
          </div>
        </div>
        
        <div className="hidden md:flex flex-1 justify-center z-10">
          <div className="relative w-72 h-72 rounded-full border border-gray-200 bg-white flex items-center justify-center shadow-sm">
             <div className="absolute inset-2 rounded-full border border-gray-100" />
             <div className="absolute inset-8 rounded-full border border-gray-50" />
             <ShieldCheck size={48} className="text-brand-primary" />
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
        {features.map((feature, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="p-8 rounded-lg bg-white border border-gray-200 hover:shadow-sm transition-all"
          >
            <div className="w-12 h-12 bg-white border border-brand-primary/10 shadow-sm rounded-lg flex items-center justify-center text-brand-cyan mb-6">
              <feature.icon size={20} />
            </div>
            <h3 className="font-semibold text-brand-dark mb-3">{feature.title}</h3>
            <p className="text-gray-500 text-sm leading-relaxed font-light">{feature.desc}</p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8 border-t border-gray-100">
        {[
          { label: '已支持输入类型', value: '5+' },
          { label: '风险信号类别', value: '8+' },
          { label: '检索证据来源', value: '多源知识库' },
          { label: '输出支持', value: 'JSON 结构化' },
        ].map((stat, i) => (
          <div key={i} className="p-6 text-center rounded-lg bg-brand-bg border border-gray-200">
            <div className="text-3xl font-light text-brand-dark mb-3">{stat.value}</div>
            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-[0.2em]">{stat.label}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
