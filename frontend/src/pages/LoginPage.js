// src/pages/LoginPage.js
import React, { useState } from "react";
import { TextField, Button, Paper, Typography, Box, CircularProgress } from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "../services/api"; // ✅ use centralized api.js
import ErrorSnackbar from "../components/ErrorSnackbar";
import "../styles/LoginPage.css";

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: "", severity: "error" });

  const navigate = useNavigate();

  const handleLogin = async () => {
    setLoading(true);
    setSnack({ open: false, message: "", severity: "error" });
    try {
      const res = await api.post("/api/users/login", { email, password }); // ✅ no hardcoded base URL

      // Save user + token in localStorage
      localStorage.setItem("user", JSON.stringify(res.data.user));
      localStorage.setItem("token", res.data.token);

      setSnack({ open: true, message: "Login successful", severity: "success" });

      setTimeout(() => {
        if (res.data.user.role === "superadmin") navigate("/admin");
        else navigate("/upload");
      }, 600);
    } catch (err) {
      const msg = err.friendlyMessage || err.response?.data?.detail || "Invalid credentials";
      setSnack({ open: true, message: msg, severity: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="login-page-root">
      <div className="hero-column">
        <div className="hero-badge">AI Document Studio</div>
        <Typography variant="h2" component="h1" className="hero-title">
          Transform your <br /> documents with AI
        </Typography>
        <Typography className="hero-sub">
          Upload files and convert them into structured, editable documents in seconds.
        </Typography>

        <ul className="hero-features">
          <li>Automatic section detection</li>
          <li>Custom AI prompt control</li>
          <li>Streamlined editing and export</li>
        </ul>

        <a className="take-tour" href="#take-a-tour" onClick={(e) => e.preventDefault()}>
          Take a tour →
        </a>
      </div>

      <div className="form-column">
        <Paper elevation={12} className="login-box glass">
          <Typography variant="h5" className="login-title">Welcome Back</Typography>

          <TextField
            label="Email"
            variant="outlined"
            fullWidth
            margin="normal"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            InputProps={{ className: "input-field" }}
          />
          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            InputProps={{ className: "input-field" }}
          />

          <Button
            variant="contained"
            fullWidth
            onClick={handleLogin}
            className="login-btn"
            disabled={loading}
          >
            {loading ? <CircularProgress size={22} /> : "Sign in"}
          </Button>

          <div className="or-signin">or sign in with</div>

          <Button
            variant="outlined"
            fullWidth
            className="google-btn"
            onClick={() => {/* optional: google flow */}}
            disabled={loading}
          >
            <span className="google-icon">G</span> Sign in with Google
          </Button>

          <Button
            variant="text"
            fullWidth
            onClick={() => navigate("/signup")}
            disabled={loading}
            className="signup-link"
          >
            Don't have an account? Sign up
          </Button>
        </Paper>
      </div>

      <ErrorSnackbar
        open={snack.open}
        onClose={() => setSnack({ ...snack, open: false })}
        severity={snack.severity}
        message={snack.message}
      />
    </Box>
  );
}

export default LoginPage;
