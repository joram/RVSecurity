import React, { useState, useEffect, useRef } from 'react';
import { Header, Icon, Form, Radio, Container, Segment, Message } from 'semantic-ui-react';
import './PlexSvr.css';
import { getServerUrl } from '../utils/api';

const PlexSvr = () => {
  const [selectedOption, setSelectedOption] = useState('off');
  const [message, setMessage] = useState('');
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isServerOn, setIsServerOn] = useState(false);
  const timerRef = useRef(null);

  // Control Synology NAS
  const controlSynology = async (action) => {
    try {
      console.log(`Sending ${action} command to Synology NAS...`);
      setMessage(`Sending ${action} command to Synology NAS...`);
      
      const response = await fetch(`${getServerUrl()}/api/debug/synology/${action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        setMessage(`${action}: ${result.message}`);
        setIsServerOn(action === 'power-on');
        return true;
      } else {
        setMessage(`${action} failed: ${result.message}`);
        return false;
      }
    } catch (error) {
      console.error('Error controlling Synology NAS:', error);
      setMessage(`Error communicating with Synology NAS: ${error.message}`);
      return false;
    }
  };

  // Start countdown timer
  const startTimer = (minutes) => {
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    setTimeRemaining(minutes * 60); // Convert minutes to seconds
    
    timerRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          // Timer expired, turn off server
          controlSynology('power-off');
          setSelectedOption('off');
          setMessage('Timer expired - turning off Synology server');
          clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Handle radio button change
  const handleChange = async (e, { value }) => {
    setSelectedOption(value);
    
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setTimeRemaining(0);

    if (value === 'off') {
      // Turn off immediately
      await controlSynology('power-off');
    } else if (value === 'manual') {
      // Turn on and leave on
      await controlSynology('power-on');
    } else if (value.endsWith('min')) {
      // Timed options - turn on and start timer
      const minutes = parseInt(value.replace('min', ''));
      const success = await controlSynology('power-on');
      if (success) {
        startTimer(minutes);
        setMessage(`Server turned on for ${minutes} minutes`);
      }
    }
  };

  // Format time remaining for display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return (
    <div className="plex-svr-page">
      <Header as="h1" icon textAlign="center">
        <Icon name="tv" />
        <Header.Content>
          Local Plex Server
          <Header.Subheader>Turns the local Plex server on/off for power savings (10 Watts)</Header.Subheader>
        </Header.Content>
      </Header>
      
      <Container>
        <Segment>
          {message && (
            <Message>
              {message}
              {timeRemaining > 0 && (
                <div style={{ marginTop: '10px', fontWeight: 'bold' }}>
                  Time remaining: {formatTime(timeRemaining)}
                </div>
              )}
            </Message>
          )}
          
          <Form>
            <Form.Field>
              <Radio
                label='Off'
                name='plexServerOption'
                value='off'
                checked={selectedOption === 'off'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 2 minutes'
                name='plexServerOption'
                value='2min'
                checked={selectedOption === '2min'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 3 minutes'
                name='plexServerOption'
                value='3min'
                checked={selectedOption === '3min'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 4 minutes'
                name='plexServerOption'
                value='4min'
                checked={selectedOption === '4min'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On until I turn off'
                name='plexServerOption'
                value='manual'
                checked={selectedOption === 'manual'}
                onChange={handleChange}
              />
            </Form.Field>
          </Form>
        </Segment>
      </Container>
    </div>
  );
};

export default PlexSvr;
