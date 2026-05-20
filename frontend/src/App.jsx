import { useEffect } from "react";
import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import Marketplace from "./components/Marketplace";
import ItemDetail from "./components/ItemDetail";

function isPublicPath(pathname) {
  return pathname === "/" || pathname.startsWith("/item/");
}

function BodyTheme() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (isPublicPath(pathname)) {
      document.body.dataset.surface = "public";
    } else {
      delete document.body.dataset.surface;
    }
  }, [pathname]);
  return null;
}

function TopNav() {
  const { pathname } = useLocation();
  // Public surfaces (buyer flow) get no chrome — the brief calls for a
  // garage-sale flyer, not a brand. Dashboard keeps the seller nav.
  if (isPublicPath(pathname)) return null;
  return (
    <nav className="nav">
      <NavLink to="/" className="nav-brand">
        <span className="logo-dot" />
        Karthik and Ashton's Moving Sale
      </NavLink>
      <div className="nav-links">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `btn ${isActive ? "btn-secondary" : "btn-ghost"}`}
        >
          Browse
        </NavLink>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `btn ${isActive ? "btn-secondary" : "btn-ghost"}`}
        >
          My Listings
        </NavLink>
      </div>
    </nav>
  );
}

function App() {
  return (
    <BrowserRouter>
      <BodyTheme />
      <TopNav />
      <Routes>
        <Route path="/" element={<Marketplace />} />
        <Route path="/item/:id" element={<ItemDetail />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
