import 'leaflet/dist/leaflet.css';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { Card, RegimeBadge } from '../components/ui';

// A base map with a clearly-labelled DEMO marker. Geo-referenced overlay of predicted masks is DEFERRED:
// the backend has no geo-prediction endpoint and /predict returns class counts, not georeferenced pixels.
// CircleMarker (SVG) is used deliberately to avoid Leaflet's bundler marker-icon asset issues.
const DEMO_POINT: [number, number] = [-12.05, -77.05]; // near Lima, Peru — a CloudSEN12 ROI region (DEMO)

export function MapViewer() {
  return (
    <div className="page">
      <div className="page-head">
        <h1>Map viewer</h1>
        <p className="muted">
          <RegimeBadge regime="DEMO" /> Base map only. Prediction geo-overlay is{' '}
          <RegimeBadge regime="DEFERRED" /> — no geo-prediction endpoint exists, and no mask is fabricated.
        </p>
      </div>

      <Card title="Base map (OpenStreetMap)">
        <div className="map-wrap">
          <MapContainer center={DEMO_POINT} zoom={4} scrollWheelZoom={false} className="map">
            <TileLayer
              attribution='&copy; OpenStreetMap contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <CircleMarker center={DEMO_POINT} radius={9} pathOptions={{ color: '#fdae61', fillOpacity: 0.6 }}>
              <Popup>DEMO location (CloudSEN12 ROI region). No real prediction overlay.</Popup>
            </CircleMarker>
          </MapContainer>
        </div>
        <p className="muted small">
          Real CloudSEN12 rasters carry CRS + geotransform; overlaying predicted masks in map space is future
          work (would need a geo-aware prediction endpoint returning georeferenced pixels).
        </p>
      </Card>
    </div>
  );
}
