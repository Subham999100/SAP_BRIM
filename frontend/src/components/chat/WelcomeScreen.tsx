import React from 'react';
import { Layers, Shield, Sparkles, BookOpen, Cpu, Terminal } from 'lucide-react';
import { Badge } from '../ui/badge';

interface WelcomeScreenProps {
  onSelectPrompt?: (prompt: string) => void;
}

const SAMPLE_PROMPTS = [
  {
    title: 'BRIM Subscription Billing',
    prompt: 'Explain SAP BRIM subscription order management and how billing documents are generated.',
    icon: Layers,
  },
  {
    title: 'MM-FI Integration',
    prompt: 'How does account determination work in SAP MM-FI integration during goods receipt and invoice verification?',
    icon: BookOpen,
  },
  {
    title: 'S/4HANA Migration',
    prompt: 'What are the architectural differences between traditional ECC 6.0 and SAP S/4HANA Universal Journal (ACDOCA)?',
    icon: Cpu,
  },
  {
    title: 'ABAP Core Data Services',
    prompt: 'Provide best practices for creating ABAP Core Data Services (CDS) views with associations and annotations in S/4HANA.',
    icon: Terminal,
  },
];

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onSelectPrompt }) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-3xl mx-auto w-full text-center">
      {/* Brand Icon & Heading */}
      <div className="mb-4">
        <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-700/80 flex items-center justify-center mx-auto text-sap-400">
          <Layers className="w-6 h-6" />
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <h1 className="text-xl sm:text-2xl font-semibold text-slate-100 tracking-tight">
          SAP Knowledge Assistant
        </h1>
        <Badge variant="sap">Enterprise</Badge>
      </div>

      <p className="text-xs sm:text-sm text-slate-400 max-w-lg mx-auto mb-6">
        Specialized RAG intelligence grounded in official SAP documentation, S/4HANA, Fiori, BRIM, ABAP, and ERP modules.
      </p>

      {/* Domain Policy Notice */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 max-w-md mx-auto mb-8">
        <Shield className="w-3.5 h-3.5 text-sap-400 shrink-0" />
        <span>Grounded in enterprise docs. Non-SAP queries are rejected automatically.</span>
      </div>

      {/* Suggested prompts */}
      {onSelectPrompt && (
        <div className="w-full max-w-2xl text-left">
          <div className="flex items-center gap-1.5 mb-2.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            <Sparkles className="w-3 h-3 text-sap-400" />
            <span>Suggested Inquiries</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SAMPLE_PROMPTS.map((sample, idx) => {
              const Icon = sample.icon;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSelectPrompt(sample.prompt)}
                  className="flex flex-col text-left p-3 rounded-lg bg-slate-900/50 hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700 transition group cursor-pointer"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-3.5 h-3.5 text-sap-400 group-hover:text-sap-300 shrink-0" />
                    <span className="text-xs font-medium text-slate-200 group-hover:text-white">
                      {sample.title}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                    {sample.prompt}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
