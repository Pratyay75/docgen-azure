import React from "react";
import { Button } from "@mui/material";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/Navbar.css";

function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = JSON.parse(localStorage.getItem("user"));

  const handleLogout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    navigate("/login");
  };

  const handleConfigure = () => {
    // detect current page and save it
    if (location.pathname.startsWith("/viewer")) {
      localStorage.setItem("lastPage", "viewer");
    } else {
      localStorage.setItem("lastPage", "upload");
    }
    navigate("/configure");
  };

  return (
    <header className="nav-outer">
      {/* subtle backlight behind the whole top area */}
      <div className="nav-backlight" aria-hidden="true" />

      <div className="navbar-container">
        <div className="navbar-inner">
          <div className="navbar-left">
            <span
              className="navbar-title"
              onClick={() => navigate("/upload")}
              style={{ cursor: "pointer" }}
            >
              DocGen
            </span>
          </div>

          <div className="navbar-right">
            {/* Configure button visible for all authenticated users */}
            {user && (
              <Button
                className="glass-button config-btn"
                onClick={handleConfigure}
              >
                Configure
              </Button>
            )}

            {user?.role === "superadmin" && (
              <Button
                className="glass-button admin-btn"
                onClick={() => navigate("/admin")}
              >
                Admin Panel
              </Button>
            )}

            <Button className="glass-button logout-btn" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
