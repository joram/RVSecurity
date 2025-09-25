import React from 'react';
import { Header, Icon } from 'semantic-ui-react';
import './WiFi.css';

const WiFi = () => {
  return (
    <div className="wifi-page">
      <Header as="h1" icon textAlign="center">
        <Icon name="tv" />
        <Header.Content>
          TV Control
          <Header.Subheader>TV control functionality coming soon</Header.Subheader>
        </Header.Content>
      </Header>
    </div>
  );
};

export default WiFi;
