import React, { useState } from 'react';
import { Form, Button, TextArea, Message, Card, Header, Segment, Icon, Checkbox } from 'semantic-ui-react';
import './WiFi.css';
import { fetchFromServer } from '../utils/api';

const WiFi = () => {
  // Force refresh - updated CSS layout
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [permanentStore, setPermanentStore] = useState(false);
  const [output, setOutput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!ssid.trim()) {
      setOutput('Error: SSID is required');
      return;
    }
    
    if (!password.trim()) {
      setOutput('Error: Password is required');
      return;
    }

    setIsLoading(true);
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
      setIsLoading(false);
    }
  };

  const clearOutput = () => {
    setOutput('');
    setLastResult(null);
  };

  const clearForm = () => {
    setSsid('');
    setPassword('');
    setPermanentStore(false);
  };

  return (
    <div className="wifi-page">
      <Header as="h1" icon textAlign="center">
        <Icon name="wifi" />
        <Header.Content>
          WiFi Configuration
          <Header.Subheader>Configure WiFi settings for RP2W device</Header.Subheader>
        </Header.Content>
      </Header>

      <div style={{ 
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '20px',
        marginTop: '20px',
        maxWidth: '600px',
        width: '100%',
        margin: '20px auto 0 auto',
        padding: '0 15px'
      }}>
        <Card className="wifi-form-card" style={{ width: '100%', minHeight: '300px' }}>
          <Card.Content>
            <Card.Header>WiFi Settings</Card.Header>
            <Card.Description>
              Enter the WiFi credentials to configure the RP2W device
            </Card.Description>
          </Card.Content>
          <Card.Content>
            <Form onSubmit={handleSubmit}>
              <Form.Field required>
                <label>SSID (Network Name)</label>
                <Form.Input
                  placeholder="Enter WiFi network name"
                  value={ssid}
                  onChange={(e) => setSsid(e.target.value)}
                  disabled={isLoading}
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
                  disabled={isLoading}
                  icon="lock"
                  iconPosition="left"
                />
              </Form.Field>

              <Form.Field>
                <Checkbox
                  label="Permanently store this SSID/Password pair in RP2W"
                  checked={permanentStore}
                  onChange={(e, { checked }) => setPermanentStore(checked)}
                  disabled={isLoading}
                />
              </Form.Field>

              <div className="form-buttons">
                <Button 
                  type="submit" 
                  primary 
                  loading={isLoading}
                  disabled={isLoading || !ssid.trim() || !password.trim()}
                  icon="send"
                  labelPosition="left"
                  content="Send Configuration"
                />
                <Button 
                  type="button" 
                  secondary 
                  onClick={clearForm}
                  disabled={isLoading}
                  icon="refresh"
                  content="Clear Form"
                />
              </div>
            </Form>
          </Card.Content>
        </Card>

        <Card className="wifi-output-card" style={{ width: '100%', minHeight: '400px' }}>
          <Card.Content>
            <Card.Header>
              Output
              <Button 
                floated="right" 
                size="mini" 
                onClick={clearOutput}
                disabled={isLoading}
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
                placeholder="Output from RP2W will appear here..."
                style={{ width: '100%', minHeight: '300px' }}
                readOnly
              />
            </Segment>
          </Card.Content>
        </Card>
      </div>
    </div>
  );
};

export default WiFi;
