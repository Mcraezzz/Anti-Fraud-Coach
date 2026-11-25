/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { 
  ShieldAlert, 
  Home, 
  ScanSearch, 
  Network, 
  GraduationCap, 
  History, 
  FileJson,
  Menu,
  X
} from 'lucide-react';
import HomeView from './views/HomeView';
import RecognitionView from './views/RecognitionView';
import EvidenceView from './views/EvidenceView';
import TrainingView from './views/TrainingView';
import HistoryView from './views/HistoryView';
import DebugView from './views/DebugView';
import { mockResult } from './mockData';

export type TabType = 'home' | 'recognition' | 'evidence' | 'training' | 'history' | 'debug';

export default function App() {
  const [activeTab, setActiveTab] = useState<TabType>('home');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // We share the mock result across views to simulate a connected system
  const currentResult = mockResult;

  const tabs = [
    { id: 'home', label: '首页概览', icon: Home },
    { id: 'recognition', label: '媒体内容识别', icon: ScanSearch },
    { id: 'evidence', label: '证据链分析', icon: Network },
    { id: 'training', label: '反诈训练中心', icon: GraduationCap },
    { id: 'history', label: '历史记录', icon: History },
    { id: 'debug', label: 'JSON / Debug', icon: FileJson },
  ] as const;

  const renderContent = () => {
    switch (activeTab) {
      case 'home': return <HomeView onNavigate={setActiveTab} />;
      case 'recognition': return <RecognitionView result={currentResult} />;
      case 'evidence': return <EvidenceView result={currentResult} />;
      case 'training': return <TrainingView result={currentResult} />;
      case 'history': return <HistoryView />;
      case 'debug': return <DebugView result={currentResult} />;
      default: return <HomeView onNavigate={setActiveTab} />;
    }
  };

  return (
    <div className="min-h-screen bg-brand-bg text-brand-dark flex overflow-hidden">
      
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-gray-900/50 z-40 md:hidden" 
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 bg-brand-bg border-r border-gray-200 transform transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-3 p-8 border-b border-gray-200">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-brand-primary to-brand-cyan flex items-center justify-center text-white">
            <ShieldAlert size={16} />
          </div>
          <div>
            <h1 className="font-serif font-light text-xl text-brand-dark leading-tight tracking-tight">Anti-Fraud Coach</h1>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.2em] mt-1">识别与训练系统</p>
          </div>
        </div>

        <nav className="p-6 space-y-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setSidebarOpen(false);
              }}
              className={`w-full flex items-center gap-4 px-4 py-3 rounded text-sm transition-all duration-200 ${
                activeTab === tab.id 
                  ? 'bg-white border border-gray-200 text-brand-primary shadow-sm font-semibold' 
                  : 'text-gray-500 hover:text-brand-dark hover:bg-gray-100/50'
              }`}
            >
              <tab.icon size={18} className={activeTab === tab.id ? 'text-brand-primary' : 'text-gray-400'} />
              {tab.label}
            </button>
          ))}
        </nav>
        
        <div className="absolute bottom-0 left-0 right-0 p-8 border-t border-gray-200 bg-brand-bg">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-green" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400">AI 模型在线</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden flex items-center justify-between p-4 border-b border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-gradient-to-br from-brand-primary to-brand-cyan flex items-center justify-center text-white">
              <ShieldAlert size={12} />
            </div>
            <span className="font-serif text-lg text-brand-dark tracking-tight">Anti-Fraud Coach</span>
          </div>
          <button onClick={() => setSidebarOpen(true)} className="p-2 text-gray-500 hover:text-brand-dark">
            <Menu size={20} />
          </button>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-12 bg-white">
          <div className="max-w-6xl mx-auto h-full">
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  );
}

