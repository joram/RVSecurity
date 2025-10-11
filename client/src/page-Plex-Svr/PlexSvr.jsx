import React, { useState } from 'react';
import { Header, Icon, Form, Radio, Container, Segment } from 'semantic-ui-react';
import './PlexSvr.css';

const PlexSvr = () => {
  const [selectedOption, setSelectedOption] = useState('');

  const handleChange = (e, { value }) => setSelectedOption(value);

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
                label='On for 2 hours'
                name='plexServerOption'
                value='2hours'
                checked={selectedOption === '2hours'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 3 hours'
                name='plexServerOption'
                value='3hours'
                checked={selectedOption === '3hours'}
                onChange={handleChange}
              />
            </Form.Field>
            <Form.Field>
              <Radio
                label='On for 4 hours'
                name='plexServerOption'
                value='4hours'
                checked={selectedOption === '4hours'}
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
