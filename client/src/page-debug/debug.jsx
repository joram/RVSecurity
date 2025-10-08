import React, { useEffect, useState } from "react";
import './debug.css';
import { fetchFromServer } from '../utils/api';

console.log("Debug component loaded");

function Debug() {
  const [usbPorts, setUsbPorts] = useState({});
  const [kasaOutlets, setKasaOutlets] = useState({});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

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
        // Refresh Kasa status after a short delay to get updated power readings
        setTimeout(getKasaStatus, 1000);
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
      setLoading(false);
    };
    
    loadData();
  }, []);

  // Auto-refresh every 5 seconds for power readings
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading) {
        getKasaStatus(); // Refresh Kasa status to get updated power readings
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [loading]);

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
            {Object.entries(kasaOutlets).map(([outletId, outletData]) => (
              <div key={outletId} className="control-item">
                <h3>{outletData.name}</h3>
                <div className="control-buttons">
                  <label className="radio-control">
                    <input
                      type="radio"
                      name={`kasa-${outletId}`}
                      checked={outletData.enabled}
                      onChange={() => controlKasaOutlet(outletId, 'on')}
                    />
                    <span className={`radio-label ${outletData.enabled ? 'active' : ''}`}>
                      ON
                    </span>
                  </label>
                  <label className="radio-control">
                    <input
                      type="radio"
                      name={`kasa-${outletId}`}
                      checked={!outletData.enabled}
                      onChange={() => controlKasaOutlet(outletId, 'off')}
                    />
                    <span className={`radio-label ${!outletData.enabled ? 'active' : ''}`}>
                      OFF
                    </span>
                  </label>
                </div>
                <div className="power-display">
                  Power: {outletData.power_watts}W
                </div>
                {outletData.error && (
                  <div className="error-text">{outletData.error}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Debug;
