import { useEffect, useRef, useState } from 'react';
import Message from './Message';
import VoiceButton from './VoiceButton';

export default function ChatPanel({ messages, onAsk, asking, voiceEnabled }) {
  const [input, setInput] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  function submit(e) {
    e.preventDefault();
    if (!input.trim()) return;
    const q = input;
    setInput('');
    onAsk(q);
  }

  return (
    <div className="main-col">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">Ask something about your documents</div>
            <div className="empty-sub">Answers are grounded only in what you've uploaded — no outside guessing.</div>
          </div>
        ) : (
          messages.map((m) => <Message key={m.id} message={m} />)
        )}
      </div>

      {asking && (
        <div className="typing-indicator">
          <span />
          <span />
          <span />
        </div>
      )}

      <div className="composer-wrap">
        <form className="composer-form" onSubmit={submit}>
          {voiceEnabled && <VoiceButton onTranscript={setInput} disabled={asking} />}
          <textarea
            className="composer-input"
            rows={1}
            placeholder="Ask about your documents…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={asking}
          />
          <button type="submit" className="send-round" disabled={asking || !input.trim()} title="Send">
            →
          </button>
        </form>
        <div className="composer-hint">
          Answers are grounded only in your uploaded documents — RAGnify will say so if it doesn't know.
        </div>
      </div>
    </div>
  );
}
