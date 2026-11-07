'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

interface UseVoiceRecognitionOptions {
  lang?: string;
  silenceTimeoutMs?: number;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: any) => void;
}

export function useVoiceRecognition(options: UseVoiceRecognitionOptions = {}) {
  const { lang = 'es-CO', silenceTimeoutMs = 1200, onResult, onError } = options;
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0); // 0 to 100%

  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const accumulatedTextRef = useRef<string>('');
  const isFinalizedRef = useRef<boolean>(false);

  // Keep latest callbacks in refs so SpeechRecognition is never recreated mid-speech
  const onResultRef = useRef(onResult);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Clean audio meter and hardware microphone stream
  const stopAudioMeter = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

  const stopListening = useCallback(() => {
    isFinalizedRef.current = true;
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
    }
    stopAudioMeter();
    accumulatedTextRef.current = '';
    setTranscript('');
    setIsListening(false);
  }, [stopAudioMeter]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setIsSupported(false);
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        // Ignore any trailing events after command was already detected and stopped
        if (isFinalizedRef.current) {
          return;
        }

        let fullTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript + ' ';
        }
        const cleanText = fullTranscript.trim();
        if (!cleanText) return;

        accumulatedTextRef.current = cleanText;
        setTranscript(cleanText);

        if (onResultRef.current) {
          onResultRef.current(cleanText, false);
        }

        // Reset silence timer on every new detected word
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }

        silenceTimerRef.current = setTimeout(() => {
          const finalCommand = accumulatedTextRef.current.trim();
          if (finalCommand && !isFinalizedRef.current) {
            // 1. Mark finalized & stop listening immediately
            isFinalizedRef.current = true;
            if (recognitionRef.current) {
              try {
                recognitionRef.current.stop();
              } catch (_) {}
            }
            stopAudioMeter();
            setIsListening(false);

            // 2. Delete transcript state
            accumulatedTextRef.current = '';
            setTranscript('');

            // 3. Emit final command to trigger modal & clear input
            if (onResultRef.current) {
              onResultRef.current(finalCommand, true);
            }
          }
        }, silenceTimeoutMs);
      };

      recognition.onerror = (event: any) => {
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          console.warn('SpeechRecognition error:', event.error);
        }
        if (onErrorRef.current) onErrorRef.current(event);
      };

      recognition.onend = () => {
        // If browser ended recognition naturally and we have unsubmitted text, finalize it now
        const pendingText = accumulatedTextRef.current.trim();
        if (pendingText && !isFinalizedRef.current) {
          isFinalizedRef.current = true;
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
          accumulatedTextRef.current = '';
          setTranscript('');
          if (onResultRef.current) {
            onResultRef.current(pendingText, true);
          }
        }
        setIsListening(false);
        stopAudioMeter();
      };

      recognitionRef.current = recognition;
    }

    return () => {
      isFinalizedRef.current = true;
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
      stopAudioMeter();
    };
  }, [lang, silenceTimeoutMs, stopAudioMeter]);

  const startListening = useCallback(async () => {
    if (!isSupported) return;
    isFinalizedRef.current = false;
    accumulatedTextRef.current = '';
    setTranscript('');

    // 1. Enable Hardware Auto Gain Control, Noise Suppression and Echo Cancellation
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            autoGainControl: true,
            noiseSuppression: true,
            echoCancellation: true,
            channelCount: 1,
          },
        });
        mediaStreamRef.current = stream;

        // Web Audio Analyser for volume indicator
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          audioContextRef.current = ctx;
          const source = ctx.createMediaStreamSource(stream);
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 256;
          source.connect(analyser);
          analyserRef.current = analyser;

          const dataArray = new Uint8Array(analyser.frequencyBinCount);
          const updateVolume = () => {
            if (!analyserRef.current) return;
            analyserRef.current.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const avg = sum / dataArray.length;
            const level = Math.min(100, Math.round((avg / 128) * 100));
            setAudioLevel(level);
            animFrameRef.current = requestAnimationFrame(updateVolume);
          };
          updateVolume();
        }
      }
    } catch (e) {
      console.warn('Microphone AutoGain not initialized, continuing with standard SpeechRecognition:', e);
    }

    // 2. Start SpeechRecognition
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error('Error starting recognition:', e);
      }
    }
  }, [isSupported]);

  return {
    isListening,
    transcript,
    isSupported,
    audioLevel,
    startListening,
    stopListening,
  };
}
