const CONFIDENCE_LABEL = {
  high: 'Grounded · high confidence',
  medium: 'Grounded · medium confidence',
  low: 'Grounded · low confidence',
  none: 'Not found in your documents',
};

export default function Message({ message }) {
  const isUser = message.role === 'user';
  return (
    <div className={`msg msg-${message.role}`}>
      <div className="msg-bubble">{message.content}</div>

      {!isUser && message.confidence && (
        <div className={`grounding-badge grounding-${message.confidence}`}>
          {CONFIDENCE_LABEL[message.confidence]}
        </div>
      )}

      {!isUser && message.sources?.length > 0 && (
        <details className="sources">
          <summary>Sources ({message.sources.length})</summary>
          {message.sources.map((s, i) => (
            <div className="source-chip" key={i}>
              <span className="source-idx">[{i + 1}]</span> <span className="source-doc">{s.doc_name}</span>
              <div className="source-text">
                {s.text.slice(0, 240)}
                {s.text.length > 240 ? '…' : ''}
              </div>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}
