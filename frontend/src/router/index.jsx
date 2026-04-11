import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { LoadingBlock } from "../components/LoadingBlock";
import { useAuth } from "../hooks/useAuth";
import { AppLayout } from "../layouts/AppLayout";
import { ConsultationCreatePage } from "../pages/ConsultationCreatePage";
import { ConsultationDetailPage } from "../pages/ConsultationDetailPage";
import { ConsultationHistoryPage } from "../pages/ConsultationHistoryPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingBlock label="Validando sesion..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate replace to="/consultations/new" />} />
            <Route path="/consultations/new" element={<ConsultationCreatePage />} />
            <Route path="/consultations" element={<ConsultationHistoryPage />} />
            <Route path="/consultations/:id" element={<ConsultationDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
