import React, { useEffect, useState, useCallback } from 'react';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  X,
  AlertCircle,
  CheckCircle,
  Loader,
  Eye,
  EyeOff,
  Save,
  User,
  ShieldCheck,
  Mail,
} from 'lucide-react';
import api from '../api';

const PrincipalManagement = () => {
  const [principals, setPrincipals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchUdise, setSearchUdise] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [selectedSchool, setSelectedSchool] = useState(null);
  const [status, setStatus] = useState({ type: null, message: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [filter, setFilter] = useState('all'); // all, active, inactive

  const [formData, setFormData] = useState({
    full_name: '',
    username: '',
    school_pseudocode: '',
    password: '',
  });

  const [schoolData, setSchoolData] = useState({
    school_level: '',
    total_students: 0,
    total_tch: 0,
  });

  // Fetch all principals
  const fetchPrincipals = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/auth/users');
      const principalsOnly = response.data.filter(u => u.role === 'principal');
      setPrincipals(principalsOnly);
    } catch (err) {
      console.error('Fetch principals error:', err.response?.data || err.message);
      setStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to fetch principals. Please ensure you are logged in as admin.',
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrincipals();
  }, [fetchPrincipals]);

  // Handle search
  const handleSearch = async (e) => {
    const udise = e.target.value;
    setSearchUdise(udise);

    if (!udise.trim()) {
      fetchPrincipals();
      return;
    }

    try {
      const response = await api.get(`/auth/users/udise/${udise}`);
      setPrincipals([response.data]);
    } catch (err) {
      if (err.response?.status === 404) {
        setPrincipals([]);
        setStatus({
          type: 'warning',
          message: `No principal found with UDISE: ${udise}`,
        });
      }
    }
  };

  // Load school details for editing
  const handleEditSchool = async (principal) => {
    try {
      const response = await api.get(`/auth/schools/${principal.school_pseudocode}`);
      setSchoolData(response.data);
      setSelectedSchool(principal);
    } catch (err) {
      setStatus({
        type: 'error',
        message: 'Failed to load school details',
      });
    }
  };

  // Handle form changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSchoolChange = (e) => {
    const { name, value } = e.target;
    setSchoolData(prev => ({
      ...prev,
      [name]: name.includes('total') ? parseFloat(value) || 0 : value,
    }));
  };

  // Add new principal
  const handleAddPrincipal = async (e) => {
    e.preventDefault();

    if (!formData.full_name || !formData.username || !formData.school_pseudocode || !formData.password) {
      setStatus({
        type: 'error',
        message: 'All fields are required',
      });
      return;
    }

    try {
      await api.post('/auth/register', {
        full_name: formData.full_name,
        username: formData.username,
        school_pseudocode: formData.school_pseudocode,
        password: formData.password,
        role: 'principal',
      });

      setStatus({
        type: 'success',
        message: 'Principal added successfully',
      });

      setFormData({
        full_name: '',
        username: '',
        school_pseudocode: '',
        password: '',
      });
      setShowAddForm(false);

      setTimeout(() => {
        fetchPrincipals();
        setStatus({ type: null, message: '' });
      }, 2000);
    } catch (err) {
      setStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to add principal',
      });
    }
  };

  // Update school details
  const handleUpdateSchool = async (e) => {
    e.preventDefault();

    try {
      await api.put(`/auth/schools/${selectedSchool.school_pseudocode}`, schoolData);

      setStatus({
        type: 'success',
        message: 'School details updated successfully',
      });

      setTimeout(() => {
        setSelectedSchool(null);
        fetchPrincipals();
        setStatus({ type: null, message: '' });
      }, 2000);
    } catch (err) {
      setStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to update school',
      });
    }
  };

  // Delete principal
  const handleDeletePrincipal = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this principal account?')) return;

    try {
      await api.delete(`/auth/users/${userId}`);

      setStatus({
        type: 'success',
        message: 'Principal deleted successfully',
      });

      setTimeout(() => {
        fetchPrincipals();
        setStatus({ type: null, message: '' });
      }, 2000);
    } catch (err) {
      setStatus({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to delete principal',
      });
    }
  };

  // Filter principals
  const filteredPrincipals = principals.filter(p => {
    if (filter === 'active') return p.is_active;
    if (filter === 'inactive') return !p.is_active;
    return true;
  });

  return (
    <div className="animate-fade-in">
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginBottom: '0.25rem' }}>Principal Management</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
          Manage principal users and school details by UDISE ID
        </p>
      </header>

      {/* Status Messages */}
      {status.message && (
        <div
          className="glass-panel"
          style={{
            marginBottom: '1.5rem',
            padding: '1rem 1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            backgroundColor: status.type === 'error'
              ? 'rgba(251, 113, 133, 0.1)'
              : status.type === 'warning'
              ? 'rgba(251, 146, 60, 0.1)'
              : 'rgba(52, 211, 153, 0.1)',
            borderLeft: `4px solid ${
              status.type === 'error'
                ? '#fb7185'
                : status.type === 'warning'
                ? '#fb923c'
                : '#34d399'
            }`,
          }}
        >
          {status.type === 'error' ? (
            <AlertCircle size={20} color="#fb7185" />
          ) : (
            <CheckCircle size={20} color="#34d399" />
          )}
          <span>{status.message}</span>
        </div>
      )}

      {/* Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', flex: 1 }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <Search
              size={18}
              style={{
                position: 'absolute',
                left: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              placeholder="Search by UDISE ID..."
              value={searchUdise}
              onChange={handleSearch}
              style={{
                width: '100%',
                padding: '10px 12px 10px 40px',
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '0.95rem',
              }}
            />
          </div>
        </div>

        <button
          onClick={() => setShowAddForm(!showAddForm)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            backgroundColor: 'var(--accent-blue)',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 600,
            transition: 'all 200ms ease',
          }}
          onMouseEnter={(e) => (e.target.style.transform = 'translateY(-2px)')}
          onMouseLeave={(e) => (e.target.style.transform = 'translateY(0)')}
        >
          <Plus size={18} />
          Add Principal
        </button>
      </div>

      {/* Filter Buttons */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {['all', 'active', 'inactive'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '8px 16px',
              backgroundColor: filter === f ? 'var(--accent-blue)' : 'transparent',
              color: filter === f ? '#fff' : 'var(--text-secondary)',
              border: `1px solid ${filter === f ? 'var(--accent-blue)' : 'var(--border-light)'}`,
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'all 200ms ease',
              textTransform: 'capitalize',
              fontWeight: 500,
            }}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Add Principal Form */}
      {showAddForm && (
        <div className="glass-panel" style={{ marginBottom: '2rem', padding: '2rem' }}>
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.3rem' }}>Add New Principal</h2>

          <form onSubmit={handleAddPrincipal}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  placeholder="Enter full name"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                  }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  UDISE ID *
                </label>
                <input
                  type="text"
                  name="school_pseudocode"
                  value={formData.school_pseudocode}
                  onChange={handleChange}
                  placeholder="e.g., 1003076"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                  }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Username *
                </label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Enter username"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                  }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Password *
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Enter password"
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 12px',
                      paddingRight: '40px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      color: 'var(--text-muted)',
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                type="submit"
                style={{
                  padding: '10px 20px',
                  backgroundColor: 'var(--accent-blue)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Create Principal
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                style={{
                  padding: '10px 20px',
                  backgroundColor: 'transparent',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-light)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Principals List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <Loader size={32} style={{ animation: 'spin 1s linear infinite', margin: '0 auto' }} />
        </div>
      ) : filteredPrincipals.length === 0 ? (
        <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>No principals found</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {filteredPrincipals.map(principal => (
            <div key={principal.id} className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1.5rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <div
                      style={{
                        width: '40px',
                        height: '40px',
                        borderRadius: '8px',
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <User size={20} color="var(--accent-blue)" />
                    </div>
                    <div>
                      <h3 style={{ marginBottom: '0.25rem', fontWeight: 700 }}>{principal.full_name}</h3>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>@{principal.username}</p>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1rem' }}>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>UDISE ID</p>
                      <p style={{ fontWeight: 600 }}>{principal.school_pseudocode}</p>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Status</p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div
                          style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            backgroundColor: principal.is_active ? '#34d399' : '#64748b',
                          }}
                        />
                        <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                          {principal.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                    <div>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Joined</p>
                      <p style={{ fontWeight: 600 }}>
                        {principal.created_at ? new Date(principal.created_at).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <button
                    onClick={() => handleEditSchool(principal)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '8px 12px',
                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
                      color: 'var(--accent-blue)',
                      border: '1px solid var(--accent-blue)',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 500,
                      transition: 'all 200ms ease',
                    }}
                    onMouseEnter={(e) => (e.target.style.backgroundColor = 'rgba(59, 130, 246, 0.2)')}
                    onMouseLeave={(e) => (e.target.style.backgroundColor = 'rgba(59, 130, 246, 0.1)')}
                  >
                    <Edit2 size={14} />
                    Edit School
                  </button>

                  <button
                    onClick={() => handleDeletePrincipal(principal.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '8px 12px',
                      backgroundColor: 'rgba(251, 113, 133, 0.1)',
                      color: 'var(--danger)',
                      border: '1px solid var(--danger)',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.9rem',
                      fontWeight: 500,
                      transition: 'all 200ms ease',
                    }}
                    onMouseEnter={(e) => (e.target.style.backgroundColor = 'rgba(251, 113, 133, 0.2)')}
                    onMouseLeave={(e) => (e.target.style.backgroundColor = 'rgba(251, 113, 133, 0.1)')}
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* School Edit Modal */}
      {selectedSchool && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(4px)',
          }}
          onClick={() => setSelectedSchool(null)}
        >
          <div
            className="glass-panel"
            style={{
              maxWidth: '600px',
              width: '90%',
              maxHeight: '80vh',
              overflow: 'auto',
              padding: '2rem',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2>Edit School Details</h2>
              <button
                onClick={() => setSelectedSchool(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '0',
                }}
              >
                <X size={24} />
              </button>
            </div>

            <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px' }}>
              <p style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                <strong>Principal:</strong> {selectedSchool.full_name}
              </p>
              <p style={{ fontSize: '0.9rem' }}>
                <strong>UDISE:</strong> {selectedSchool.school_pseudocode}
              </p>
            </div>

            <form onSubmit={handleUpdateSchool}>
              <div style={{ display: 'grid', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>School Level</label>
                  <input
                    type="text"
                    name="school_level"
                    value={schoolData.school_level || ''}
                    onChange={handleSchoolChange}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Total Students</label>
                  <input
                    type="number"
                    name="total_students"
                    value={schoolData.total_students || 0}
                    onChange={handleSchoolChange}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Total Teachers</label>
                  <input
                    type="number"
                    name="total_tch"
                    value={schoolData.total_tch || 0}
                    onChange={handleSchoolChange}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Total Classrooms</label>
                  <input
                    type="number"
                    name="classrooms_total"
                    value={schoolData.classrooms_total || 0}
                    onChange={handleSchoolChange}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid var(--border-light)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="submit"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    flex: 1,
                    padding: '12px',
                    backgroundColor: 'var(--accent-blue)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  <Save size={16} />
                  Save Changes
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedSchool(null)}
                  style={{
                    flex: 1,
                    padding: '12px',
                    backgroundColor: 'transparent',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrincipalManagement;
