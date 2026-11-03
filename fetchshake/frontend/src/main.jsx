
import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Download,
  Link2,
  ShieldCheck,
  Zap,
  Image,
  Video,
  LoaderCircle,
  AlertCircle,
  CheckCircle2,
  Globe,
  Coffee,
  Clipboard,
  Scan,
} from 'lucide-react';

import './style.css';

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const platforms = [
  'YouTube',
  'Instagram',
  'Facebook',
  'X / Twitter',
  'TikTok',
  'Reddit',
  'Pinterest',
  'Vimeo',
];

function App() {
  const [url, setUrl] = useState('');
  const [type, setType] = useState('auto');
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  async function analyze(e) {
    e?.preventDefault();

    setError('');
    setData(null);

    if (!url.trim()) {
      return setError('Paste a link first.');
    }

    try {
      new URL(url);
    } catch {
      return setError('Please enter a valid URL including https://');
    }

    setBusy(true);

    try {
      const res = await fetch(`${API}/api/v1/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          media_type: type,
        }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.detail || 'Could not analyze this link.');
      }

      setData(json);
    } catch (err) {
      setError(err.message || 'Could not connect to Fetchshek API.');
    } finally {
      setBusy(false);
    }
  }

  async function downloadMedia(formatId) {
    setDownloading(true);
    setError('');

    try {
      const res = await fetch(`${API}/api/v1/download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url,
          media_type: type,
          format_id: formatId,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Download failed.');
      }

      const blob = await res.blob();
      const disposition = res.headers.get('content-disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || 'fetchshek-media';

      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');

      anchor.href = objectUrl;
      anchor.download = filename;

      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (err) {
      setError(err.message || 'Download failed.');
    } finally {
      setDownloading(false);
    }
  }

  async function pasteLink() {
    try {
      const text = await navigator.clipboard.readText();

      if (text) {
        setUrl(text.trim());
        setData(null);
        setError('');
      }
    } catch {
      setError('Clipboard access is unavailable. Paste your link manually.');
    }
  }

  function clearForm() {
    setUrl('');
    setData(null);
    setError('');
  }

  return (
    <div className="page">
      <nav className="nav wrap">
        <a className="brand" href="#">
          <span className="brand-icon">
            <Download size={19} />
          </span>
          <span className="brand-name">Fetchshek</span>
        </a>

        <div className="nav-right">
          <a href="#sources" className="nav-text">Supported sources</a>

          <span className="nav-pill">
            <span className="status-dot" />
            Free to use
          </span>

          <a
            href="https://x.com/call_me_tiwari"
            target="_blank"
            rel="noreferrer"
            className="nav-pill"
          >
            <Globe size={13} />
            @call_me_tiwari
          </a>

          <a
            href="https://buymeacoffee.com/call_me_tiwari"
            target="_blank"
            rel="noreferrer"
            className="nav-pill"
          >
            <Coffee size={13} />
            Buy Me a Coffee
          </a>
        </div>
      </nav>

      <main className="wrap">
        <section className="hero">
          <div className="eyebrow">SIMPLE. FAST. ALL IN ONE.</div>

          <h1>
            Your media. <em>One simple link.</em>
          </h1>

          <p className="sub">
            Paste a public video or image link. Fetchshek finds the available
            media and prepares it for download.
          </p>

          <form className="panel" onSubmit={analyze}>
            <div className="panel-heading">
              <label className="input-label" htmlFor="media-url">
                Paste your link
              </label>
              <span className="public-label">
                <Globe size={12} />
                Public links only
              </span>
            </div>

            <div className="url-row">
              <Link2 className="url-icon" size={18} />

              <input
                id="media-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
              />

              {url && (
                <button
                  className="clear"
                  type="button"
                  onClick={clearForm}
                >
                  Clear
                </button>
              )}

              <button
                className="paste-btn"
                type="button"
                onClick={pasteLink}
              >
                <Clipboard size={13} />
                Paste
              </button>
            </div>

            <div className="form-bottom">
              <div className="select-wrap">
                <span>Media type</span>

                <div className="type-options">
                  <button
                    type="button"
                    className={type === 'auto' ? 'type-option active' : 'type-option'}
                    onClick={() => setType('auto')}
                  >
                    <Scan size={14} />
                    Auto detect
                  </button>

                  <button
                    type="button"
                    className={type === 'video' ? 'type-option active' : 'type-option'}
                    onClick={() => setType('video')}
                  >
                    <Video size={14} />
                    Video
                  </button>

                  <button
                    type="button"
                    className={type === 'image' ? 'type-option active' : 'type-option'}
                    onClick={() => setType('image')}
                  >
                    <Image size={14} />
                    Images
                  </button>
                </div>
              </div>

              <button
                className="primary"
                disabled={busy || !url.trim()}
                type="submit"
              >
                {busy ? (
                  <>
                    <LoaderCircle className="spin" size={16} />
                    Analyzing
                  </>
                ) : (
                  <>
                    Analyze link
                    <span className="button-arrow">→</span>
                  </>
                )}
              </button>
            </div>

            <p className="helper-text">
              <AlertCircle size={12} />
              Analyze first, then choose from the available media and formats.
            </p>
          </form>

          {error && (
            <div className="error">
              <AlertCircle size={17} />
              {error}
            </div>
          )}

          {data && (
            <section className="result">
              <div className="result-head">
                <div>
                  <div className="success-label">
                    <CheckCircle2 size={14} />
                    MEDIA FOUND
                  </div>

                  <h2>{data.title || 'Your media is ready'}</h2>

                  <p>{data.platform} · {data.media_type}</p>
                </div>

                <span className="type-icon">
                  {data.media_type === 'image' ? <Image /> : <Video />}
                </span>
              </div>

              {data.thumbnail && (
                <img
                  className="thumbnail"
                  src={data.thumbnail}
                  alt="Media preview"
                  referrerPolicy="no-referrer"
                />
              )}

              <div className="formats">
                <div className="format-title">
                  AVAILABLE DOWNLOAD QUALITY
                </div>

                {data.formats?.map((format, index) => (
                  <div
                    className="format"
                    key={`${format.format_id}-${index}`}
                  >
                    <div>
                      <strong>
                        {format.label || format.resolution || 'Original quality'}
                      </strong>

                      <small>
                        {format.description ||
                          format.ext?.toUpperCase() ||
                          'Original media'}
                      </small>
                    </div>

                    <button
                      className="download-btn"
                      disabled={downloading || !format.available}
                      onClick={() => downloadMedia(format.format_id)}
                    >
                      {downloading ? (
                        <LoaderCircle className="spin" size={15} />
                      ) : (
                        <Download size={15} />
                      )}

                      {format.available ? 'Download' : 'Unavailable'}
                    </button>
                  </div>
                ))}
              </div>

              <p className="fine">
                Available quality depends on the original media and source
                platform. Only download content you have permission to save.
              </p>
            </section>
          )}

          <div className="platforms" id="sources">
            <span>SUPPORTED SOURCES INCLUDE</span>

            <div>
              {platforms.map((platform) => (
                <b key={platform}>{platform}</b>
              ))}
            </div>
          </div>
        </section>

        <section className="features">
          <article>
            <span><Zap size={19} /></span>
            <div>
              <h3>Quick analysis</h3>
              <p>
                Find supported media and available formats from a single URL.
              </p>
            </div>
          </article>

          <article>
            <span><Image size={19} /></span>
            <div>
              <h3>Images & videos</h3>
              <p>
                Direct image and video links, plus supported public posts.
              </p>
            </div>
          </article>

          <article>
            <span><ShieldCheck size={19} /></span>
            <div>
              <h3>Responsibly designed</h3>
              <p>
                No DRM circumvention or access-control bypass. Respect creator rights.
              </p>
            </div>
          </article>
        </section>

        <div className="permission-note">
          <ShieldCheck size={13} />
          Only download content you own or have permission to save.
        </div>
      </main>

      <footer className="wrap">
        <span>Fetchshek</span>
        <span>Your media. One simple link.</span>
      </footer>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
