// src/components/ErrorSnackbar.js
import React from "react";
import { Snackbar, Alert } from "@mui/material";

export default function ErrorSnackbar({ open, onClose, severity = "error", message = "" }) {
  return (
    <Snackbar open={open} autoHideDuration={6000} onClose={onClose} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
      <Alert onClose={onClose} severity={severity} sx={{ width: "100%" }}>
        {message}
      </Alert>
    </Snackbar>
  );
}
