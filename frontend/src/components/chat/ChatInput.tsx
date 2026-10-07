import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Mic, MicOff } from 'lucide-react';
import { Button } from '../ui/button';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
}

// Extend the Window interface for SpeechRecognition browser API
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    SpeechRecognition: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    webkitSpeechRecognition: any;
  }
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, isLoading }) => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const interimRef = useRef('');

  // Detect browser support for SpeechRecognition
  useEffect(() => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    setVoiceSupported(!!SpeechRecognitionAPI);
  }, []);

  // Auto-resize textarea up to ~4 lines (~110px)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const nextHeight = Math.min(Math.max(textareaRef.current.scrollHeight, 44), 110);
      textareaRef.current.style.height = `${nextHeight}px`;
    }
  }, [input]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    interimRef.current = '';
    setIsListening(false);
  }, []);

  const startListening = useCallback(() => {
    setVoiceError(null);
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    try {
      const recognition = new SpeechRecognitionAPI();
      recognition.lang = 'en-US';
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognitionRef.current = recognition;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript) {
          setInput((prev) => {
            const base = prev.endsWith(' ') || prev === '' ? prev : prev + ' ';
            return (base + finalTranscript).trimStart();
          });
        }
        interimRef.current = interimTranscript;
      };

      recognition.onerror = (event: any) => {
        if (event.error === 'not-allowed') {
          setVoiceError('Microphone access denied. Please allow microphone permissions.');
        } else if (event.error !== 'aborted') {
          setVoiceError('Voice recognition error. Please try again.');
        }
        stopListening();
      };

      recognition.onend = () => {
        setIsListening(false);
        recognitionRef.current = null;
        interimRef.current = '';
      };

      recognition.start();
    } catch {
      setVoiceError('Could not initialize speech recognition.');
    }
  }, [stopListening]);

  const toggleVoice = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    if (isListening) stopListening();

    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-3 pt-2">
      {/* Voice error banner */}
      {voiceError && (
        <div className="mb-2 px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-xs text-rose-300 flex items-center justify-between gap-2">
          <span>{voiceError}</span>
          <button
            type="button"
            onClick={() => setVoiceError(null)}
            className="text-rose-400 hover:text-rose-200 text-xs font-bold shrink-0"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Composer container */}
      <form
        onSubmit={handleSubmit}
        className={`relative bg-slate-900 border rounded-xl transition-all duration-150 ${
          isListening
            ? 'border-rose-500/80 ring-1 ring-rose-500/30'
            : 'border-slate-800 focus-within:border-slate-700 focus-within:ring-1 focus-within:ring-slate-700'
        }`}
      >
        <div className="flex items-end gap-1.5 p-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? 'Listening... speak now' : 'Ask anything about SAP (S/4HANA, BRIM, MM, FI, ABAP)...'}
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent text-slate-100 placeholder-slate-500 text-xs sm:text-sm px-2 py-1.5 focus:outline-none resize-none leading-relaxed disabled:opacity-50"
            style={{ minHeight: '40px', maxHeight: '110px' }}
          />

          <div className="flex items-center gap-1 shrink-0 pb-0.5">
            {/* Listening indicator */}
            {isListening && (
              <span className="flex items-center gap-1 text-[11px] text-rose-400 font-medium px-2 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                Listening
              </span>
            )}

            {/* Mic button */}
            {voiceSupported && (
              <Button
                type="button"
                variant={isListening ? 'destructive' : 'ghost'}
                size="icon"
                onClick={toggleVoice}
                disabled={isLoading}
                title={isListening ? 'Stop recording' : 'Voice input'}
                aria-label={isListening ? 'Stop microphone' : 'Start microphone'}
                className="h-8 w-8 rounded-lg"
              >
                {isListening ? (
                  <MicOff className="w-3.5 h-3.5" />
                ) : (
                  <Mic className="w-3.5 h-3.5" />
                )}
              </Button>
            )}

            {/* Send button */}
            <Button
              type="submit"
              variant="sap"
              size="icon"
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
              className="h-8 w-8 rounded-lg shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </Button>
          </div>
        </div>
      </form>

      <div className="text-center mt-1.5">
        <span className="text-[10px] text-slate-500">
          SAP Knowledge Assistant &middot; Enterprise RAG &middot; Enter sends, Shift + Enter adds newline
        </span>
      </div>
    </div>
  );
};
