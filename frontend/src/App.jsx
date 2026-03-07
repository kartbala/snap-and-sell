import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import Marketplace from "./components/Marketplace";

function App() {
  return (
    <BrowserRouter>
      <nav className="nav">
        <NavLink to="/" className="nav-brand">
          <span className="logo-dot" />
          Snap & Sell
        </NavLink>
        <div className="nav-links">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `btn ${isActive ? "btn-secondary" : "btn-ghost"}`
            }
          >
            Browse
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `btn ${isActive ? "btn-secondary" : "btn-ghost"}`
            }
          >
            My Listings
          </NavLink>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<Marketplace />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
