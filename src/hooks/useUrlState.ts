/**
 * useUrlState.ts — Shareable seat-selection state via URL.
 *
 * Encodes the selected room ID and chosen seats into a compact,
 * lz-string-compressed query parameter (?s=…). When the page loads
 * the hook reads the URL, decompresses the state, and returns the
 * seat map so the room view can highlight the correct seats.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from 'lz-string';

const QUERY_PARAM_KEY = 's';
const MAX_ENCODED_STATE_LENGTH = 1800;

export type SeatValue = 1 | string;
export type SeatDataMap = Record<string, SeatValue>;

export interface SessionState {
  r: string;
  d: SeatDataMap;
}

const DEFAULT_SESSION_STATE: SessionState = {
  r: '',
  d: {},
};

const isSeatValue = (value: unknown): value is SeatValue =>
  value === 1 || typeof value === 'string';

const isSeatDataMap = (value: unknown): value is SeatDataMap => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  return Object.values(value).every(isSeatValue);
};

const isSessionState = (value: unknown): value is SessionState => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const candidate = value as Partial<SessionState>;
  return typeof candidate.r === 'string' && isSeatDataMap(candidate.d);
};

const decodeSessionState = (encoded: string | null): SessionState | null => {
  if (!encoded || encoded.length > MAX_ENCODED_STATE_LENGTH) {
    return null;
  }

  try {
    const decompressed = decompressFromEncodedURIComponent(encoded);
    if (!decompressed) {
      return null;
    }

    const parsed = JSON.parse(decompressed) as unknown;
    if (!isSessionState(parsed)) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
};

const encodeSessionState = (state: SessionState): string =>
  compressToEncodedURIComponent(JSON.stringify(state));

export interface UseUrlStateResult {
  state: SessionState;
  isUrlWriteLimited: boolean;
  shareUrl: string | null;
  urlError: string | null;
  setSeatData: (seatData: SeatDataMap) => void;
  setSeatValue: (seatId: string, value: SeatValue | undefined) => void;
  clearState: () => void;
}

export const useUrlState = (roomId: string): UseUrlStateResult => {
  const location = useLocation();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<{
    location: typeof location;
    state: SessionState;
    error: string | null;
  } | null>(null);
  const decoded = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const parsed = decodeSessionState(params.get(QUERY_PARAM_KEY));
    return {
      state: parsed ? { ...parsed, r: parsed.r || roomId } : { r: roomId, d: {} },
      invalid: params.has(QUERY_PARAM_KEY) && !parsed,
    };
  }, [location.search, roomId]);
  const currentDraft = draft?.location === location ? draft : null;
  const state = currentDraft?.state ?? decoded.state;
  const encoded = useMemo(() => encodeSessionState(state), [state]);
  const isUrlWriteLimited = encoded.length > MAX_ENCODED_STATE_LENGTH;
  const urlError = currentDraft ? currentDraft.error : (decoded.invalid
    ? 'This link contains an invalid or oversized selection. Select seats to start a new link.'
    : null);

  // A new history entry owns its selection; a previous unsaved draft must not
  // overwrite Back/Forward or a different room. No polling is needed.
  useEffect(() => setDraft(null), [location]);

  const shareUrl = useMemo(() => {
    if (urlError || isUrlWriteLimited || typeof window === 'undefined') return null;
    const url = new URL(`${location.pathname}${location.search}${location.hash}`, window.location.origin);
    url.searchParams.set(QUERY_PARAM_KEY, encoded);
    return url.toString();
  }, [encoded, isUrlWriteLimited, location, urlError]);

  const updateState = useCallback((updater: (prev: SessionState) => SessionState) => {
    const next = updater(state);
    const nextEncoded = encodeSessionState(next);
    if (nextEncoded.length > MAX_ENCODED_STATE_LENGTH) {
      setDraft({ location, state: next, error: 'Selection too large to share. Shorten names or remove seats. These changes are only in this tab.' });
      return;
    }
    const params = new URLSearchParams(location.search);
    params.set(QUERY_PARAM_KEY, nextEncoded);
    try {
      // BrowserRouter schedules location updates as transitions. Keep the input
      // value current immediately so fast typing cannot lose intermediate keys.
      setDraft({ location, state: next, error: null });
      // Navigate through the router so its location, history metadata and UI
      // agree. This runs in the event handler, never in a React state updater.
      void navigate({ pathname: location.pathname, search: `?${params}`, hash: location.hash }, { replace: true, state: location.state });
    } catch {
      setDraft({ location, state: next, error: 'Unable to save this selection in the link. Your changes are only in this tab; edit again to retry.' });
    }
  }, [location, navigate, state]);

  const setSeatData = useCallback(
    (seatData: SeatDataMap) => {
      updateState((prev) => ({ ...prev, d: { ...seatData } }));
    },
    [updateState],
  );

  const setSeatValue = useCallback(
    (seatId: string, value: SeatValue | undefined) => {
      updateState((prev) => {
        const nextData = { ...prev.d };

        if (value === undefined) {
          delete nextData[seatId];
        } else {
          nextData[seatId] = value;
        }

        return { ...prev, d: nextData };
      });
    },
    [updateState],
  );

  const clearState = useCallback(() => {
    updateState(() => ({ ...DEFAULT_SESSION_STATE, r: roomId }));
  }, [roomId, updateState]);
  return useMemo(
    () => ({
      state,
      isUrlWriteLimited,
      shareUrl,
      urlError,
      setSeatData,
      setSeatValue,
      clearState,
    }),
    [clearState, isUrlWriteLimited, shareUrl, urlError, setSeatData, setSeatValue, state],
  );
};
