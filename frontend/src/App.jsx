import { Navigate, Route, Routes } from "react-router-dom";
import PageFrame from "./components/PageFrame";
import { roleHome, useAuth } from "./auth";
import DoctorView from "./pages/DoctorView";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import MedreaPage from "./pages/MedreaPage";
import PatientView from "./pages/PatientView";
import SurrogateView from "./pages/SurrogateView";

function Guard({ role, children }) {
  const { session } = useAuth();
  if (!session?.user) return <Navigate to="/" replace />;
  if (session.user.role !== role) {
    return <Navigate to={roleHome(session.user.role)} replace />;
  }
  return children;
}

export default function App() {
  return (
    <>
      <PageFrame />
      <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/medrea" element={<MedreaPage />} />
      <Route
        path="/patient"
        element={
          <Guard role="patient">
            <PatientView />
          </Guard>
        }
      />
      <Route
        path="/doctor"
        element={
          <Guard role="doctor">
            <DoctorView />
          </Guard>
        }
      />
      <Route
        path="/surrogate"
        element={
          <Guard role="surrogate">
            <SurrogateView />
          </Guard>
        }
      />
      <Route path="*" element={<HomeRedirect />} />
      </Routes>
    </>
  );
}

function HomeRedirect() {
  const { session } = useAuth();
  if (!session?.user) return <Navigate to="/" replace />;
  return <Navigate to={roleHome(session.user.role)} replace />;
}
