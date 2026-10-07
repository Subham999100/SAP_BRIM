import React from 'react';
import { Database, Globe, AlertTriangle } from 'lucide-react';
import { Badge } from '../ui/badge';

interface SourceTypeBadgeProps {
  sourceType?: 'knowledge_base' | 'web' | 'refusal' | 'error';
}

export const SourceTypeBadge: React.FC<SourceTypeBadgeProps> = ({ sourceType }) => {
  if (!sourceType) return null;

  if (sourceType === 'knowledge_base') {
    return (
      <Badge variant="sap" className="gap-1 px-1.5 py-0.5 text-[10px]">
        <Database className="w-3 h-3 text-sap-400" />
        <span>SAP Knowledge Base</span>
      </Badge>
    );
  }

  if (sourceType === 'web') {
    return (
      <Badge variant="secondary" className="gap-1 px-1.5 py-0.5 text-[10px] text-cyan-300 border-cyan-800/40 bg-cyan-950/40">
        <Globe className="w-3 h-3 text-cyan-400" />
        <span>SAP Web Reference</span>
      </Badge>
    );
  }

  if (sourceType === 'refusal') {
    return (
      <Badge variant="destructive" className="gap-1 px-1.5 py-0.5 text-[10px]">
        <AlertTriangle className="w-3 h-3 text-rose-400" />
        <span>Scope Restriction</span>
      </Badge>
    );
  }

  return null;
};
