import React from 'react';
import { Layers, Shield } from 'lucide-react';

interface WelcomeScreenProps {
  onSelectPrompt?: (prompt: string) => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = () => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-2xl mx-auto w-full text-center">
      {/* Brand Icon & Heading */}
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-sap-700 via-sap-600 to-sap-400 flex items-center justify-center shadow-xl shadow-sap-600/20 border border-sap-400/30 mx-auto">
          <Layers className="w-8 h-8 text-white" />
        </div>
        <div className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full bg-emerald-500 text-[10px] font-bold text-slate-950 uppercase tracking-wider">
          Enterprise
        </div>
      </div>

      <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight mb-2">
        SAP Knowledge Assistant
      </h1>
      <p className="text-sm sm:text-base text-slate-400 max-w-lg mx-auto mb-6">
        Production-grade RAG specialized strictly for SAP ERP, S/4HANA, Fiori, ABAP, Basis, and functional modules.
      </p>

      {/* Domain Policy Badge */}
      <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-700/80 text-xs text-slate-300 mx-auto shadow-inner">
        <Shield className="w-3.5 h-3.5 text-sap-400" />
        <span>Strict SAP Domain Policy: Non-SAP questions are rejected automatically.</span>
      </div>
    </div>
  );
};
