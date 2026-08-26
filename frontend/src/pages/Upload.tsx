import { useState } from 'react';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { postUpload } from '../services/api';
import type { UploadResponse } from '../services/types';
import { Card, ErrorState } from '../components/ui';
import { fmtInt, shortHash } from '../utils/format';

export function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const { run, pending, error, result } = useAsyncAction<File, UploadResponse>(postUpload);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Upload</h1>
        <p className="muted">
          Store a scene/raster on the backend (content-addressed, git-ignored). The file is hashed and
          recorded; wiring an uploaded raster into <code>/predict</code> is future work (out of M14 scope).
        </p>
      </div>

      <div className="grid-2">
        <Card title="Choose a file">
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              if (file) void run(file);
            }}
          >
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              aria-label="File to upload"
            />
            <button className="btn primary" type="submit" disabled={pending || !file}>
              {pending ? 'Uploading…' : 'Upload'}
            </button>
          </form>
        </Card>

        <Card title="Result">
          {error && <ErrorState error={error} />}
          {!error && !result && <p className="muted">Pick a file and upload it.</p>}
          {result && (
            <dl className="kv">
              <dt>upload_id</dt><dd className="mono">{result.upload_id}</dd>
              <dt>filename</dt><dd>{result.filename}</dd>
              <dt>content hash</dt><dd className="mono">{shortHash(result.content_hash, 16)}</dd>
              <dt>size</dt><dd>{fmtInt(result.size_bytes)} bytes</dd>
              <dt>content type</dt><dd>{result.content_type || '—'}</dd>
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}
