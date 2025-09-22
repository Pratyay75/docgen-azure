// src/pages/SignupPage.js
import React, { useState } from "react";
import { TextField, Button, Paper, Typography, Box, CircularProgress } from "@mui/material";
import { useNavigate } from "react-router-dom";
import api from "../services/api"; // ✅ use centralized API instance
import ErrorSnackbar from "../components/ErrorSnackbar";
import "../styles/SignupPage.css";

function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: "", severity: "error" });

  const navigate = useNavigate();

  // --- Core signup logic ---
  const handleSignup = async () => {
    setLoading(true);
    setSnack({ open: false, message: "", severity: "error" });
    try {
      const res = await api.post("/api/users/signup", { name, email, password }); // ✅ no hardcoded URL

      // Save user and token in localStorage
      localStorage.setItem("user", JSON.stringify(res.data.user));
      localStorage.setItem("token", res.data.token);

      setSnack({ open: true, message: "Account created", severity: "success" });

      setTimeout(() => navigate("/upload"), 600);
    } catch (err) {
      const msg = err.friendlyMessage || err.response?.data?.detail || "Signup failed";
      setSnack({ open: true, message: msg, severity: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box className="signup-page-root">
      {/* LEFT HERO */}
      <div className="heroColumn">
        <div className="heroBadge">AI Document Studio</div>
        <Typography component="h1" className="heroTitle">
          Transform your <br /> documents with AI
        </Typography>
        <Typography className="heroSub">
          Upload files and convert them into structured, editable documents in seconds.
        </Typography>
        <ul className="heroFeatures">
          <li>Automatic section detection</li>
          <li>Custom AI prompt control</li>
          <li>Streamlined editing and export</li>
        </ul>
        <a className="takeTour" href="#take-a-tour" onClick={(e) => e.preventDefault()}>
          Take a tour →
        </a>
      </div>

      {/* RIGHT FORM */}
      <div className="formColumn">
        <Paper elevation={12} className="card glass">
          <Typography variant="h5" className="cardTitle">Get started</Typography>

          <TextField
            label="Name"
            variant="outlined"
            fullWidth
            margin="normal"
            value={name}
            onChange={(e) => setName(e.target.value)}
            InputProps={{ className: "inputRoot" }}
            InputLabelProps={{ className: "inputLabel" }}
          />
          <TextField
            label="Email"
            variant="outlined"
            fullWidth
            margin="normal"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            InputProps={{ className: "inputRoot" }}
            InputLabelProps={{ className: "inputLabel" }}
          />
          <TextField
            label="Password"
            type="password"
            variant="outlined"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            InputProps={{ className: "inputRoot" }}
            InputLabelProps={{ className: "inputLabel" }}
          />

          <Button
            variant="contained"
            fullWidth
            onClick={handleSignup}
            className="primaryBtn"
            disabled={loading}
          >
            {loading ? <CircularProgress size={22} /> : "Sign up"}
          </Button>

          <div className="orText">or sign up with</div>

          <Button
            variant="outlined"
            fullWidth
            className="googleBtn"
            onClick={() => {}}
            disabled={loading}
          >
            <span className="googleIcon">G</span> Sign up with Google
          </Button>

          <Button
            variant="text"
            fullWidth
            onClick={() => navigate("/login")}
            disabled={loading}
            className="switchLink"
          >
            Already have an account? Sign in
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

export default SignupPage;
