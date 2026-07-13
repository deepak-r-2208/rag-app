const MODELS = [
  { id: 'all-minilm', name: 'MiniLM (fast)', desc: '46MB, 384-dim. Quick and light.' },
  { id: 'nomic-embed-text', name: 'Nomic Embed (quality)', desc: '274MB, 768-dim. Stronger semantic recall.' },
];

export default function SettingsPanel({ settings, onChange, onClose }) {
  const weightLabel =
    settings.hybrid_weight < 0.34 ? 'Mostly keyword' : settings.hybrid_weight > 0.66 ? 'Mostly vector' : 'Balanced hybrid';

  return (
    <div className="settings-panel">
      <div className="settings-head">
        <h2>Settings</h2>
        <button className="icon-btn" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="settings-block">
        <div className="settings-label">Embedding model</div>
        {MODELS.map((m) => (
          <div
            key={m.id}
            className={`model-option ${settings.embedding_model === m.id ? 'model-option-active' : ''}`}
            onClick={() => onChange({ embedding_model: m.id })}
          >
            <div className="model-name">{m.name}</div>
            <div className="model-desc">{m.desc}</div>
          </div>
        ))}
        <div className="settings-note">
          Both run through your local Ollama instance — free, open-source, no per-call API cost.
        </div>
      </div>

      <div className="settings-block">
        <div className="settings-label">Hybrid search balance</div>
        <input
          type="range"
          min="0"
          max="100"
          value={Math.round(settings.hybrid_weight * 100)}
          onChange={(e) => onChange({ hybrid_weight: Number(e.target.value) / 100 })}
        />
        <div className="slider-labels">
          <span>Keyword</span>
          <span>Vector</span>
        </div>
        <div style={{ textAlign: 'center', fontSize: 12.5, fontWeight: 600, marginTop: 6 }}>{weightLabel}</div>
      </div>

      <div className="settings-block">
        <div className="toggle-row">
          <div>
            <div className="model-name">Voice input</div>
            <div className="model-desc">Ask questions by speaking.</div>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={settings.voice_enabled}
              onChange={(e) => onChange({ voice_enabled: e.target.checked })}
            />
            <span className="slider-track" />
          </label>
        </div>
      </div>
    </div>
  );
}
