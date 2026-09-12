/**
 * App.tsx — Root router.
 *
 * Defines every client-side route in the SPA:
 *   /         → Landing page (Home)
 *   /rooms    → Filterable room browser (RoomsPage)
 *   /room/:id → Interactive seat map for a single room (RoomView)
 *   /edit     → Seat-position editor for contributors (EditSeats, gated)
 *   /compare  → Image-processing comparison sandbox (Compare)
 *   *         → Fallback redirect to /
 */
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import { RouteErrorBoundary } from './components/RouteErrorBoundary';

const RoomView = lazy(() => import('./pages/RoomView'));
const RoomsPage = lazy(() => import('./pages/RoomsPage'));
const EditSeats = lazy(() => import('./pages/EditSeats'));
const Compare = lazy(() => import('./pages/Compare'));

const App = () => {
  const isEditorEnabled = import.meta.env.DEV || import.meta.env.VITE_ENABLE_EDITOR === 'true';
  const location = useLocation();

  return (
    <RouteErrorBoundary key={location.pathname}>
      <Suspense fallback={<main className="route-status" role="status">Loading page…</main>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/room/:roomId" element={<RoomView />} />
          <Route path="/edit" element={isEditorEnabled ? <EditSeats /> : <Navigate to="/" replace />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </RouteErrorBoundary>
  );
};

export default App;
