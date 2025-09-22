// src/pages/UploadPage.js
import React, { useState, useRef, useEffect } from "react";
import { CircularProgress, Menu, MenuItem, IconButton } from "@mui/material";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import SearchIcon from "@mui/icons-material/Search";
import AddIcon from "@mui/icons-material/Add";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import ErrorSnackbar from "../components/ErrorSnackbar";
import "../styles/UploadPage.css";

export default function UploadPage() {
  const [documents, setDocuments] = useState([]);
  const [rawText, setRawText] = useState(localStorage.getItem("draft_raw_text") || "");
  const [loading, setLoading] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: "", severity: "error" });
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const textareaRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await axios.get("http://127.0.0.1:8000/api/documents/my-documents", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDocuments(res.data?.documents || []);
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  const handleFileUpload = async (fileOrEvent) => {
    const file = fileOrEvent instanceof File ? fileOrEvent : fileOrEvent?.target?.files?.[0];
    if (!file) return;

    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const fd = new FormData();
      fd.append("file", file);

      const res = await axios.post("http://127.0.0.1:8000/api/documents/upload", fd, {
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "multipart/form-data" },
      });

      const extracted = res.data?.raw_text || res.data?.extracted_text || "";
      setRawText(extracted);
      localStorage.setItem("draft_raw_text", extracted);
      await fetchDocs();

      setSnack({ open: true, message: "File uploaded and text extracted", severity: "success" });
    } catch (err) {
      console.error("upload error", err);
      setSnack({
        open: true,
        message: err?.response?.data?.detail || "Upload/extract failed",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePasteChange = (e) => {
    setRawText(e.target.value);
    localStorage.setItem("draft_raw_text", e.target.value);
  };

  const handleGenerate = async () => {
    if (!rawText || rawText.trim().length === 0) {
      setSnack({ open: true, message: "Please upload or paste text first", severity: "error" });
      return;
    }
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const cfgRes = await axios.get("http://127.0.0.1:8000/api/config", {
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => null);
      const config = cfgRes?.data || null;

      const payload = {
        raw_text: rawText,
        created_by: config?.created_by || config?.document_type || "",
        pages: config?.pages || [],
        sections: config?.sections || [],
      };

      const res = await axios.post("http://127.0.0.1:8000/api/documents/generate", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const id = res.data?.id || res.data?.document?.id;
      if (!id) throw new Error("No document id returned");

      localStorage.removeItem("draft_raw_text");
      navigate(`/viewer/${id}`);
    } catch (err) {
      console.error("generate error", err);
      setSnack({
        open: true,
        message: err?.response?.data?.detail || "Failed to generate document",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setRawText("");
    localStorage.removeItem("draft_raw_text");
  };

  const handleLoadDoc = (doc) => {
    setRawText(doc.raw_text || "");
    localStorage.setItem("draft_raw_text", doc.raw_text || "");
  };

  const handleNewDoc = () => {
    setRawText("");
    localStorage.removeItem("draft_raw_text");
  };

  const handleMenuOpen = (event, doc) => {
    setMenuAnchor(event.currentTarget);
    setSelectedDoc(doc);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedDoc(null);
  };

  const handleDeleteDoc = async () => {
    if (!selectedDoc) return;
    try {
      const token = localStorage.getItem("token");
      await axios.delete(`http://127.0.0.1:8000/api/documents/${selectedDoc.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      await fetchDocs();
      setSnack({ open: true, message: "Document deleted", severity: "success" });
    } catch (err) {
      console.error("delete error", err);
      setSnack({ open: true, message: "Failed to delete document", severity: "error" });
    } finally {
      handleMenuClose();
    }
  };

  const hasContent = rawText.trim().length > 0;

  return (
    <>
      <Navbar />
      <div className="uploadpage-root">
        <div className="uploadpage-layout">
          {/* Sidebar */}
          <aside className="sidebar">
            <button className="new-doc-btn" onClick={handleNewDoc}>
              <AddIcon fontSize="small" style={{ marginRight: "6px" }} />
              New Document
            </button>

            <div className="search-wrapper">
              <SearchIcon className="search-icon" />
              <input type="text" className="search-box" placeholder="Search documents..." />
            </div>

            <div className="doc-section">
              <h4>Recent</h4>
              {documents.map((doc) => (
                <div key={doc.id} className="doc-item">
                  <span className="doc-content" onClick={() => handleLoadDoc(doc)}>
                    <span className="doc-icon">📄</span>
                    <span className="doc-name">{doc.filename || "Untitled"}</span>
                  </span>
                  <IconButton
                    size="small"
                    onClick={(e) => handleMenuOpen(e, doc)}
                    className="doc-menu-btn"
                  >
                    <MoreVertIcon fontSize="small" />
                  </IconButton>
                </div>
              ))}
            </div>
          </aside>

          {/* Main viewer */}
          <main className="viewer-container">
            {!hasContent && (
              <div className="placeholder-overlay">
                <UploadFileIcon className="placeholder-icon" />
                <h2 className="placeholder-title">Start Writing</h2>
                <p className="placeholder-subtext">
                  Type here or upload a file to get started
                </p>
              </div>
            )}
            <textarea
              ref={textareaRef}
              className="viewer-textarea"
              value={rawText}
              onChange={handlePasteChange}
              placeholder=""
            />
            <div className="button-row">
              {!hasContent ? (
                <label className="btn upload-btn">
                  {loading ? "Uploading..." : "Upload"}
                  <input
                    type="file"
                    style={{ display: "none" }}
                    onChange={(e) => handleFileUpload(e.target.files?.[0])}
                  />
                </label>
              ) : (
                <>
                  <button
                    className={`btn generate-btn ${loading ? "loading" : ""}`}
                    onClick={handleGenerate}
                    disabled={loading}
                  >
                    {loading ? <CircularProgress size={18} color="inherit" /> : "Generate"}
                  </button>
                  <button className="btn clear-btn" onClick={handleClear} disabled={loading}>
                    Clear
                  </button>
                </>
              )}
            </div>
          </main>
        </div>

        {/* Delete Menu */}
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
          classes={{ paper: "custom-menu" }}
        >
          <MenuItem className="delete-menu-item" onClick={handleDeleteDoc}>
            Delete
          </MenuItem>
        </Menu>

        <ErrorSnackbar
          open={snack.open}
          onClose={() => setSnack({ ...snack, open: false })}
          severity={snack.severity}
          message={snack.message}
        />
      </div>
    </>
  );
}
