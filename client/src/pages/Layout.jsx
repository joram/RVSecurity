import React, { useEffect } from 'react';
import { Outlet, Link } from "react-router-dom";
import {Button, Menu} from "semantic-ui-react";
import { useState } from 'react';
import { fetchFromServer, getServerUrl } from '../utils/api';


function TogglableButton(props) {
  let { text, activeColor, state, onClick } = props;
  const [active, setActive] = useState(false)
  function handleClick(){
    console.log("Button clicked: " + text);
    setActive((active) => !active);
    onClick(!active);
  }
  useEffect(() => {
    setActive(state);
  }, [state])

  let color = "grey";
  if (active) {
    color = activeColor;
  }
 
  return (
    <Button toggle color={color} onClick={handleClick}>
      {text}
    </Button>
  )

}
function tellServerAlarmStateChanged(state, alarmName){
  console.log("Alarm state changed: " + state + " " + alarmName)
  let url = `${getServerUrl()}/api/alarmpost`;
  fetch(url, {
    method: "POST",
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    },
    body: JSON.stringify({
      "state": state,
      "alarm": alarmName,
    })
  })

}

function ToggleBikeAlarm(active) {
  console.log("Bike alarm is now " + active);
  tellServerAlarmStateChanged(active, "bike");
}

function ToggleInteriorAlarm(active) {
  console.log("Interior alarm is now " + active);
  tellServerAlarmStateChanged(active, "interior");
}

function Layout() {
  let [bikeAlarmState, setBikeAlarmState] = useState(false);
  let [interiorAlarmState, setInteriorAlarmState] = useState(false);

  function getAlarmStatesFromServer(){
    fetchFromServer('/api/alarmget')
    .then(data => {
      // console.log(data);
      setBikeAlarmState(data.bike);
      setInteriorAlarmState(data.interior);
    })
    .catch(error => {
      console.error('Error fetching alarm states:', error);
    });
  }

  useEffect(() => {
    getAlarmStatesFromServer();
    const interval = setInterval(() => {
      getAlarmStatesFromServer();
    }, 5000);  // 1000 ms = 1 second
    return () => clearInterval(interval);
  }, [])

  return (
    <div>
      <Menu>
          <Menu.Item as={Link} to="/">Home</Menu.Item>
          <Menu.Item as={Link} to="/power">Power</Menu.Item>
          <Menu.Item as={Link} to="/internet">Internet</Menu.Item>
          <Menu.Item as={Link} to="/wifi">TV</Menu.Item>
          <Menu.Item as={TogglableButton} onClick={ToggleBikeAlarm} state={bikeAlarmState} text="Bike Alarm" activeColor="blue"></Menu.Item>
          <Menu.Item as={TogglableButton} onClick={ToggleInteriorAlarm} state={interiorAlarmState} text="Interior Alarm" activeColor="red"></Menu.Item>
      </Menu>
      <Outlet />
    </div>
    
    
  )
};

export default Layout;
