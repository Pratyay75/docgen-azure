// src/pages/AdminPage.js
import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  MenuItem,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  IconButton,
  Paper,
} from "@mui/material";
import { Delete, Edit, Save, Cancel } from "@mui/icons-material";
import axios from "axios";
import Navbar from "../components/Navbar";
import ErrorSnackbar from "../components/ErrorSnackbar";
import "../styles/AdminPage.css";

function AdminPage() {
  const [tab, setTab] = useState("company");

  // --- Companies ---
  const [companies, setCompanies] = useState([]);
  const [editingCompanyId, setEditingCompanyId] = useState(null);
  const [newCompany, setNewCompany] = useState({
    name: "",
    email: "",
    address: "",
    contact_person_name: "",
    contact_person_phone: "",
  });

  // --- Users ---
  const [users, setUsers] = useState([]);
  const [editingUserId, setEditingUserId] = useState(null);
  const [newUser, setNewUser] = useState({
    name: "",
    email: "",
    password: "",
    company_id: "",
  });

  // Snackbar
  const [snack, setSnack] = useState({ open: false, message: "", severity: "error" });

  const token = localStorage.getItem("token");

  useEffect(() => {
    fetchCompanies();
    fetchUsers();
  }, []);

  // ======================
  // COMPANY FUNCTIONS
  // ======================
  const fetchCompanies = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/companies", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCompanies(res.data);
    } catch {
      setSnack({ open: true, message: "Failed to load companies", severity: "error" });
    }
  };

  const handleSaveCompany = async (company) => {
    try {
      await axios.post("http://127.0.0.1:8000/api/companies", company, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchCompanies();
      setNewCompany({ name: "", email: "", address: "", contact_person_name: "", contact_person_phone: "" });
      setSnack({ open: true, message: "Company saved successfully", severity: "success" });
    } catch {
      setSnack({ open: true, message: "Failed to save company", severity: "error" });
    }
  };

  const handleUpdateCompany = async (company) => {
    try {
      await axios.post("http://127.0.0.1:8000/api/companies", company, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchCompanies();
      setEditingCompanyId(null);
      setSnack({ open: true, message: "Company updated successfully", severity: "success" });
    } catch {
      setSnack({ open: true, message: "Failed to update company", severity: "error" });
    }
  };

  const handleDeleteCompany = async (id) => {
    try {
      await axios.delete(`http://127.0.0.1:8000/api/companies/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchCompanies();
      fetchUsers();
      setSnack({ open: true, message: "Company deleted", severity: "success" });
    } catch {
      setSnack({ open: true, message: "Failed to delete company", severity: "error" });
    }
  };

  // ======================
  // USER FUNCTIONS
  // ======================
  const fetchUsers = async () => {
    try {
      const res = await axios.get("http://127.0.0.1:8000/api/users", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUsers(res.data);
    } catch {
      setSnack({ open: true, message: "Failed to load users", severity: "error" });
    }
  };

  const handleSaveUser = async (user) => {
    try {
      await axios.post("http://127.0.0.1:8000/api/users/register", user, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchUsers();
      setNewUser({ name: "", email: "", password: "", company_id: "" });
      setSnack({ open: true, message: "User saved successfully", severity: "success" });
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to save user";
      setSnack({ open: true, message: msg, severity: "error" });
    }
  };

  const handleUpdateUser = async (user) => {
    try {
      await axios.put(`http://127.0.0.1:8000/api/users/${user.id}`, user, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchUsers();
      setEditingUserId(null);
      setSnack({ open: true, message: "User updated successfully", severity: "success" });
    } catch {
      setSnack({ open: true, message: "Failed to update user", severity: "error" });
    }
  };

  const handleDeleteUser = async (id) => {
    try {
      await axios.delete(`http://127.0.0.1:8000/api/users/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchUsers();
      setSnack({ open: true, message: "User deleted", severity: "success" });
    } catch {
      setSnack({ open: true, message: "Failed to delete user", severity: "error" });
    }
  };

  return (
    <>
      <Navbar />
      <Box className="admin-page-root">
        {/* Sidebar */}
        <div className="admin-sidebar">
          <div
            className={`sidebar-item ${tab === "company" ? "active" : ""}`}
            onClick={() => setTab("company")}
          >
            Company Master
          </div>
          <div
            className={`sidebar-item ${tab === "user" ? "active" : ""}`}
            onClick={() => setTab("user")}
          >
            User Master
          </div>
        </div>

        {/* Content */}
        <Box flex={1} p={4}>
          {tab === "company" && (
            <Paper className="table-container" elevation={3}>
              <Typography variant="h6" className="admin-title">Company Master</Typography>
              <Table className="admin-table">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Address</TableCell>
                    <TableCell>Contact Person</TableCell>
                    <TableCell>Phone</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {companies.map((c) => (
                    <TableRow key={c.id}>
                      {editingCompanyId === c.id ? (
                        <>
                          <TableCell><TextField size="small" value={c.name} onChange={(e) => (c.name = e.target.value)} /></TableCell>
                          <TableCell><TextField size="small" value={c.email || ""} onChange={(e) => (c.email = e.target.value)} /></TableCell>
                          <TableCell><TextField size="small" value={c.address || ""} onChange={(e) => (c.address = e.target.value)} /></TableCell>
                          <TableCell><TextField size="small" value={c.contact_person_name || ""} onChange={(e) => (c.contact_person_name = e.target.value)} /></TableCell>
                          <TableCell><TextField size="small" value={c.contact_person_phone || ""} onChange={(e) => (c.contact_person_phone = e.target.value)} /></TableCell>
                          <TableCell>
                            <Box className="action-buttons">
                              <IconButton onClick={() => handleUpdateCompany(c)}><Save /></IconButton>
                              <IconButton onClick={() => setEditingCompanyId(null)}><Cancel /></IconButton>
                            </Box>
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell>{c.name}</TableCell>
                          <TableCell>{c.email}</TableCell>
                          <TableCell>{c.address}</TableCell>
                          <TableCell>{c.contact_person_name}</TableCell>
                          <TableCell>{c.contact_person_phone}</TableCell>
                          <TableCell>
                            <Box className="action-buttons">
                              <IconButton onClick={() => setEditingCompanyId(c.id)}><Edit /></IconButton>
                              <IconButton onClick={() => handleDeleteCompany(c.id)}><Delete /></IconButton>
                            </Box>
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                  <TableRow className="add-row">
                    <TableCell><TextField size="small" placeholder="Name" value={newCompany.name} onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" placeholder="Email" value={newCompany.email} onChange={(e) => setNewCompany({ ...newCompany, email: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" placeholder="Address" value={newCompany.address} onChange={(e) => setNewCompany({ ...newCompany, address: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" placeholder="Contact Name" value={newCompany.contact_person_name} onChange={(e) => setNewCompany({ ...newCompany, contact_person_name: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" placeholder="Phone" value={newCompany.contact_person_phone} onChange={(e) => setNewCompany({ ...newCompany, contact_person_phone: e.target.value })} /></TableCell>
                    <TableCell><Button variant="contained" onClick={() => handleSaveCompany(newCompany)}>Add</Button></TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </Paper>
          )}

          {tab === "user" && (
            <Paper className="table-container" elevation={3}>
              <Typography variant="h6" className="admin-title">User Master</Typography>
              <Table className="admin-table">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Company</TableCell>
                    <TableCell>Password</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((u) => (
                    <TableRow key={u.id}>
                      {editingUserId === u.id ? (
                        <>
                          <TableCell><TextField size="small" value={u.name || ""} onChange={(e) => (u.name = e.target.value)} /></TableCell>
                          <TableCell><TextField size="small" value={u.email} onChange={(e) => (u.email = e.target.value)} /></TableCell>
                          <TableCell>
                            <TextField size="small" select value={u.company_id || ""} onChange={(e) => (u.company_id = e.target.value)}>
                              {companies.map((c) => (
                                <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                              ))}
                            </TextField>
                          </TableCell>
                          <TableCell><TextField size="small" type="password" value={u.password || ""} onChange={(e) => (u.password = e.target.value)} /></TableCell>
                          <TableCell>
                            <Box className="action-buttons">
                              <IconButton onClick={() => handleUpdateUser(u)}><Save /></IconButton>
                              <IconButton onClick={() => setEditingUserId(null)}><Cancel /></IconButton>
                            </Box>
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell>{u.name}</TableCell>
                          <TableCell>{u.email}</TableCell>
                          <TableCell>{u.company_name}</TableCell>
                          <TableCell>******</TableCell>
                          <TableCell>
                            <Box className="action-buttons">
                              <IconButton onClick={() => setEditingUserId(u.id)}><Edit /></IconButton>
                              <IconButton onClick={() => handleDeleteUser(u.id)}><Delete /></IconButton>
                            </Box>
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                  <TableRow className="add-row">
                    <TableCell><TextField size="small" placeholder="Name" value={newUser.name} onChange={(e) => setNewUser({ ...newUser, name: e.target.value })} /></TableCell>
                    <TableCell><TextField size="small" placeholder="Email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} /></TableCell>
                    <TableCell>
                      <TextField size="small" select value={newUser.company_id} onChange={(e) => setNewUser({ ...newUser, company_id: e.target.value })}>
                        {companies.map((c) => (
                          <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
                        ))}
                      </TextField>
                    </TableCell>
                    <TableCell><TextField size="small" placeholder="Password" type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} /></TableCell>
                    <TableCell><Button variant="contained" onClick={() => handleSaveUser(newUser)}>Add</Button></TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </Paper>
          )}
        </Box>
      </Box>

      <ErrorSnackbar
        open={snack.open}
        onClose={() => setSnack({ ...snack, open: false })}
        severity={snack.severity}
        message={snack.message}
      />
    </>
  );
}

export default AdminPage;
