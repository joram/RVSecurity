import React, { useEffect, useState } from "react";
import './debug.css';
import { fetchFromServer } from '../utils/api';

console.log("Debug component loaded");

function Debug() {
  const [usbPorts, setUsbPorts] = useState({});
  const [kasaOutlets, setKasaOutlets] = useState({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch USB port status
  const getUsbStatus = async () => {
    try {
      const response = await fetchFromServer('/api/debug/usb/status');
      if (response.success) {
        setUsbPorts(response.ports);
      } else {
        console.error('Failed to get USB status:', response.message);
        setMessage(response.message);
      }
    } catch (error) {
      console.error('Error fetching USB status:', error);
      setMessage('Failed to fetch USB status');
    }
  };

  // Fetch Kasa outlet status
  const getKasaStatus = async () => {
    try {
      const response = await fetchFromServer('/api/debug/kasa/status');
      if (response.success) {
        setKasaOutlets(response.outlets);
      } else {
        console.error('Failed to get Kasa status:', response.message);
        setMessage(response.message);
      }
    } catch (error) {
      console.error('Error fetching Kasa status:', error);
      setMessage('Failed to fetch Kasa status');
    }
  };

  // Control USB port
  const controlUsbPort = async (portNum, action) => {
    try {
      const response = await fetch(`/api/debug/usb/${portNum}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      });
      
      const result = await response.json();
      
      if (result.success) {
        setMessage(result.message);
        // Refresh USB status after a short delay
        setTimeout(getUsbStatus, 500);
      } else {
        setMessage(result.message);
      }
    } catch (error) {
      console.error('Error controlling USB port:', error);
      setMessage(`Error controlling USB port ${portNum}`);
    }
  };

  // Control Kasa outlet
  const controlKasaOutlet = async (outletId, action) => {
    try {
      const response = await fetch(`/api/debug/kasa/${outletId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      });
      
      const result = await response.json();
      
      if (result.success) {
        setMessage(result.message);
        // Refresh Kasa status after a longer delay to prevent connection spam
        setTimeout(getKasaStatus, 3000);
      } else {
        setMessage(result.message);
      }
    } catch (error) {
      console.error('Error controlling Kasa outlet:', error);
      setMessage(`Error controlling Kasa outlet ${outletId}`);
    }
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([getUsbStatus(), getKasaStatus()]);
      setLastUpdate(new Date());
      setLoading(false);
    };
    
    loadData();
  }, []);

  // Auto-refresh removed to prevent connection leaks and unwanted updates
  // Power readings will only update when manually controlling outlets

  // Manual refresh function
  const refreshData = async () => {
    setLoading(true);
    setMessage('Refreshing data...');
    await Promise.all([getUsbStatus(), getKasaStatus()]);
    setLoading(false);
    setLastUpdate(new Date());
    setMessage('Data refreshed successfully');
  };

  if (loading) {
    return (
      <div className="debug-container">
        <h1>Debug Control Panel</h1>
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="debug-container">
      <h1>Debug Control Panel</h1>
      
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        <button 
          onClick={refreshData}
          disabled={loading}
          style={{
            backgroundColor: '#4CAF50',
            color: 'white',
            padding: '10px 20px',
            border: 'none',
            borderRadius: '5px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </button>
        {lastUpdate && (
          <div style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </div>
      
      {message && (
        <div className="message-box">
          {message}
        </div>
      )}

      <div className="debug-sections">
        {/* USB Ports Section */}
        <div className="debug-section">
          <h2>USB Ports (Internet Access)</h2>
          <div className="control-grid">
            {Object.entries(usbPorts).map(([portNum, portData]) => (
              <div key={portNum} className="control-item">
                <h3>{portData.name}</h3>
                <div className="control-buttons">
                  <label className="radio-control">
                    <input
                      type="radio"
                      name={`usb-${portNum}`}
                      checked={portData.enabled}
                      onChange={() => controlUsbPort(portNum, 'on')}
                    />
                    <span className={`radio-label ${portData.enabled ? 'active' : ''}`}>
                      ON
                    </span>
                  </label>
                  <label className="radio-control">
                    <input
                      type="radio"
                      name={`usb-${portNum}`}
                      checked={!portData.enabled}
                      onChange={() => controlUsbPort(portNum, 'off')}
                    />
                    <span className={`radio-label ${!portData.enabled ? 'active' : ''}`}>
                      OFF
                    </span>
                  </label>
                </div>
                {portData.error && (
                  <div className="error-text">{portData.error}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Kasa Power Strip Section */}
        <div className="debug-section">
          <h2>Kasa Power Strip</h2>
          <div className="control-grid">
            {Object.entries(kasaOutlets).map(([outletId, outletData]) => {
              const isOffline = outletData.status && ['offline', 'error', 'system_error', 'comm_error'].includes(outletData.status);
              const isMockData = outletData.mock || isOffline;
              
              return (
                <div key={outletId} className={`control-item ${isOffline ? 'offline' : ''}`}>
                  <h3>{outletData.name}</h3>
                  {isMockData && (
                    <div className="status-indicator">
                      {outletData.status === 'offline' && <span className="status-offline">OFFLINE</span>}
                      {outletData.status === 'error' && <span className="status-error">CONNECTION ERROR</span>}
                      {outletData.status === 'system_error' && <span className="status-error">SYSTEM ERROR</span>}
                      {outletData.status === 'comm_error' && <span className="status-error">COMM ERROR</span>}
                      {outletData.mock && !outletData.status && <span className="status-mock">MOCK DATA</span>}
                    </div>
                  )}
                  <div className="control-buttons">
                    <label className="radio-control">
                      <input
                        type="radio"
                        name={`kasa-${outletId}`}
                        checked={outletData.enabled}
                        onChange={() => !isOffline && controlKasaOutlet(outletId, 'on')}
                        disabled={isOffline}
                      />
                      <span className={`radio-label ${outletData.enabled ? 'active' : ''} ${isOffline ? 'disabled' : ''}`}>
                        ON
                      </span>
                    </label>
                    <label className="radio-control">
                      <input
                        type="radio"
                        name={`kasa-${outletId}`}
                        checked={!outletData.enabled}
                        onChange={() => !isOffline && controlKasaOutlet(outletId, 'off')}
                        disabled={isOffline}
                      />
                      <span className={`radio-label ${!outletData.enabled ? 'active' : ''} ${isOffline ? 'disabled' : ''}`}>
                        OFF
                      </span>
                    </label>
                  </div>
                  <div className={`power-display ${isOffline ? 'offline' : ''}`}>
                    Power: {outletData.power_watts}W
                    {isMockData && <span className="mock-indicator"> (simulated)</span>}
                  </div>
                  {outletData.error && (
                    <div className="error-text">{outletData.error}</div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Debug;
