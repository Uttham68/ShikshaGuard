import React, { useState, useEffect } from 'react';
import { 
    Cpu, 
    Activity, 
    Database, 
    AlertCircle, 
    PlayCircle, 
    Clock, 
    RotateCcw, 
    ShieldAlert, 
    Zap,
    History,
    RefreshCw
} from 'lucide-react';
import api from '../api';

const AiControlPanel = () => {
    const [modelVersions, setModelVersions] = useState([]);
    const [anomalies, setAnomalies] = useState(null);
    const [trainingStatus, setTrainingStatus] = useState(false);
    const [rollbackStatus, setRollbackStatus] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchSystemData = async () => {
        setLoading(true);
        try {
            const modelsRes = await api.get('/models/versions').catch(() => ({ data: { versions: [] } }));
            setModelVersions(modelsRes.data.versions || []);
            // Set default anomaly data - global stats are calculated on-demand
            setAnomalies({ global_anomaly_fraction: 0, highest_density_anomaly_clusters: 0 });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSystemData();
    }, []);

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
            <Activity className="animate-spin" size={32} color="var(--accent-blue)" />
        </div>
    );

    const triggerRetrain = async () => {
        if (!window.confirm("Initialize full neuro-retraining pipeline?")) return;
        setTrainingStatus(true);
        try {
            await api.post('/train');
            await fetchSystemData();
        } catch (err) {
            console.error("Retrain failure", err);
        } finally {
            setTrainingStatus(false);
        }
    };

    const handleRollback = async (version_ts) => {
        if (!window.confirm("Revert systemic intelligence to previous state?")) return;
        setRollbackStatus(version_ts);
        try {
            await api.post(`/models/rollback/${version_ts}`);
            await fetchSystemData();
        } catch (err) {
            console.error("Rollback failure", err);
        } finally {
            setRollbackStatus(null);
        }
    };

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>AI Control</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Manage systemic intelligence lifecycles and historical rollbacks.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '2rem' }}>
                
                {/* Version History */}
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <History size={20} color="var(--accent-blue)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Temporal Weights</h2>
                    </div>
                    
                    <div className="glass-panel" style={{ padding: '0.5rem' }}>
                        {modelVersions.length === 0 ? (
                            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No historical versions found.</div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                {modelVersions.map((v, i) => (
                                    <div key={v} style={{ 
                                        padding: '1.25rem', 
                                        borderBottom: i === modelVersions.length - 1 ? 'none' : '1px solid var(--border-light)',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                        backgroundColor: i === 0 ? 'rgba(59, 130, 246, 0.03)' : 'transparent'
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: i === 0 ? 'var(--accent-blue)' : 'var(--text-muted)' }} />
                                            <div>
                                                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{new Date(parseInt(v) * 1000).toLocaleString()}</div>
                                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{i === 0 ? 'Current Active State' : 'Legacy Snapshot'}</div>
                                            </div>
                                        </div>
                                        
                                        {i !== 0 ? (
                                            <button 
                                                onClick={() => handleRollback(v)}
                                                disabled={rollbackStatus !== null}
                                                className="btn"
                                                style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem', border: '1px solid var(--border-light)' }}
                                            >
                                                {rollbackStatus === v ? <RefreshCw className="animate-spin" size={14} /> : <RotateCcw size={14} />}
                                                Rollback
                                            </button>
                                        ) : (
                                            <span className="badge badge-success">Active</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Operations */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    <div className="glass-panel" style={{ padding: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                            <Zap size={20} color="var(--warning)" />
                            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Operations</h2>
                        </div>
                        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '2rem' }}>
                            Re-initialize the XGBoost training pipeline. This will consume the current baseline artifacts to calibrate systemic risk scoring weights.
                        </p>
                        <button 
                            className="btn btn-primary" 
                            style={{ width: '100%', justifyContent: 'center', padding: '0.875rem' }} 
                            onClick={triggerRetrain}
                            disabled={trainingStatus}
                        >
                            {trainingStatus ? <Activity className="animate-spin" size={18} /> : <PlayCircle size={18} />}
                            {trainingStatus ? 'Processing Neural Weights...' : 'Initiate Full Retraining'}
                        </button>
                    </div>

                    <div className="glass-panel" style={{ padding: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                            <ShieldAlert size={20} color="var(--accent-purple)" />
                            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Anomaly pulse</h2>
                        </div>
                        
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                                <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Global Variance</div>
                                <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--warning)' }}>
                                    {(anomalies?.global_anomaly_fraction * 100 || 0).toFixed(1)}%
                                </div>
                            </div>
                            <div className="glass-card" style={{ padding: '1rem', textAlign: 'center' }}>
                                <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Flagged Grids</div>
                                <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                                    {anomalies?.highest_density_anomaly_clusters || 0}
                                </div>
                            </div>
                        </div>
                        
                        <div style={{ marginTop: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                            Isolation Forest unsupervised scan is active. Monitoring for multi-dimensional reporting inconsistencies in real-time.
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default AiControlPanel;
