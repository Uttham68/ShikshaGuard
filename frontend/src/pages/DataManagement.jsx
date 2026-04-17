import React, { useEffect, useState, useCallback } from 'react';
import { 
    Upload, 
    Activity, 
    Database, 
    AlertTriangle, 
    CheckCircle, 
    RefreshCw,
    Download,
    BarChart3,
    Clock,
    FileText,
    Zap,
    TrendingUp,
    AlertCircle,
    Copy,
    Eye
} from 'lucide-react';
import api from '../api';

const DataManagement = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [uploadState, setUploadState] = useState({ uploading: false, error: null, success: false });
    const [trainingState, setTrainingState] = useState({ status: 'idle', progress: 0, logs: '', error: null });
    const [preview, setPreview] = useState(null);
    const [showPreview, setShowPreview] = useState(false);
    const [pollingId, setPollingId] = useState(null);

    // Fetch dataset statistics
    const fetchStats = useCallback(async () => {
        try {
            const response = await api.get('/data/stats');
            setStats(response.data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    // Poll training status
    useEffect(() => {
        if (trainingState.status !== 'running') return;

        const pollTrainingStatus = async () => {
            try {
                const response = await api.get('/data/training-status');
                setTrainingState(prev => ({
                    ...prev,
                    status: response.data.status,
                    progress: (response.data.progress || 0) * 100,
                    logs: response.data.logs || prev.logs,
                }));

                if (response.data.status === 'complete') {
                    setTimeout(() => fetchStats(), 1000); // Refresh stats after training completes
                } else if (response.data.status === 'failed') {
                    setTrainingState(prev => ({
                        ...prev,
                        error: response.data.error || 'Training failed',
                    }));
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        const interval = setInterval(pollTrainingStatus, 2000);
        return () => clearInterval(interval);
    }, [trainingState.status, fetchStats]);

    // Handle CSV upload
    const handleFileUpload = async (event) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setUploadState({ uploading: true, error: null, success: false });

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await api.post('/data/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setUploadState({ uploading: false, error: null, success: true });
            setTimeout(() => {
                setUploadState(prev => ({ ...prev, success: false }));
                fetchStats(); // Refresh stats
            }, 3000);
        } catch (err) {
            setUploadState({
                uploading: false,
                error: err.response?.data?.detail || 'Upload failed',
                success: false,
            });
        }
        event.target.value = ''; // Reset file input
    };

    // Trigger model retraining
    const handleRetrain = async () => {
        if (!window.confirm('Start full model retraining? This may take 5-10 minutes.')) return;

        setTrainingState({ status: 'running', progress: 0, logs: '', error: null });

        try {
            await api.post('/data/retrain');
        } catch (err) {
            setTrainingState(prev => ({
                ...prev,
                status: 'failed',
                error: err.response?.data?.detail || 'Failed to start training',
            }));
        }
    };

    // Fetch dataset preview
    const handleShowPreview = async () => {
        if (showPreview) {
            setShowPreview(false);
            return;
        }

        try {
            const response = await api.get('/data/preview');
            setPreview(response.data);
            setShowPreview(true);
        } catch (err) {
            console.error('Failed to fetch preview:', err);
        }
    };

    // Download template
    const handleDownloadTemplate = async () => {
        try {
            const response = await api.get('/data/template');
            const csv = response.data.csv || '';
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'dataset_template.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to download template:', err);
        }
    };

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Dataset & Model Management</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Upload training data, manage models, monitor training progress.</p>
            </header>

            {/* Statistics Grid */}
            {!loading && stats && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Total Records</span>
                            <Database size={16} color="var(--accent-blue)" />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{stats.total_rows || 0}</div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>rows in dataset</div>
                    </div>

                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Accept</span>
                            <CheckCircle size={16} color="var(--success)" />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{stats.class_distribution?.Accept || 0}</div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>approval class</div>
                    </div>

                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Flag</span>
                            <AlertTriangle size={16} color="var(--warning)" />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{stats.class_distribution?.Flag || 0}</div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>flag class</div>
                    </div>

                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Reject</span>
                            <AlertCircle size={16} color="var(--danger)" />
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{stats.class_distribution?.Reject || 0}</div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>rejection class</div>
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '2rem', marginBottom: '3rem' }}>
                {/* Upload Section */}
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                        <Upload size={20} color="var(--accent-cyan)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Upload Dataset</h2>
                    </div>

                    <div style={{
                        border: '2px dashed var(--border-light)',
                        borderRadius: '12px',
                        padding: '2rem',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                        marginBottom: '1.5rem',
                        background: 'rgba(255,255,255,0.02)',
                    }}>
                        <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            disabled={uploadState.uploading}
                            style={{ display: 'none' }}
                            id="csv-upload"
                        />
                        <label htmlFor="csv-upload" style={{ cursor: 'pointer', display: 'block' }}>
                            <Upload size={32} color="var(--accent-cyan)" style={{ marginBottom: '0.75rem', opacity: 0.7 }} />
                            <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                                {uploadState.uploading ? 'Uploading...' : 'Drag CSV here or click'}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                Accepts .csv files with school baseline data
                            </div>
                        </label>
                    </div>

                    {uploadState.success && (
                        <div style={{
                            background: 'rgba(34, 197, 94, 0.1)',
                            border: '1px solid rgba(34, 197, 94, 0.3)',
                            padding: '1rem',
                            borderRadius: '8px',
                            color: 'var(--success)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            marginBottom: '1rem',
                            fontSize: '0.9rem',
                        }}>
                            <CheckCircle size={18} />
                            Dataset uploaded and merged successfully!
                        </div>
                    )}

                    {uploadState.error && (
                        <div style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            padding: '1rem',
                            borderRadius: '8px',
                            color: 'var(--danger)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            marginBottom: '1rem',
                            fontSize: '0.9rem',
                        }}>
                            <AlertTriangle size={18} />
                            {uploadState.error}
                        </div>
                    )}

                    <button
                        onClick={handleDownloadTemplate}
                        style={{
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-light)',
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            width: '100%',
                            justifyContent: 'center',
                            fontSize: '0.9rem',
                            fontWeight: 600,
                            transition: 'all 0.2s ease',
                        }}
                        onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                        onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.05)'}
                    >
                        <Download size={16} />
                        Download CSV Template
                    </button>
                </div>

                {/* Training Section */}
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                        <Zap size={20} color="var(--accent-amber)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Model Training</h2>
                    </div>

                    {trainingState.status === 'idle' ? (
                        <>
                            <div style={{
                                background: 'rgba(59, 130, 246, 0.05)',
                                border: '1px solid rgba(59, 130, 246, 0.2)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                marginBottom: '1.5rem',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                                    <BarChart3 size={18} color="var(--accent-blue)" />
                                    <span style={{ fontWeight: 600 }}>Training Ready</span>
                                </div>
                                <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', margin: 0 }}>
                                    Retrain Random Forest validator, XGBoost forecaster, and Isolation Forest anomaly detector on latest dataset.
                                </p>
                            </div>

                            <button
                                onClick={handleRetrain}
                                style={{
                                    background: 'linear-gradient(135deg, var(--accent-amber), #f59e0b)',
                                    border: 'none',
                                    padding: '1rem 1.5rem',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    color: '#000',
                                    fontWeight: 700,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.75rem',
                                    width: '100%',
                                    fontSize: '1rem',
                                    transition: 'all 0.3s ease',
                                }}
                                onMouseEnter={(e) => e.target.style.transform = 'translateY(-2px)'}
                                onMouseLeave={(e) => e.target.style.transform = 'translateY(0)'}
                            >
                                <RefreshCw size={18} />
                                Start Full Retrain
                            </button>
                        </>
                    ) : trainingState.status === 'running' ? (
                        <>
                            <div style={{
                                background: 'rgba(34, 197, 94, 0.05)',
                                border: '1px solid rgba(34, 197, 94, 0.2)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                marginBottom: '1.5rem',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                    <Activity className="animate-spin" size={18} color="var(--success)" />
                                    <span style={{ fontWeight: 600 }}>Training in Progress</span>
                                </div>
                                <div style={{ marginBottom: '0.75rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
                                        <span>Progress</span>
                                        <span>{Math.round(trainingState.progress)}%</span>
                                    </div>
                                    <div style={{
                                        width: '100%',
                                        height: '8px',
                                        background: 'rgba(255,255,255,0.1)',
                                        borderRadius: '4px',
                                        overflow: 'hidden',
                                    }}>
                                        <div style={{
                                            height: '100%',
                                            background: 'linear-gradient(90deg, var(--success), var(--accent-cyan))',
                                            width: `${trainingState.progress}%`,
                                            transition: 'width 0.3s ease',
                                        }} />
                                    </div>
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    Estimated time: 5-10 minutes
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <button
                                    onClick={() => setShowPreview(!showPreview)}
                                    style={{
                                        flex: 1,
                                        background: 'rgba(255,255,255,0.05)',
                                        border: '1px solid var(--border-light)',
                                        padding: '0.75rem 1rem',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        fontWeight: 600,
                                        transition: 'all 0.2s ease',
                                    }}
                                    onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.1)'}
                                    onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.05)'}
                                >
                                    <Eye size={16} style={{ marginRight: '0.5rem' }} />
                                    Training Logs
                                </button>
                            </div>
                        </>
                    ) : trainingState.status === 'complete' ? (
                        <>
                            <div style={{
                                background: 'rgba(34, 197, 94, 0.1)',
                                border: '1px solid rgba(34, 197, 94, 0.3)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                marginBottom: '1.5rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '1rem',
                            }}>
                                <CheckCircle size={24} color="var(--success)" />
                                <div>
                                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Training Complete!</div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                        All models have been successfully retrained and deployed.
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={() => setTrainingState({ status: 'idle', progress: 0, logs: '', error: null })}
                                style={{
                                    background: 'linear-gradient(135deg, var(--accent-amber), #f59e0b)',
                                    border: 'none',
                                    padding: '1rem 1.5rem',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    color: '#000',
                                    fontWeight: 700,
                                    width: '100%',
                                    fontSize: '1rem',
                                }}
                            >
                                Start Another Training
                            </button>
                        </>
                    ) : (
                        <>
                            <div style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                padding: '1.5rem',
                                borderRadius: '12px',
                                marginBottom: '1.5rem',
                                display: 'flex',
                                gap: '1rem',
                            }}>
                                <AlertTriangle size={20} color="var(--danger)" style={{ flexShrink: 0 }} />
                                <div>
                                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Training Failed</div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                        {trainingState.error}
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={() => setTrainingState({ status: 'idle', progress: 0, logs: '', error: null })}
                                style={{
                                    background: 'linear-gradient(135deg, var(--accent-amber), #f59e0b)',
                                    border: 'none',
                                    padding: '1rem 1.5rem',
                                    borderRadius: '8px',
                                    cursor: 'pointer',
                                    color: '#000',
                                    fontWeight: 700,
                                    width: '100%',
                                    fontSize: '1rem',
                                }}
                            >
                                Retry Training
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Training Logs Section */}
            {showPreview && trainingState.status === 'running' && (
                <div className="glass-panel" style={{ padding: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <FileText size={20} color="var(--accent-blue)" />
                        <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Training Logs</h3>
                    </div>

                    <div style={{
                        background: 'rgba(0,0,0,0.3)',
                        borderRadius: '8px',
                        padding: '1.5rem',
                        fontFamily: 'monospace',
                        fontSize: '0.85rem',
                        lineHeight: 1.6,
                        color: 'var(--success)',
                        maxHeight: '400px',
                        overflowY: 'auto',
                        border: '1px solid var(--border-light)',
                    }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                            {trainingState.logs || 'Awaiting logs...'}
                        </pre>
                    </div>

                    <button
                        onClick={() => {
                            const text = trainingState.logs;
                            navigator.clipboard.writeText(text);
                            alert('Logs copied to clipboard!');
                        }}
                        style={{
                            marginTop: '1rem',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border-light)',
                            padding: '0.75rem 1rem',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            fontSize: '0.9rem',
                            fontWeight: 600,
                        }}
                    >
                        <Copy size={16} />
                        Copy Logs
                    </button>
                </div>
            )}

            {/* Dataset Preview Section */}
            {preview && showPreview && trainingState.status === 'idle' && (
                <div className="glass-panel" style={{ padding: '2rem', marginTop: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <Eye size={20} color="var(--accent-blue)" />
                            <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Dataset Preview</h3>
                        </div>
                        <button
                            onClick={() => setShowPreview(false)}
                            style={{
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                                color: 'var(--text-muted)',
                            }}
                        >
                            Hide
                        </button>
                    </div>

                    <div style={{ overflowX: 'auto', overflowY: 'auto', maxHeight: '400px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
                        <table style={{
                            width: '100%',
                            borderCollapse: 'collapse',
                            fontSize: '0.85rem',
                        }}>
                            <thead>
                                <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '2px solid var(--border-light)' }}>
                                    {preview.columns && preview.columns.map((col, idx) => (
                                        <th
                                            key={idx}
                                            style={{
                                                padding: '1rem',
                                                textAlign: 'left',
                                                fontWeight: 700,
                                                whiteSpace: 'nowrap',
                                                color: 'var(--accent-cyan)',
                                            }}
                                        >
                                            {col}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {preview.rows && preview.rows.map((row, idx) => (
                                    <tr
                                        key={idx}
                                        style={{
                                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                                            background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                                        }}
                                    >
                                        {row.map((cell, cellIdx) => (
                                            <td
                                                key={cellIdx}
                                                style={{
                                                    padding: '1rem',
                                                    whiteSpace: 'nowrap',
                                                }}
                                            >
                                                {cell === null || cell === undefined ? '-' : String(cell).substring(0, 30)}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DataManagement;
