'use client';

import React, { useState, useEffect } from 'react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';

interface VoiceCommandBarProps {
  onStageAction: (action: any) => void;
  onRefreshData: () => void;
}

export function VoiceCommandBar({ onStageAction, onRefreshData }: VoiceCommandBarProps) {
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentReply, setAgentReply] = useState<string | null>(null);

  const handleCommandSubmit = async (commandText: string) => {
    if (!commandText.trim()) return;
    setIsProcessing(true);
    setAgentReply(null);

    try {
      const res = await fetch('/api/py/voice/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: commandText.trim() }),
      });

      const data = await res.json();
      if (data.type === 'stage_action') {
        onStageAction(data.staged_action);
      } else if (data.reply) {
        setAgentReply(data.reply);
        if (data.needs_refresh) {
          onRefreshData();
        }
      }
    } catch (err) {
      console.error('Error executing voice command:', err);
      setAgentReply('Error de comunicación con el asistente de voz.');
    } finally {
      setIsProcessing(false);
      setInputText('');
    }
  };

  const { isListening, transcript, isSupported, startListening, stopListening } =
    useVoiceRecognition({
      lang: 'es-CO',
      onResult: (text, isFinal) => {
        setInputText(text);
        if (isFinal) {
          handleCommandSubmit(text);
        }
      },
    });

  return (
    <div className="voice-bar-container">
      {agentReply && (
        <div className="alert alert-info alert-dismissible fade show shadow-sm rounded-4 mb-2 py-2 px-3 small border-0 d-flex align-items-center justify-content-between" role="alert">
          <div className="d-flex align-items-center gap-2">
            <i className="bi bi-robot text-primary fs-5"></i>
            <span>{agentReply}</span>
          </div>
          <button
            type="button"
            className="btn-close p-2"
            onClick={() => setAgentReply(null)}
            aria-label="Close"
          ></button>
        </div>
      )}

      <div className="card shadow-lg border-0 rounded-pill p-2 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleCommandSubmit(inputText);
          }}
          className="d-flex align-items-center gap-2"
        >
          {/* Mic Button */}
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            className={`btn voice-pulse-btn ${isListening ? 'listening btn-danger' : 'btn-primary'} text-white border-0`}
            title={isListening ? 'Detener escucha' : 'Activar micrófono por voz (es-CO)'}
            disabled={!isSupported && false}
          >
            <i className={`bi ${isListening ? 'bi-mic-fill' : 'bi-mic'}`}></i>
          </button>

          {/* Transcript / Input */}
          <div className="flex-grow-1 px-2">
            <input
              type="text"
              className="form-control border-0 shadow-none bg-transparent"
              placeholder={
                isListening
                  ? 'Escuchando en español (Colombia)...'
                  : 'Prueba: "Marcar pagado Energía 20" o "¿Cuánto puedo invertir?"'
              }
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isProcessing}
            />
          </div>

          {/* Send / Status */}
          <button
            type="submit"
            className="btn btn-light rounded-circle shadow-sm"
            style={{ width: '42px', height: '42px' }}
            disabled={!inputText.trim() || isProcessing}
          >
            {isProcessing ? (
              <span className="spinner-border spinner-border-sm text-primary"></span>
            ) : (
              <i className="bi bi-arrow-up-circle-fill text-primary fs-5"></i>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
