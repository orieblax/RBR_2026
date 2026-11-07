'use client';

import React, { useState } from 'react';
import { useVoiceRecognition } from '@/hooks/useVoiceRecognition';
import { authFetch } from '@/lib/api';

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
      const data = await authFetch('/api/py/voice/command', {
        method: 'POST',
        body: JSON.stringify({ command: commandText.trim() }),
      });

      if (data.type === 'stage_action') {
        onStageAction(data.staged_action);
      } else if (data.reply) {
        setAgentReply(data.reply);
        if (data.needs_refresh) {
          onRefreshData();
        }
      }
    } catch (err: any) {
      console.error('Error executing voice command:', err);
      setAgentReply(err.message || 'Error de comunicación con el asistente de voz.');
    } finally {
      setIsProcessing(false);
      setInputText('');
    }
  };

  const { isListening, isSupported, audioLevel, startListening, stopListening } =
    useVoiceRecognition({
      lang: 'es-CO',
      silenceTimeoutMs: 1800,
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
        <div
          className="alert alert-info alert-dismissible fade show shadow-sm rounded-4 mb-2 py-2 px-3 small border-0 d-flex align-items-center justify-content-between"
          role="alert"
        >
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
            className={`btn voice-pulse-btn ${
              isListening ? 'listening btn-danger' : 'btn-primary'
            } text-white border-0`}
            title={isListening ? 'Detener escucha' : 'Activar micrófono por voz con Auto-Gain (es-CO)'}
            disabled={!isSupported && false}
          >
            <i className={`bi ${isListening ? 'bi-mic-fill' : 'bi-mic'}`}></i>
          </button>

          {/* Transcript / Input + Volume Meter */}
          <div className="flex-grow-1 px-2 position-relative">
            <input
              type="text"
              className="form-control border-0 shadow-none bg-transparent"
              placeholder={
                isListening
                  ? 'Escuchando en español... Habla natural, espera 1.8s o pulsa Enviar'
                  : 'Prueba: "Gasté 50000 en transporte desde mi bolsillo" o "Marcar pagado Gas"'
              }
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isProcessing}
            />

            {/* Visual Live Audio Level Indicator */}
            {isListening && (
              <div
                className="progress position-absolute bottom-0 start-0 w-100"
                style={{ height: '3px', borderRadius: '0' }}
              >
                <div
                  className="progress-bar bg-success transition-all"
                  role="progressbar"
                  style={{
                    width: `${Math.max(5, audioLevel)}%`,
                    transition: 'width 0.1s ease',
                  }}
                  aria-valuenow={audioLevel}
                  aria-valuemin={0}
                  aria-valuemax={100}
                ></div>
              </div>
            )}
          </div>

          {/* Send / Status */}
          <button
            type="submit"
            className="btn btn-light rounded-circle shadow-sm"
            style={{ width: '42px', height: '42px' }}
            disabled={!inputText.trim() || isProcessing}
            title="Enviar comando"
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
