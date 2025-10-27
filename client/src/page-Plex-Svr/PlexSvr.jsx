import React, { useState, useEffect, useRef } from 'react';
import { Header, Icon, Form, Radio, Container, Segment, Message } from 'semantic-ui-react';
import './PlexSvr.css';
import { getServerUrl } from '../utils/api';

const PlexSvr = () => {
  const [selectedOption, setSelectedOption] = useState('off');
  const [message, setMessage] = useState('');
  const [scheduledTime, setScheduledTime] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
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

  // Get scheduled shutdown time from server
  const getScheduledTime = async () => {
    try {
      const response = await fetch(`${getServerUrl()}/api/debug/synology/scheduled-time`);
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setScheduledTime(result.scheduled_time);
          return result.scheduled_time;
        }
      }
    } catch (error) {
      console.error('Error getting scheduled time:', error);
    }
    return null;
  };

  // Schedule shutdown on server
  const scheduleShutdown = async (hours) => {
    try {
      const response = await fetch(`${getServerUrl()}/api/debug/synology/schedule-shutdown`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ hours }),
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setScheduledTime(result.scheduled_time);
          return result.scheduled_time; // Return the actual timestamp
        }
      }
    } catch (error) {
      console.error('Error scheduling shutdown:', error);
    }
    return false;
  };

  // Cancel scheduled shutdown
  const cancelScheduledShutdown = async () => {
    try {
      const response = await fetch(`${getServerUrl()}/api/debug/synology/scheduled-time`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setScheduledTime(null);
          return true;
        }
      }
    } catch (error) {
      console.error('Error cancelling scheduled shutdown:', error);
    }
    return false;
  };

  // Check if server is currently running (without changing UI state)
  const isServerCurrentlyRunning = async () => {
    try {
      const response = await fetch(`${getServerUrl()}/api/debug/synology/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        return false;
      }
      
      const result = await response.json();
      
      if (result.success && result.message) {
        const messageText = String(result.message).toLowerCase();
        
        // Look for indicators that server is actually running/responding to services
        return messageText.includes('running') || 
               messageText.includes('online') || 
               messageText.includes('logged in') ||
               messageText.includes('authenticated') ||
               messageText.includes('web interface') ||
               messageText.includes('dsm') ||
               (messageText.includes('status') && messageText.includes('ok'));
      }
    } catch (error) {
      console.error('Error checking server status:', error);
    }
    return false;
  };

  // Check server status on component load
  const checkServerStatus = async () => {
    let serverIsOn = false; // Declare local variable
    
    try {
      setIsLoading(true);
      setMessage('Checking server status...');
      
      const response = await fetch(`${getServerUrl()}/api/debug/synology/status`, {
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
        // Check the message field for actual server status indicators
        if (result.message) {
          const messageText = String(result.message).toLowerCase();
          
          // Look for indicators that server is actually running/responding to services
          // NOT just network reachable (which could be just WoL capability)
          serverIsOn = messageText.includes('running') || 
                      messageText.includes('online') || 
                      messageText.includes('logged in') ||
                      messageText.includes('authenticated') ||
                      messageText.includes('web interface') ||
                      messageText.includes('dsm') ||
                      (messageText.includes('status') && messageText.includes('ok'));
        }
        
        if (serverIsOn) {
          // Don't set the radio button here - let getScheduledTime determine if it's timed or manual
          setMessage("✅ Server is running.");
        } else {
          setSelectedOption('off');
          // Check if ethernet is active by parsing the message text
          let ethernetActive = false;
          if (result.message) {
            const messageText = String(result.message).toLowerCase();
            // Look for "ethernet: active" or "ethernet:      active" in the message
            ethernetActive = messageText.includes('ethernet:') && 
                           messageText.includes('active') &&
                           !messageText.includes('inactive');
          }
          
          if (ethernetActive) {
            setMessage("⏹️ Server is offline and ready to startup");
          } else {
            setMessage("❌ Synology Plex server is offline and must be restarted manually. It's behind TV set.");
          }
        }
      } else {
        setMessage(`❌ Unable to determine server status: ${result.message || 'Unknown error'}`);
        setSelectedOption('off');
      }
      
      // Also get scheduled shutdown time and update radio selection
      const scheduledTime = await getScheduledTime();
      
      // If server is on and there's a scheduled time, set appropriate radio button
      if (serverIsOn && scheduledTime) {
        const now = Date.now() / 1000;
        const remainingSeconds = scheduledTime - now;
        const remainingHours = Math.ceil(remainingSeconds / 3600);
        
        // Set the radio button based on remaining time
        if (remainingHours >= 2 && remainingHours <= 4) {
          setSelectedOption(`${remainingHours}hr`);
        } else {
          setSelectedOption('manual');
        }
      } else if (serverIsOn && !scheduledTime) {
        setSelectedOption('manual');
      }
      
    } catch (error) {
      console.error('Error checking server status:', error);
      setMessage('Error checking server status - assuming server is off');
      setSelectedOption('off');
    } finally {
      setIsLoading(false);
    }
  };

  // Start countdown timer based on scheduled time
  const startTimer = (useScheduledTime = null) => {
    // Clear any existing timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    const targetTime = useScheduledTime || scheduledTime;
    if (!targetTime) {
      setTimeRemaining(0);
      return;
    }
    
    timerRef.current = setInterval(() => {
      const now = Date.now() / 1000; // Convert to seconds
      const remaining = Math.max(0, Math.floor(targetTime - now));
      
      setTimeRemaining(remaining);
      
      if (remaining <= 0) {
        // Timer expired, turn off server
        controlSynology('power-off');
        setSelectedOption('off');
        setScheduledTime(null);
        setMessage('Synology Plex Server off');
        clearInterval(timerRef.current);
      }
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

    if (value === 'off') {
      // Turn off immediately and cancel any scheduled shutdown
      await cancelScheduledShutdown();
      await controlSynology('power-off');
      setTimeRemaining(0);
    } else if (value === 'manual') {
      // Turn on and leave on (cancel any scheduled shutdown)
      await cancelScheduledShutdown();
      
      // Check if server is already running
      const serverRunning = await isServerCurrentlyRunning();
      if (serverRunning) {
        setMessage('✅ Server is running.');
      } else {
        await controlSynology('power-on');
      }
      setTimeRemaining(0);
    } else if (value.endsWith('hr')) {
      // Timed options - turn on and schedule shutdown
      const hours = parseInt(value.replace('hr', ''));
      
      // Check if server is already running
      const serverRunning = await isServerCurrentlyRunning();
      let success = true;
      
      if (serverRunning) {
        setMessage(`Server already running - scheduled to turn off in ${hours} hours`);
      } else {
        success = await controlSynology('power-on');
        if (success) {
          setMessage(`Server turned on for ${hours} hours`);
        }
      }
      
      if (success) {
        const newScheduledTime = await scheduleShutdown(hours);
        if (newScheduledTime) {
          // Use the fresh scheduled time directly to avoid React state timing issues
          startTimer(newScheduledTime);
        }
      }
    }
  };

  // Format time remaining for display
  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    let countdown = '';
    if (hours > 0) {
      countdown = `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      countdown = `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    // Add wall clock time if we have a scheduled time
    if (scheduledTime) {
      const shutoffTime = new Date(scheduledTime * 1000).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
      return `${countdown} remaining (turns off at ${shutoffTime})`;
    }
    
    return countdown;
  };

  // Cleanup timer on unmount and check server status on mount
  useEffect(() => {
    // Check server status when component mounts
    checkServerStatus();
    
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Start timer when scheduledTime changes
  useEffect(() => {
    if (scheduledTime) {
      startTimer();
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      setTimeRemaining(0);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduledTime]);

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
          {isLoading && (
            <Message icon>
              <Icon name="circle notched" loading />
              <Message.Content>
                <Message.Header>Loading</Message.Header>
                Checking server status...
              </Message.Content>
            </Message>
          )}
          
          {!isLoading && message && (
            <Message negative={message.includes('must be restarted manually')}>
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
                disabled={isLoading}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 2 hours'
                name='plexServerOption'
                value='2hr'
                checked={selectedOption === '2hr'}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 3 hours'
                name='plexServerOption'
                value='3hr'
                checked={selectedOption === '3hr'}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 4 hours'
                name='plexServerOption'
                value='4hr'
                checked={selectedOption === '4hr'}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On until I turn off'
                name='plexServerOption'
                value='manual'
                checked={selectedOption === 'manual'}
                onChange={handleChange}
                disabled={isLoading}
              />
            </Form.Field>
          </Form>
        </Segment>
      </Container>
    </div>
  );
};

export default PlexSvr;
