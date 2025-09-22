// src/pages/ConfigurePage.js
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import ErrorSnackbar from "../components/ErrorSnackbar";
import api from "../services/api";
import "../styles/ConfigurePage.css";

export default function ConfigurePage() {
  const navigate = useNavigate();

  const [documentName, setDocumentName] = useState("");
  const [createdBy, setCreatedBy] = useState("");
  const [pages, setPages] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [snack, setSnack] = useState({
    open: false,
    message: "",
    severity: "error",
  });

  const makeId = (prefix = "id") =>
    `${prefix}_${Date.now()}_${Math.floor(Math.random() * 10000)}`;

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await api.get("/api/config", {
   headers: { Authorization: `Bearer ${token}` },
 });

        if (res.data) {
          setDocumentName(res.data.document_name || "");
          setCreatedBy(res.data.created_by || res.data.document_type || "");

          const pagesData = (res.data.pages || []).map((p) => ({
            __localId: p.__localId || makeId("pg"),
            ...p,
          }));
          const sectionsData = (res.data.sections || []).map((s) => ({
            __localId: s.__localId || makeId("sec"),
            ...s,
          }));
          setPages(pagesData);
          setSections(sectionsData);
        } else {
          setDocumentName("");
          setCreatedBy("");
          setPages([]);
          setSections([]);
        }
      } catch (err) {
        if (err?.response?.status !== 404) {
          console.error("Failed to load config", err);
          setSnack({
            open: true,
            message:
              err?.response?.data?.detail || "Failed to load configuration",
            severity: "error",
          });
        }
      }
    };
    fetchConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---------------------- Pages ---------------------- */
  const addPage = () =>
    setPages((p) => [
      ...p,
      {
        __localId: makeId("pg"),
        name: "",
        sequence: p.length + 1,
        sample_output: "",
        generated_prompt: "",
        editable_prompt: "",
        manually_edited: false,
      },
    ]);

  const removePage = (localId) =>
    setPages((p) => p.filter((x) => x.__localId !== localId));

  const updatePage = (localId, key, val) => {
    setPages((p) => {
      const copy = p.map((it) =>
        it.__localId === localId ? { ...it, [key]: val } : it
      );
      if (key === "editable_prompt") {
        return copy.map((it) =>
          it.__localId === localId ? { ...it, manually_edited: true } : it
        );
      }
      return copy;
    });
  };

  /* ---------------------- Sections ---------------------- */
  const addSection = () =>
    setSections((s) => [
      ...s,
      {
        __localId: makeId("sec"),
        name: "",
        sequence: s.length + 1,
        type: "list",
        style_tone: "Professional",
        formatting_rules: [],
        length_word_count: "",
        sample_output: "",
        generated_prompt: "",
        editable_prompt: "",
        manually_edited: false,
      },
    ]);

  const removeSection = (localId) =>
    setSections((s) => s.filter((x) => x.__localId !== localId));

  const updateSection = (localId, key, val) => {
    setSections((s) => {
      const copy = s.map((it) =>
        it.__localId === localId ? { ...it, [key]: val } : it
      );
      if (key === "editable_prompt") {
        return copy.map((it) =>
          it.__localId === localId ? { ...it, manually_edited: true } : it
        );
      }
      return copy;
    });
  };

  /* ---------------------- Save ---------------------- */
  const handleSave = async () => {
    if (!documentName.trim()) {
      setSnack({
        open: true,
        message: "Document name is required",
        severity: "error",
      });
      return;
    }
    if (
      sections.some((s) => !s.name.trim()) ||
      pages.some((p) => !p.name.trim())
    ) {
      setSnack({
        open: true,
        message: "Each page and section needs a name",
        severity: "error",
      });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem("token");

      const payload = {
        document_name: documentName,
        created_by: createdBy,
        pages: pages.map((p, i) => ({
          name: p.name,
          sequence: Number(p.sequence) || i + 1,
          sample_output: p.sample_output,
          editable_prompt: p.editable_prompt || "",
          manually_edited: !!p.manually_edited,
        })),
        sections: sections.map((s, i) => ({
          name: s.name,
          sequence: Number(s.sequence) || i + 1,
          type: s.type,
          style_tone: s.style_tone,
          formatting_rules: Array.isArray(s.formatting_rules)
            ? s.formatting_rules
            : (s.formatting_rules || "")
                .split(",")
                .map((r) => r.trim())
                .filter(Boolean),
          length_word_count: s.length_word_count,
          sample_output: s.sample_output,
          editable_prompt: s.editable_prompt || "",
          manually_edited: !!s.manually_edited,
        })),
      };

      const res = await api.post("/api/config", payload, {
   headers: { Authorization: `Bearer ${token}` },
 });

      if (res.data) {
        const pagesData = (res.data.pages || []).map((p) => ({
          __localId: p.__localId || makeId("pg"),
          ...p,
        }));
        const sectionsData = (res.data.sections || []).map((s) => ({
          __localId: s.__localId || makeId("sec"),
          ...s,
        }));
        setPages(pagesData);
        setSections(sectionsData);
      }

      setSnack({
        open: true,
        message: "Configuration saved successfully",
        severity: "success",
      });
    } catch (err) {
      console.error("save config error", err);
      setSnack({
        open: true,
        message:
          err?.response?.data?.detail || "Failed to save configuration",
        severity: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  /* ---------------------- Navigation ---------------------- */
  const handleBack = () => {
    navigate("/upload");
  };

  const autoResize = (e) => {
    e.target.style.height = "auto";
    e.target.style.height = e.target.scrollHeight + "px";
  };

  /* ---------------------- Render ---------------------- */
  return (
    <>
      <Navbar />
      <div className="configure-wrapper">
        <div className="cfg-page-root">
          <div className="cfg-card">
            {/* --- Document Configuration --- */}
            <h2 className="cfg-heading">Configure Document</h2>
            <div className="cfg-inner-card">
              <div className="cfg-label-row cfg-label-doc">
                <div className="lbl">Document Name</div>
                <div className="lbl">Created By (Author Role)</div>
              </div>
              <div className="cfg-section-row cfg-row-doc">
                <input
                  className="cfg-input"
                  type="text"
                  value={documentName}
                  onChange={(e) => setDocumentName(e.target.value)}
                />
                <input
                  className="cfg-input"
                  type="text"
                  placeholder="Enter author role (e.g. Business Analyst)"
                  value={createdBy}
                  onChange={(e) => setCreatedBy(e.target.value)}
                />
              </div>
            </div>

            {/* --- Page Configuration --- */}
            <h2 className="cfg-heading">Configure Pages</h2>
            <div className="cfg-inner-card">
              {pages.length === 0 && (
                <div className="empty-state">
                  No pages yet. Click <b>+ Add Page</b> to get started.
                </div>
              )}
              <div className="cfg-label-row cfg-label-pages">
                <div className="lbl">Page Name</div>
                <div className="lbl">Sequence</div>
                <div className="lbl">Sample Output</div>
                <div className="lbl">Prompt (Editable)</div>
                <div className="lbl"></div>
              </div>

              {pages.map((pg) => (
                <div
                  key={pg.__localId}
                  className="cfg-section-row cfg-row-pages card-row"
                >
                  <input
                    className="cfg-input"
                    type="text"
                    value={pg.name}
                    onChange={(e) =>
                      updatePage(pg.__localId, "name", e.target.value)
                    }
                  />
                  <input
                    className="cfg-input seq"
                    type="number"
                    min="1"
                    value={pg.sequence}
                    onChange={(e) =>
                      updatePage(pg.__localId, "sequence", e.target.value)
                    }
                  />
                  <textarea
                    className="cfg-input sample"
                    placeholder="Optional sample output"
                    value={pg.sample_output || ""}
                    onChange={(e) =>
                      updatePage(pg.__localId, "sample_output", e.target.value)
                    }
                    rows={3}
                    onInput={autoResize}
                  />
                  <textarea
                    className="cfg-input prompt"
                    value={pg.editable_prompt || pg.generated_prompt || ""}
                    onChange={(e) =>
                      updatePage(pg.__localId, "editable_prompt", e.target.value)
                    }
                    rows={4}
                    onInput={autoResize}
                  />
                  <button
                    className="cfg-delete"
                    onClick={() => removePage(pg.__localId)}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div className="cfg-add-row">
                <button className="cfg-add cfg-add-primary" onClick={addPage}>
                  + Add Page
                </button>
              </div>
            </div>

            {/* --- Section Configuration --- */}
            <h2 className="cfg-heading">Configure Sections</h2>
            <div className="cfg-inner-card">
              {sections.length === 0 && (
                <div className="empty-state">
                  No sections yet. Click <b>+ Add Section</b> to get started.
                </div>
              )}
              <div className="cfg-label-row cfg-label-sections">
                <div className="lbl">Section Name</div>
                <div className="lbl">Sequence</div>
                <div className="lbl">Type</div>
                <div className="lbl">Style & Tone</div>
                <div className="lbl">Formatting Rules</div>
                <div className="lbl">Length / Word Count</div>
                <div className="lbl">Sample Output</div>
                <div className="lbl">Prompt (Editable)</div>
                <div className="lbl"></div>
              </div>

              {sections.map((sec) => (
                <div
                  key={sec.__localId}
                  className="cfg-section-row cfg-row-sections card-row"
                >
                  <input
                    className="cfg-input"
                    type="text"
                    value={sec.name}
                    onChange={(e) =>
                      updateSection(sec.__localId, "name", e.target.value)
                    }
                  />
                  <input
                    className="cfg-input seq"
                    type="number"
                    min="1"
                    value={sec.sequence}
                    onChange={(e) =>
                      updateSection(sec.__localId, "sequence", e.target.value)
                    }
                  />
                  <select
                    className="cfg-select type"
                    value={sec.type}
                    onChange={(e) =>
                      updateSection(sec.__localId, "type", e.target.value)
                    }
                  >
                    <option value="list">List</option>
                    <option value="text">Paragraph</option>
                    <option value="table">Table</option>
                  </select>
                  <select
                    className="cfg-select style"
                    value={sec.style_tone || "Professional"}
                    onChange={(e) =>
                      updateSection(sec.__localId, "style_tone", e.target.value)
                    }
                  >
                    <option value="Professional">Professional</option>
                    <option value="Casual">Casual</option>
                    <option value="Formal">Formal</option>
                    <option value="Friendly">Friendly</option>
                    <option value="Academic">Academic</option>
                  </select>
                  <input
                    className="cfg-input formatting"
                    type="text"
                    placeholder="Comma separated rules"
                    value={
                      Array.isArray(sec.formatting_rules)
                        ? sec.formatting_rules.join(", ")
                        : sec.formatting_rules
                    }
                    onChange={(e) =>
                      updateSection(
                        sec.__localId,
                        "formatting_rules",
                        e.target.value
                      )
                    }
                  />
                  <input
                    className="cfg-input length"
                    type="text"
                    placeholder="e.g. 200-300 words"
                    value={sec.length_word_count || ""}
                    onChange={(e) =>
                      updateSection(
                        sec.__localId,
                        "length_word_count",
                        e.target.value
                      )
                    }
                  />
                  <textarea
                    className="cfg-input sample"
                    placeholder="Optional sample output"
                    value={sec.sample_output || ""}
                    onChange={(e) =>
                      updateSection(
                        sec.__localId,
                        "sample_output",
                        e.target.value
                      )
                    }
                    rows={3}
                    onInput={autoResize}
                  />
                  <textarea
                    className="cfg-input prompt"
                    value={sec.editable_prompt || sec.generated_prompt || ""}
                    onChange={(e) =>
                      updateSection(
                        sec.__localId,
                        "editable_prompt",
                        e.target.value
                      )
                    }
                    rows={4}
                    onInput={autoResize}
                  />
                  <button
                    className="cfg-delete"
                    onClick={() => removeSection(sec.__localId)}
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div className="cfg-add-row">
                <button className="cfg-add cfg-add-primary" onClick={addSection}>
                  + Add Section
                </button>
              </div>
            </div>

            {/* --- Actions --- */}
            <div className="cfg-actions">
              <button className="back-only" onClick={handleBack}>
                Back
              </button>
              <button
                className={`generate-btn ${loading ? "loading" : ""}`}
                onClick={handleSave}
                disabled={loading}
              >
                {loading ? "Saving..." : "Save Configuration"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <ErrorSnackbar
        open={snack.open}
        onClose={() => setSnack({ ...snack, open: false })}
        severity={snack.severity}
        message={snack.message}
      />
    </>
  );
}
