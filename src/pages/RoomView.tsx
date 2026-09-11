/**
 * RoomView.tsx — Interactive seat map for a single room.
 *
 * Loads the room's floor-plan image and seat coordinates from
 * registry.json, renders them on an interactive canvas (RoomCanvas),
 * and exposes seat selection + shareable URL state via useUrlState.
 * Users can click seats, then copy/share the URL so friends can
 * see the same selection.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useLocation, useParams } from 'react-router-dom';

import registry from '../data/registry.json';
import { useUrlState, type SeatValue } from '../hooks/useUrlState';
import { extractMeta } from '../utils/roomMeta';
import {
  RoomCanvas,
  type RoomConfig,
  type ViewportState,
} from '../components/viewer/RoomCanvas';
import { type SeatModel } from '../components/viewer/Seat';
import { SelectedSeatsSidebar } from '../components/viewer/SelectedSeatsSidebar';

type RegistryRoom = (typeof registry.rooms)[number];

/** Derive a clean display name from the image path, e.g. "/maps-masked/LKCSB Seminar Room 1-1.png" → "LKCSB Seminar Room 1-1" */
const displayName = (room: RegistryRoom): string => {
  if (room.image) {
    const file = room.image.replace(/^\/maps(?:-masked)?\//, '').replace(/\.png$/i, '');
    if (file) return file;
  }
  return room.name ?? room.id;
};

const toRoomConfig = (room: RegistryRoom, seatData: Record<string, SeatValue>): RoomConfig => ({
  id: room.id,
  name: displayName(room),
  imageUrl: room.image,
  width: room.width,
  height: room.height,
  seats: room.seats.map((seat) => ({
    id: seat.id,
    x: seat.x,
    y: seat.y,
    status: seatData[seat.id] ? 'reserved' : 'available',
  })),
});

const RoomView = () => {
  const { roomId } = useParams<{ roomId: string }>();
  const location = useLocation();
  const { state, isUrlWriteLimited, shareUrl, urlError, setSeatValue, setSeatData } = useUrlState(roomId ?? '');
  const [selectedSeatId, setSelectedSeatId] = useState<string | undefined>();
  const [copyResult, setCopyResult] = useState<{ url: string; status: 'copying' | 'copied' | 'denied' } | null>(null);
  const copyStatus = copyResult?.url === shareUrl ? copyResult?.status : null;
  const copied = copyStatus === 'copied';

  /* ---- Zoom state (controlled from right panel) ---- */
  const [viewport, setViewport] = useState<ViewportState>({ zoom: 1, panX: 0, panY: 0 });

  const registryRoom = useMemo(
    () => registry.rooms.find((entry) => entry.id === roomId) ?? null,
    [roomId],
  );

  const room = useMemo((): RoomConfig | null => {
    if (!registryRoom) return null;
    return toRoomConfig(registryRoom, state.d);
  }, [registryRoom, state.d]);

  /* ---- Sidebar state ---- */
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  /* Seminar rooms get 30% larger seat dots for easier tapping */
  const seatRadius = useMemo(() => {
    if (!registryRoom) return 18 * 1.3;
    const meta = extractMeta(registryRoom.image, registryRoom.seats.length);
    return meta.type === 'Seminar Room' ? 23 * 1.3 : 18 * 1.3;
  }, [registryRoom]);

  useEffect(() => {
    setSelectedSeatId(undefined);
    setViewport({ zoom: 1, panX: 0, panY: 0 });
    setIsSidebarOpen(false); // Close sidebar on room change
  }, [roomId]);

  const handleSeatSelect = useCallback(
    (seat: SeatModel) => {
      setSelectedSeatId(seat.id);
      const currentValue = state.d[seat.id];
      if (currentValue === undefined) {
        setSeatValue(seat.id, 1);
        setIsSidebarOpen(true); // Auto-open sidebar when selecting a seat
      } else if (currentValue === 1) {
        setSeatValue(seat.id, undefined);
      }
    },
    [setSeatValue, state.d],
  );

  const handleCopyLink = useCallback(async () => {
    if (!shareUrl) return;
    setCopyResult({ url: shareUrl, status: 'copying' });
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(shareUrl);
      setCopyResult({ url: shareUrl, status: 'copied' });
    } catch {
      setCopyResult({ url: shareUrl, status: 'denied' });
    }
  }, [shareUrl]);

  const handleClearAll = useCallback(() => {
    setSeatData({});
    setSelectedSeatId(undefined);
  }, [setSeatData]);

  const zoomReset = useCallback(() => {
    setViewport({ zoom: 1, panX: 0, panY: 0 });
  }, []);

  /* Derive the selected-seats list from URL state */
  const selectedEntries = useMemo(() => {
    return Object.entries(state.d).map(([seatId, value]) => ({
      seatId,
      name: typeof value === 'string' ? value : null,
    }));
  }, [state.d]);

  if (state.r !== roomId && registry.rooms.some((entry) => entry.id === state.r)) {
    return <Navigate to={{ pathname: `/room/${encodeURIComponent(state.r)}`, search: location.search, hash: location.hash }} replace state={location.state} />;
  }

  if (!room || state.r !== roomId) {
    return (
      <main style={{ padding: 24 }}>
        <h1>Room not found</h1>
        <p>We could not find room: {state.r || roomId}</p>
        <Link to="/">Back home</Link>
      </main>
    );
  }

  return (
    <div className="fullscreen-room-view">
      {/* Background Watermark Layer */}
      <div className="watermark-bg" />

      {/* Main Floorplan Canvas Map */}
      <div className="fullscreen-canvas-container">
        <RoomCanvas
          room={room}
          selectedSeatId={selectedSeatId}
          seatRadius={seatRadius}
          onSeatSelect={handleSeatSelect}
          viewportState={viewport}
          onViewportStateChange={setViewport}
        />
      </div>

      {/* Top Overlay Banner */}
      <div className="room-banner">
        <div className="room-banner__left">
          <Link to="/rooms" className="back-link banner-nav">
            <span className="banner-nav__icon">←</span>
            <span>Back</span>
          </Link>
        </div>
        <div className="room-banner__center">
          <h1>{room.name ?? `Room ${room.id}`}</h1>
        </div>
        <div className="room-banner__right">
          <button type="button" className="btn btn--secondary banner-btn-reset" onClick={zoomReset}>
            Reset
          </button>
          <button type="button" className="btn btn--primary banner-btn-copy" onClick={handleCopyLink} disabled={!shareUrl || copyStatus === 'copying'} aria-label={copied ? 'Link copied' : 'Share selection'}>
            {copied ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
              </svg>
            )}
            <span>{copied ? 'Copied!' : 'Share'}</span>
          </button>
        </div>
      </div>

      <p className="share-notice" role="status" aria-live="polite">
        {urlError ?? (copyStatus === 'denied'
          ? 'Copy was blocked. Copy the link from your address bar, or try Share again.'
          : copied ? 'Selection link copied.' : '')}
      </p>

      <SelectedSeatsSidebar
        isOpen={isSidebarOpen}
        selectedSeatId={selectedSeatId}
        selectedEntries={selectedEntries}
        isUrlWriteLimited={isUrlWriteLimited}
        urlError={urlError}
        onToggleOpen={() => setIsSidebarOpen((open) => !open)}
        onClearAll={handleClearAll}
        onSelectSeat={setSelectedSeatId}
        onSetSeatValue={setSeatValue}
      />
    </div>
  );
};

export default RoomView;
