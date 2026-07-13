import { useRef, useState } from 'react';

const ICONS = {
  pdf: 'PDF', docx: 'DOC', txt: 'TXT', md: 'MD', csv: 'CSV', json: 'JSN',
  png: 'IMG', jpg: 'IMG', jpeg: 'IMG', webp: 'IMG',
};

export default function Sidebar({
  className = '',
  sessions,
  currentSessionId,
  onSelectSession,
  onNewSession,
  onDeleteSession,
  documents,
  onUpload,
  onDeleteDocument,
}) {
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);

  return (
    <aside className={`sidebar ${className}`}>
      <div className="sidebar-left-top">
        <button className="btn btn-ghost" style={{ width: '100%' }} onClick={onNewSession}>
          + New conversation
        </button>
      </div>

      <div className="session-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`session-item ${s.id === currentSessionId ? 'session-active' : ''}`}
            onClick={() => onSelectSession(s.id)}
          >
            <span className="session-title">{s.title}</span>
            <button
              className="session-del"
              title="Delete conversation"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteSession(s.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-title">Documents</div>
        <div
          className={`dropzone ${dragActive ? 'dropzone-active' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            setDragActive(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            if (e.dataTransfer.files.length) onUpload(e.dataTransfer.files);
          }}
        >
          <strong>Click to upload</strong> or drag files here
          <br />
          <span style={{ fontSize: 11 }}>PDF · DOCX · TXT · CSV · JSON · PNG/JPG (OCR)</span>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.md,.csv,.json,.pdf,.docx,.png,.jpg,.jpeg,.webp"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files.length) onUpload(e.target.files);
              e.target.value = '';
            }}
          />
        </div>

        <div className="doc-list">
          {documents.length === 0 && (
            <div className="empty-state small">
              <div className="empty-title">No documents yet</div>
              <div className="empty-sub">Upload files to get started.</div>
            </div>
          )}
          {documents.map((d) => (
            <div className="doc-item" key={d.id}>
              <div className="doc-icon">{ICONS[d.file_type] || 'DOC'}</div>
              <div className="doc-meta">
                <div className="doc-name">{d.name}</div>
                <div className="doc-sub">
                  {d.chunk_count} chunks · .{d.file_type}
                </div>
              </div>
              <button className="session-del" title="Delete document" onClick={() => onDeleteDocument(d.id)}>
                ×
              </button>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
