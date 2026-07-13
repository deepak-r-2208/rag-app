export default function FocusStack({ className = '', sources }) {
  return (
    <aside className={`sidebar sidebar-right ${className}`}>
      <div className="sidebar-section">
        <div className="sidebar-title">Focus stack · retrieved passages</div>

        {sources.length === 0 ? (
          <div className="empty-state small">
            <div className="empty-title">Focus stack</div>
            <div className="empty-sub">Ask a question and the most relevant passages will sharpen into view here.</div>
          </div>
        ) : (
          sources.map((c, i) => {
            const blur = Math.max(0, (1 - c.score) * 3.2).toFixed(2);
            const opacity = (0.45 + c.score * 0.55).toFixed(2);
            return (
              <div
                key={i}
                className={`focus-card ${i === 0 ? 'focus-card-top' : ''}`}
                style={{ '--blur': `${blur}px`, '--op': opacity }}
              >
                {i === 0 && <span className="focus-tag">IN FOCUS</span>}
                <div className="focus-score">{Math.round(c.score * 100)}%</div>
                <div className="focus-doc">{c.doc_name}</div>
                <div className="focus-text">
                  {c.text.slice(0, 180)}
                  {c.text.length > 180 ? '…' : ''}
                </div>
                <div className="focus-meta">
                  lex {c.lexical_score.toFixed(2)} · vec {c.vector_score.toFixed(2)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
