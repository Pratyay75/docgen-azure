// src/pages/ViewerPage.js
import React, { useState, useEffect, useRef } from "react";
import {
  Paper,
  Typography,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  CircularProgress,
  Toolbar,
  Select,
  MenuItem,
  InputBase,
  Menu,
} from "@mui/material";
import { useParams } from "react-router-dom";

// Material Icons
import RefreshIcon from "@mui/icons-material/Refresh";
import SaveIcon from "@mui/icons-material/Save";
import SearchIcon from "@mui/icons-material/Search";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import FormatBoldIcon from "@mui/icons-material/FormatBold";
import FormatItalicIcon from "@mui/icons-material/FormatItalic";
import FormatUnderlinedIcon from "@mui/icons-material/FormatUnderlined";
import FormatColorFillIcon from "@mui/icons-material/FormatColorFill";
import FormatColorTextIcon from "@mui/icons-material/FormatColorText";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";

import Navbar from "../components/Navbar";
import ErrorSnackbar from "../components/ErrorSnackbar";
import api from "../services/api";
import "../styles/ViewerPage.css";

function ViewerPage() {
  const { id } = useParams();

  // ---------------------------
  // State
  // ---------------------------
  const [documentData, setDocumentData] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);

  // For regeneration
  const [openDialog, setOpenDialog] = useState(false);
  const [currentItem, setCurrentItem] = useState(null); // page or section
  const [itemPrompt, setItemPrompt] = useState("");

  // Preview modal
  const [openPreview, setOpenPreview] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");

  // Download menu
  const [anchorElDownload, setAnchorElDownload] = useState(null);

  // Snackbar
  const [snack, setSnack] = useState({
    open: false,
    message: "",
    severity: "error",
  });

  // Editor references
  const viewerScrollRef = useRef(null);
  const pageContentRefs = useRef({});
  const localEditedRef = useRef({});

  // Styling toolbar state
  const [fontFamily, setFontFamily] = useState("Calibri");
  const [fontSize, setFontSize] = useState(16);

  // ---------------------------
  // Fetch document on mount
  // ---------------------------
  useEffect(() => {
    fetchDocument();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const fetchDocument = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/documents/${id}`);
      const doc = res.data?.document || res.data;
      const normalizedDoc = normalizeDocument(doc);
      setDocumentData(normalizedDoc);
      resetRefs(normalizedDoc);
      setTimeout(() => populateEditorsFromDocument(normalizedDoc), 50);
    } catch (err) {
      console.error("fetchDocument error:", err);
      setSnack({
        open: true,
        message: err?.response?.data?.detail || "Failed to load document",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------
  // Helpers
  // ---------------------------
  const resetRefs = (doc) => {
    localEditedRef.current = {};
    pageContentRefs.current = {};
    (doc?.pages || []).forEach((_, i) => {
      localEditedRef.current[`page${i}`] = false;
    });
    (doc?.sections || []).forEach((_, i) => {
      localEditedRef.current[`section${i}`] = false;
    });
  };

  const normalizeDocument = (doc) => {
    if (!doc) return { pages: [], sections: [] };
    const copy = { ...doc };
    copy.pages = (doc.pages || []).map((p) => normalizeShape(p, "page"));
    copy.sections = (doc.sections || []).map((s) =>
      normalizeShape(s, "section")
    );
    return copy;
  };

  const normalizeShape = (obj, mode) => {
    if (!obj) return obj;
    const o = { ...obj };
    if (!o.type && mode === "section") o.type = "text";
    if (!o.layout && mode === "page") o.layout = "text";
    return o;
  };

  // ---------------------------
  // Render editors from data
  // ---------------------------
  const populateEditorsFromDocument = (doc) => {
    if (!doc) return;

    (doc.pages || []).forEach((pg, idx) => {
      const el = pageContentRefs.current[`page${idx}`];
      if (!el || localEditedRef.current[`page${idx}`]) return;
      el.innerHTML = pg.content || "";
    });

    (doc.sections || []).forEach((sec, idx) => {
      const el = pageContentRefs.current[`section${idx}`];
      if (!el || localEditedRef.current[`section${idx}`]) return;
      el.innerHTML = sec.content || "";
    });
  };

  // ---------------------------
  // Save page/section
  // ---------------------------
  const handleSave = async (mode, index) => {
    if (!documentData) return;
    const item =
      mode === "page" ? documentData.pages[index] : documentData.sections[index];
    const refKey = `${mode}${index}`;
    const el = pageContentRefs.current[refKey];
    if (!el) return;

    const html = el.innerHTML;

    try {
      const res = await api.post(
        `/api/documents/${id}/save-${mode}`,
        mode === "page"
          ? { page_name: item.name, content: html }
          : { section_name: item.name, content: html }
      );

      const updated = normalizeDocument(res.data.document);
      setDocumentData(updated);
      setSnack({
        open: true,
        message: `${mode} "${item.name}" saved`,
        severity: "success",
      });
      localEditedRef.current[refKey] = true;
      setTimeout(() => populateEditorsFromDocument(updated), 50);
    } catch (err) {
      console.error("save error", err);
      setSnack({
        open: true,
        message: `Failed to save ${mode}`,
        severity: "error",
      });
    }
  };

  // ---------------------------
  // Regeneration
  // ---------------------------
  const handleRegenerate = async () => {
    if (!currentItem) return;
    const mode = currentItem._mode;
    setLoading(true);
    try {
      const res = await api.post(
        `/api/documents/${id}/regenerate-${mode}`,
        mode === "page"
          ? {
              page_name: currentItem.name,
              user_instruction: itemPrompt,
              raw_text: documentData?.raw_text || "",
            }
          : {
              section_name: currentItem.name,
              user_instruction: itemPrompt,
              raw_text: documentData?.raw_text || "",
            }
      );
      const updated = normalizeDocument(res.data.document);
      setDocumentData(updated);
      setSnack({
        open: true,
        message: `${mode} regenerated successfully`,
        severity: "success",
      });
      resetRefs(updated);
      setTimeout(() => populateEditorsFromDocument(updated), 50);
      handleCloseDialog();
    } catch (err) {
      console.error("regenerate error", err);
      setSnack({
        open: true,
        message: `Failed to regenerate ${mode}`,
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateDocument = async () => {
    setLoading(true);
    try {
      const res = await api.post(`/api/documents/${id}/regenerate-document`, {
        raw_text: documentData?.raw_text || "",
      });
      const updated = normalizeDocument(res.data.document);
      setDocumentData(updated);
      setSnack({
        open: true,
        message: "Document regenerated",
        severity: "success",
      });
      resetRefs(updated);
      setTimeout(() => populateEditorsFromDocument(updated), 50);
    } catch (err) {
      console.error("regen doc error", err);
      setSnack({
        open: true,
        message: "Failed to regenerate document",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (item, mode) => {
    setCurrentItem({ ...item, _mode: mode });
    setItemPrompt("");
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setCurrentItem(null);
    setItemPrompt("");
  };

  // ---------------------------
  // Search with highlight
  // ---------------------------
  const handleSearch = () => {
    if (!search || !documentData) return;
    const lower = search.toLowerCase();

    const allItems = [
      ...(documentData.pages || []).map((p) => ({ ...p, _mode: "page" })),
      ...(documentData.sections || []).map((s) => ({ ...s, _mode: "section" })),
    ];

    const idx = allItems.findIndex((i) =>
      JSON.stringify(i.content).toLowerCase().includes(lower)
    );

    if (idx >= 0) {
      const refKey =
        idx < (documentData.pages || []).length
          ? `page${idx}`
          : `section${idx - (documentData.pages || []).length}`;
      const el = pageContentRefs.current[refKey];
      if (el && viewerScrollRef.current) {
        viewerScrollRef.current.scrollTo({
          top: el.offsetTop - 12,
          behavior: "smooth",
        });
        const regex = new RegExp(`(${search})`, "gi");
        el.querySelectorAll("mark").forEach((m) => {
          m.outerHTML = m.innerText;
        });
        el.innerHTML = el.innerHTML.replace(regex, "<mark>$1</mark>");
      }
    } else {
      setSnack({ open: true, message: "Not found", severity: "info" });
    }
  };

  // ---------------------------
  // Preview + Download
  // ---------------------------
  const handleOpenPreview = async () => {
    setLoading(true);
    try {
      const pageHtml = (documentData?.pages || []).map((_, idx) => {
        const el = pageContentRefs.current[`page${idx}`];
        return el ? el.innerHTML : "";
      });

      const sectionHtml = (documentData?.sections || []).map((_, idx) => {
        const el = pageContentRefs.current[`section${idx}`];
        return el ? el.innerHTML : "";
      });

      const joined = [...pageHtml, ...sectionHtml].join("");

      const styledHtml = `
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: ${fontFamily}, sans-serif; font-size: ${fontSize}px; line-height: 1.5; margin: 40px; }
    h1, h2, h3, h4, h5, h6 { font-weight: bold; margin-top: 20px; margin-bottom: 10px; }
    p { margin: 10px 0; }
    ul, ol { margin: 10px 20px; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; }
    th, td { border: 1px solid #333; padding: 6px; text-align: left; }
  </style>
</head>
<body>
  ${joined}
</body>
</html>
`;

      const blob = new Blob([styledHtml], { type: "text/html" });

      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
      setOpenPreview(true);
    } catch (err) {
      console.error("preview error", err);
      setSnack({
        open: true,
        message: "Preview failed",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClosePreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
    setOpenPreview(false);
  };

  const handleOpenDownloadMenu = (e) => setAnchorElDownload(e.currentTarget);
  const handleCloseDownloadMenu = () => setAnchorElDownload(null);

  const handleDownload = async () => {
    setLoading(true);
    handleCloseDownloadMenu();
    try {
      const pageHtml = (documentData?.pages || []).map((_, idx) => {
        const el = pageContentRefs.current[`page${idx}`];
        return el ? el.innerHTML : "";
      });

      const sectionHtml = (documentData?.sections || []).map((_, idx) => {
        const el = pageContentRefs.current[`section${idx}`];
        return el ? el.innerHTML : "";
      });

      const joined = [...pageHtml, ...sectionHtml].join("");

      const styledHtml = `
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    body { font-family: ${fontFamily}, sans-serif; font-size: ${fontSize}px; line-height: 1.5; margin: 40px; }
    h1, h2, h3, h4, h5, h6 { font-weight: bold; margin-top: 20px; margin-bottom: 10px; }
    p { margin: 10px 0; }
    ul, ol { margin: 10px 20px; }
    table { border-collapse: collapse; width: 100%; margin: 15px 0; }
    th, td { border: 1px solid #333; padding: 6px; text-align: left; }
  </style>
</head>
<body>
  ${joined}
</body>
</html>
`;

      const payload = {
        title: documentData?.title || `document_${id}`,
        htmlContent: styledHtml,
      };

      const res = await api.post(`/api/documents/${id}/export`, payload, {
        responseType: "blob",
      });

      let filename = `${payload.title}.docx`;
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      setSnack({
        open: true,
        message: `Downloaded ${filename}`,
        severity: "success",
      });
    } catch (err) {
      console.error("download error", err);
      setSnack({
        open: true,
        message: "Export failed",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------
  // Render editable content
  // ---------------------------
  const renderEditable = (item, mode, idx) => {
    const refKey = `${mode}${idx}`;
    return (
      <div
        className="page-content"
        contentEditable
        suppressContentEditableWarning
        ref={(el) => {
          if (!el) return;
          pageContentRefs.current[refKey] = el;
          if (
            !localEditedRef.current[refKey] &&
            (!el.innerHTML || el.innerHTML.trim() === "")
          ) {
            el.innerHTML = item.content || "";
          }
        }}
        onInput={() => {
          const node = pageContentRefs.current[refKey];
          if (!node) return;
          localEditedRef.current[refKey] = true;
          setDocumentData((prev) => {
            if (!prev) return prev;
            const copy = { ...prev };
            const html = node.innerHTML;
            if (mode === "page") {
              const arr = [...(copy.pages || [])];
              arr[idx] = { ...arr[idx], content: html };
              copy.pages = arr;
            } else {
              const arr = [...(copy.sections || [])];
              arr[idx] = { ...arr[idx], content: html };
              copy.sections = arr;
            }
            return copy;
          });
        }}
        style={{
          minHeight: 120,
          outline: "none",
          padding: "12px",
          borderRadius: "10px",
          border: "1px solid rgba(0,0,0,0.1)",
          background: "#fff",
          fontFamily,
          fontSize,
          transform: `scale(${zoom})`,
          transformOrigin: "top left",
        }}
      />
    );
  };

  // ---------------------------
  // Render main component
  // ---------------------------
  return (
    <>
      <Navbar />
      <div className="viewer-root cfg-page-root">
        {/* Fixed Toolbar */}
        <Toolbar className="viewer-toolbar cfg-toolbar fixed-toolbar">
          <div className="toolbar-left">
            <Select
              value={fontFamily}
              onChange={(e) => setFontFamily(e.target.value)}
              size="small"
            >
              <MenuItem value="Arial">Arial</MenuItem>
              <MenuItem value="Times New Roman">Times New Roman</MenuItem>
            </Select>

            <Select
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              size="small"
            >
              {[12, 14, 16, 18, 20, 24, 28].map((sz) => (
                <MenuItem key={sz} value={sz}>
                  {sz}
                </MenuItem>
              ))}
            </Select>
            <IconButton onClick={() => document.execCommand("bold")}>
              <FormatBoldIcon />
            </IconButton>
            <IconButton onClick={() => document.execCommand("italic")}>
              <FormatItalicIcon />
            </IconButton>
            <IconButton onClick={() => document.execCommand("underline")}>
              <FormatUnderlinedIcon />
            </IconButton>
            <IconButton
              onClick={() => document.execCommand("backColor", false, "yellow")}
            >
              <FormatColorFillIcon />
            </IconButton>
            <IconButton
              onClick={() => document.execCommand("foreColor", false, "red")}
            >
              <FormatColorTextIcon />
            </IconButton>
            <IconButton onClick={() => setZoom((z) => +(z + 0.1).toFixed(2))}>
              <ZoomInIcon />
            </IconButton>
            <IconButton onClick={() => setZoom((z) => +(z - 0.1).toFixed(2))}>
              <ZoomOutIcon />
            </IconButton>
          </div>
          <div className="toolbar-right">
            <div className="search-box">
              <SearchIcon />
              <InputBase
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearch();
                }}
              />
            </div>
            <Button
              variant="outlined"
              onClick={handleOpenPreview}
              disabled={loading}
            >
              Preview
            </Button>
            <Button
              variant="outlined"
              endIcon={<ArrowDropDownIcon />}
              onClick={handleOpenDownloadMenu}
            >
              Download
            </Button>
            <Menu
              anchorEl={anchorElDownload}
              open={Boolean(anchorElDownload)}
              onClose={handleCloseDownloadMenu}
            >
              <MenuItem onClick={() => handleDownload()}>
                Download as DOCX
              </MenuItem>
            </Menu>
          </div>
        </Toolbar>

        {/* Scrollable content */}
        <div className="viewer-scroll" ref={viewerScrollRef}>
          {loading ? (
            <div
              style={{
                padding: 24,
                display: "flex",
                justifyContent: "center",
              }}
            >
              <CircularProgress />
            </div>
          ) : (
            <>
              {(documentData?.pages || []).map((pg, idx) => (
                <Paper
                  key={`page-${idx}`}
                  className="viewer-page"
                  style={{ marginBottom: 18, padding: 12 }}
                >
                  <div className="page-header">
                    <Typography variant="h6" style={{ marginRight: 12 }}>
                      {pg.name}
                    </Typography>
                    <div>
                      <IconButton onClick={() => handleOpenDialog(pg, "page")}>
                        <RefreshIcon />
                      </IconButton>
                      <IconButton onClick={() => handleSave("page", idx)}>
                        <SaveIcon />
                      </IconButton>
                    </div>
                  </div>
                  {renderEditable(pg, "page", idx)}
                </Paper>
              ))}

              {(documentData?.sections || []).map((sec, idx) => (
                <Paper
                  key={`sec-${idx}`}
                  className="viewer-page"
                  style={{ marginBottom: 18, padding: 12 }}
                >
                  <div className="page-header">
                    <Typography variant="h6" style={{ marginRight: 12 }}>
                      {sec.name}
                    </Typography>
                    <div>
                      <IconButton
                        onClick={() => handleOpenDialog(sec, "section")}
                      >
                        <RefreshIcon />
                      </IconButton>
                      <IconButton onClick={() => handleSave("section", idx)}>
                        <SaveIcon />
                      </IconButton>
                    </div>
                  </div>
                  {renderEditable(sec, "section", idx)}
                </Paper>
              ))}
            </>
          )}
        </div>

        <div className="viewer-bottom" style={{ padding: 12 }}>
          <Button
            onClick={handleRegenerateDocument}
            variant="contained"
            color="primary"
          >
            Regenerate Entire Document
          </Button>
        </div>
      </div>

      {/* Regeneration Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>
          Regenerate {currentItem?._mode}: {currentItem?.name}
        </DialogTitle>
        <DialogContent>
          <TextField
            multiline
            fullWidth
            rows={4}
            value={itemPrompt}
            onChange={(e) => setItemPrompt(e.target.value)}
            placeholder="Add instruction for regeneration (optional)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleRegenerate}
            variant="contained"
            color="primary"
          >
            Regenerate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={openPreview}
        onClose={handleClosePreview}
        fullWidth
        maxWidth="lg"
      >
        <DialogTitle>Document Preview</DialogTitle>
        <DialogContent style={{ minHeight: 520 }}>
          {previewUrl ? (
            <iframe
              src={previewUrl}
              width="100%"
              height="640px"
              title="preview"
              style={{ border: "none" }}
            />
          ) : (
            <Typography>No preview available</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePreview}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <ErrorSnackbar
        open={snack.open}
        onClose={() => setSnack({ ...snack, open: false })}
        severity={snack.severity}
        message={snack.message}
      />
    </>
  );
}

export default ViewerPage;
