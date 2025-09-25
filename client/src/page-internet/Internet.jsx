import React, { useState, useEffect } from 'react';
import { Form, Button, Message, Card, Header, Icon, Segment, Radio, TextArea, Checkbox } from 'semantic-ui-react';
import './Internet.css';
import { fetchFromServer } from '../utils/api';

const Internet = () => {
  const [selectedOption, setSelectedOption] = useState('none');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [abortController, setAbortController] = useState(null);

  // WiFi configuration states
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [permanentStore, setPermanentStore] = useState(false);
  const [output, setOutput] = useState('');
  const [wifiLoading, setWifiLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const internetOptions = [
    { value: 'cellular', text: 'Cellular', port: 1, waitTime: 15 },
    { value: 'wifi', text: 'WiFi', port: 2, waitTime: 10 },
    { value: 'starlink', text: 'Starlink', port: 3, waitTime: 20 },
    { value: 'wired', text: 'Wired', port: 4, waitTime: 8 },
    { value: 'none', text: 'None', port: 0, waitTime: 0 }
  ];

  useEffect(() => {
    let interval;
    if (countdown > 0) {
      interval = setInterval(() => {
        setCountdown(prev => prev - 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [countdown]);

  const handleOptionChange = (e, { value }) => {
    // Always allow changing the selection - this will interrupt any ongoing operations
    setSelectedOption(value);
    setConnectionStatus(null);
    setStatusMessage('');
    setCountdown(0);
    
    // Abort any ongoing operation
    if (abortController) {
      abortController.abort();
    }
    
    // Reset states
    setIsLoading(false);
    setIsConnecting(false);
    
    // Automatically execute the selected action
    setTimeout(() => {
      executeAction(value);
    }, 100); // Small delay to ensure UI updates
  };

  const executeAction = async (selectedValue) => {
    if (!selectedValue) return;

    const option = internetOptions.find(opt => opt.value === selectedValue);
    if (!option) return;

    // Create new AbortController for this operation
    const newAbortController = new AbortController();
    setAbortController(newAbortController);

    // Handle "None" option - just power off all ports
    if (selectedValue === 'none') {
      setIsLoading(true);
      setIsConnecting(true);
      setConnectionStatus(null);
      setStatusMessage('Powering off all internet connections...');

      try {
        const response = await fetchFromServer('/api/internet/power', {
          method: 'POST',
          body: JSON.stringify({
            port: 0, // 0 means all ports off
            action: 'off'
          }),
          signal: newAbortController.signal
        });

        if (newAbortController.signal.aborted) return;

        if (response.success) {
          setConnectionStatus('info');
          setStatusMessage('🔌 All internet connections powered off');
        } else {
          throw new Error(response.message || 'Failed to power off ports');
        }

      } catch (error) {
        if (newAbortController.signal.aborted) return;
        console.error('Power off error:', error);
        setConnectionStatus('error');
        setStatusMessage(`❌ Failed to power off connections: ${error.message}`);
      } finally {
        setIsLoading(false);
        setIsConnecting(false);
        setAbortController(null);
      }
      return;
    }

    // Handle regular connection options
    setIsLoading(true);
    setIsConnecting(true);
    setConnectionStatus(null);
    setStatusMessage(`Connecting to ${option.text}...`);

    try {
      // Step 1: Power on the selected port and turn off others
      setStatusMessage(`Powering on ${option.text} (Port ${option.port})...`);
      
      const powerResponse = await fetchFromServer('/api/internet/power', {
        method: 'POST',
        body: JSON.stringify({
          port: option.port,
          action: 'on'
        }),
        signal: newAbortController.signal
      });

      if (newAbortController.signal.aborted) return;

      if (!powerResponse.success) {
        throw new Error(powerResponse.message || 'Failed to power on port');
      }

      // Step 2: Wait for the specified time with countdown (but check for abort)
      setStatusMessage(`Waiting for ${option.text} to initialize...`);
      setCountdown(option.waitTime);
      
      // Use a more granular wait that can be interrupted
      for (let i = option.waitTime; i > 0; i--) {
        if (newAbortController.signal.aborted) return;
        await new Promise(resolve => setTimeout(resolve, 1000));
        if (newAbortController.signal.aborted) return;
        setCountdown(i - 1);
      }

      if (newAbortController.signal.aborted) return;

      // Step 3: Test internet connectivity
      setStatusMessage(`Testing internet connectivity...`);
      setCountdown(0);
      
      const testResponse = await fetchFromServer('/api/internet/test', {
        method: 'POST',
        body: JSON.stringify({
          connection_type: selectedValue
        }),
        signal: newAbortController.signal
      });

      if (newAbortController.signal.aborted) return;

      if (testResponse.success && testResponse.connected) {
        setConnectionStatus('success');
        setStatusMessage(`✅ Internet connection established via ${option.text}!`);
      } else {
        setConnectionStatus('warning');
        setStatusMessage(`⚠️ ${option.text} powered on, but internet connectivity could not be verified. ${testResponse.message || ''}`);
      }

    } catch (error) {
      if (newAbortController.signal.aborted) return;
      console.error('Connection error:', error);
      setConnectionStatus('error');
      setStatusMessage(`❌ Failed to connect via ${option.text}: ${error.message}`);
    } finally {
      setIsLoading(false);
      setIsConnecting(false);
      setAbortController(null);
    }
  };

  // WiFi configuration functions
  const handleWifiSubmit = async (e) => {
    e.preventDefault();
    
    if (!ssid.trim()) {
      setOutput('Error: SSID is required');
      return;
    }
    
    if (!password.trim()) {
      setOutput('Error: Password is required');
      return;
    }

    setWifiLoading(true);
    setOutput('Sending WiFi configuration to RP2W...\n');
    
    try {
      const requestData = {
        ssid: ssid.trim(),
        password: password.trim(),
        permanent: permanentStore
      };

      const response = await fetchFromServer('/api/wifi-config', {
        method: 'POST',
        body: JSON.stringify(requestData)
      });

      let resultMessage = '';
      let resultType = 'info';
      
      // Handle different exit codes based on the Python script
      switch (response.exit_code) {
        case 0:
          resultMessage = 'Success: WiFi connected and configuration saved!';
          resultType = 'success';
          break;
        case 1:
          resultMessage = 'Error: General failure (connection, invalid packet, or server error)';
          resultType = 'error';
          break;
        case 100:
          resultMessage = 'Warning: SSID/Password updated but activation failed (likely bad password)';
          resultType = 'warning';
          break;
        case 101:
          resultMessage = 'Warning: SSID/Password updated but WiFi connection failed (bad/unreachable SSID or timeout)';
          resultType = 'warning';
          break;
        default:
          resultMessage = `Unknown result: Exit code ${response.exit_code}`;
          resultType = 'info';
      }

      setLastResult({ type: resultType, message: resultMessage });
      setOutput(prev => prev + `\nResponse from RP2W:\n${response.output}\n\n${resultMessage}`);
      
    } catch (error) {
      const errorMessage = `Error communicating with server: ${error.message}`;
      setLastResult({ type: 'error', message: errorMessage });
      setOutput(prev => prev + `\n${errorMessage}`);
    } finally {
      setWifiLoading(false);
    }
  };

  const clearWifiOutput = () => {
    setOutput('');
    setLastResult(null);
  };

  const clearWifiForm = () => {
    setSsid('');
    setPassword('');
    setPermanentStore(false);
  };

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'success': return 'check circle';
      case 'warning': return 'warning circle';
      case 'error': return 'times circle';
      case 'info': return 'info circle';
      default: return 'wifi';
    }
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'success': return 'green';
      case 'warning': return 'yellow';
      case 'error': return 'red';
      case 'info': return 'blue';
      default: return 'grey';
    }
  };

  return (
    <div className="internet-page">
      <Header as="h1" icon textAlign="center">
        <Icon name="wifi" />
        <Header.Content>
          Internet Connection Control
          <Header.Subheader>Select and manage your internet connection method</Header.Subheader>
        </Header.Content>
      </Header>

      <div className="internet-container">
        <Card className="internet-control-card">
          <Card.Content>
            <Form>
              <Form.Field>
                <label className="internet-connection-label">Select Internet Connection:</label>
                {internetOptions.map(option => (
                  <Form.Field key={option.value}>
                    <Radio
                      label={option.value === 'none' ? 
                        `${option.text} - Maximizes power saving` : 
                        `${option.text} (Port ${option.port}) - ${option.waitTime}s initialization`}
                      name="internetOption"
                      value={option.value}
                      checked={selectedOption === option.value}
                      onChange={handleOptionChange}
                      disabled={false}  // Always allow changing selection
                    />
                  </Form.Field>
                ))}
              </Form.Field>
            </Form>
          </Card.Content>
        </Card>

        <Card className="internet-status-card">
          <Card.Content>
            <Card.Header>
              Connection Status
              {countdown > 0 && (
                <span className="countdown-badge">
                  {countdown}s
                </span>
              )}
            </Card.Header>
          </Card.Content>
          <Card.Content>
            {/* Starlink Power Warning */}
            {selectedOption === 'starlink' && (
              <Message 
                color="red"
                icon="warning sign"
                header="Important Notice"
                content="Be sure Power is applied"
                style={{ marginBottom: '15px' }}
              />
            )}

            {statusMessage && (
              <Message 
                color={getStatusColor()}
                icon={getStatusIcon()}
                header={connectionStatus === 'success' ? 'Connected' : 
                        connectionStatus === 'warning' ? 'Partial Success' : 
                        connectionStatus === 'error' ? 'Connection Failed' : 
                        connectionStatus === 'info' ? 'Information' : 'Status'}
                content={statusMessage}
              />
            )}
            
            {/* WiFi Configuration Section */}
            {selectedOption === 'wifi' && (
              <div style={{ marginBottom: '20px' }}>
                <Card className="wifi-config-card">
                  <Card.Content>
                    <Card.Header>WiFi Configuration</Card.Header>
                    <Card.Description>
                      Configure WiFi settings for RP2W device
                    </Card.Description>
                  </Card.Content>
                  <Card.Content>
                    <Form onSubmit={handleWifiSubmit}>
                      <Form.Field required>
                        <label>SSID (Network Name)</label>
                        <Form.Input
                          placeholder="Enter WiFi network name"
                          value={ssid}
                          onChange={(e) => setSsid(e.target.value)}
                          disabled={wifiLoading}
                          icon="wifi"
                          iconPosition="left"
                        />
                      </Form.Field>
                      
                      <Form.Field required>
                        <label>Password</label>
                        <Form.Input
                          type="password"
                          placeholder="Enter WiFi password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          disabled={wifiLoading}
                          icon="lock"
                          iconPosition="left"
                        />
                      </Form.Field>

                      <Form.Field>
                        <Checkbox
                          label="Permanently store this SSID/Password pair in RP2W"
                          checked={permanentStore}
                          onChange={(e, { checked }) => setPermanentStore(checked)}
                          disabled={wifiLoading}
                        />
                      </Form.Field>

                      <div className="wifi-form-buttons">
                        <Button 
                          type="submit" 
                          primary 
                          loading={wifiLoading}
                          disabled={wifiLoading || !ssid.trim() || !password.trim()}
                          icon="send"
                          labelPosition="left"
                          content="Send Configuration"
                        />
                        <Button 
                          type="button" 
                          secondary 
                          onClick={clearWifiForm}
                          disabled={wifiLoading}
                          icon="refresh"
                          content="Clear Form"
                        />
                      </div>
                    </Form>
                  </Card.Content>
                </Card>

                <Card className="wifi-output-card" style={{ marginTop: '15px' }}>
                  <Card.Content>
                    <Card.Header>
                      WiFi Output
                      <Button 
                        floated="right" 
                        size="mini" 
                        onClick={clearWifiOutput}
                        disabled={wifiLoading}
                        icon="trash"
                        content="Clear"
                      />
                    </Card.Header>
                  </Card.Content>
                  <Card.Content>
                    {lastResult && (
                      <Message 
                        color={lastResult.type === 'success' ? 'green' : 
                               lastResult.type === 'warning' ? 'yellow' : 
                               lastResult.type === 'error' ? 'red' : 'blue'}
                        icon={lastResult.type === 'success' ? 'check circle' : 
                              lastResult.type === 'warning' ? 'warning circle' : 
                              lastResult.type === 'error' ? 'times circle' : 'info circle'}
                        header={lastResult.type === 'success' ? 'Success' : 
                                lastResult.type === 'warning' ? 'Warning' : 
                                lastResult.type === 'error' ? 'Error' : 'Information'}
                        content={lastResult.message}
                      />
                    )}
                    
                    <Segment className="output-segment">
                      <TextArea
                        value={output}
                        placeholder="WiFi configuration output will appear here..."
                        style={{ width: '100%', minHeight: '200px' }}
                        readOnly
                      />
                    </Segment>
                  </Card.Content>
                </Card>
              </div>
            )}
            
            <Segment className="status-details">
              <div className="status-grid">
                <div className="status-item">
                  <strong>Selected Connection:</strong> 
                  <span>{selectedOption ? internetOptions.find(opt => opt.value === selectedOption)?.text : 'None'}</span>
                </div>
                <div className="status-item">
                  <strong>Port Status:</strong> 
                  <span>{isConnecting ? 'Initializing...' : selectedOption ? 'Ready' : 'Standby'}</span>
                </div>
                <div className="status-item">
                  <strong>Internet Status:</strong> 
                  <span>
                    {connectionStatus === 'success' ? '✅ Connected' : 
                     connectionStatus === 'warning' ? '⚠️ Port Active, Connectivity Unknown' : 
                     connectionStatus === 'error' ? '❌ Failed' : 
                     '⚪ Not tested'}
                  </span>
                </div>
              </div>
            </Segment>
          </Card.Content>
        </Card>
      </div>
    </div>
  );
};

export default Internet;
