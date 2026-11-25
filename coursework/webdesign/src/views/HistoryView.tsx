import { motion } from 'motion/react';
import { mockHistory } from '../mockData';
import { ShieldAlert, Search } from 'lucide-react';

export default function HistoryView() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-end border-b border-gray-200 pb-4">
        <div>
          <h2 className="text-3xl font-serif font-light text-brand-dark tracking-tight">历史识别记录</h2>
          <p className="text-gray-500 font-light mt-2">查看过往风险诊断与分析报告</p>
        </div>
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search records..." 
            className="pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm text-brand-dark placeholder-gray-400 focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary w-64"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden flex-1 flex flex-col shadow-sm">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left text-sm text-gray-600">
             <thead className="bg-brand-bg text-[10px] font-bold uppercase tracking-widest text-gray-400 border-b border-gray-200">
               <tr>
                 <th className="px-8 py-5">检测时间</th>
                 <th className="px-8 py-5">输入类型</th>
                 <th className="px-8 py-5">风险等级</th>
                 <th className="px-8 py-5">疑似诈骗类型</th>
                 <th className="px-8 py-5">风险评分</th>
                 <th className="px-8 py-5 text-right">操作</th>
               </tr>
             </thead>
             <tbody className="divide-y divide-gray-100">
               {mockHistory.map((item) => (
                 <tr key={item.id} className="hover:bg-brand-bg transition-colors">
                   <td className="px-8 py-5 text-brand-dark whitespace-nowrap">{item.date}</td>
                   <td className="px-8 py-5">
                     <span className="bg-white text-gray-600 px-3 py-1 rounded text-[10px] font-bold border border-gray-200 uppercase tracking-widest shadow-sm">
                       {item.inputType}
                     </span>
                   </td>
                   <td className="px-8 py-5">
                     {item.riskLevel === 'high' && (
                       <span className="inline-flex items-center gap-1.5 text-brand-red text-xs font-bold bg-brand-red/5 px-2.5 py-1 rounded border border-brand-red/20">
                         <ShieldAlert size={14} /> 高风险
                       </span>
                     )}
                     {item.riskLevel === 'medium' && (
                       <span className="inline-flex items-center gap-1.5 text-brand-orange text-xs font-bold bg-brand-orange/5 px-2.5 py-1 rounded border border-brand-orange/20">
                         <ShieldAlert size={14} /> 中风险
                       </span>
                     )}
                     {item.riskLevel === 'low' && (
                       <span className="inline-flex items-center gap-1.5 text-brand-green text-xs font-bold bg-brand-green/5 px-2.5 py-1 rounded border border-brand-green/20">
                         <ShieldAlert size={14} /> 低风险
                       </span>
                     )}
                   </td>
                   <td className="px-8 py-5 text-gray-700">{item.fraudType}</td>
                   <td className="px-8 py-5 font-mono text-brand-dark font-medium">{item.riskScore}</td>
                   <td className="px-8 py-5 text-right">
                     <button className="text-brand-primary hover:text-brand-cyan text-xs font-bold uppercase tracking-widest transition-colors">查看报告</button>
                   </td>
                 </tr>
               ))}
             </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  );
}
