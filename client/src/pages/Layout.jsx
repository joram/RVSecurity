import React, { useEffect } from 'react';
import { Outlet, Link } from "react-router-dom";
import {Button, Menu} from "semantic-ui-react";
import { useState } from 'react';
import {IPADDR, PORT} from '../constants';


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
  let url = 'http://'.concat(IPADDR,':',PORT,'/api/alarms')
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
    let url = 'http://'.concat(IPADDR,':',PORT,'/api/alarms')
    fetch(url, {
      method: "GET",
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
    })
    .then(response => response.json())
    .then(data => {
      // console.log(data);
      setBikeAlarmState(data.bike);
      setInteriorAlarmState(data.interior);
    })
  
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
          <Menu.Item as={Link} to="/contact">Contact</Menu.Item>
          <Menu.Item as={TogglableButton} onClick={ToggleBikeAlarm} state={bikeAlarmState} text="Bike Alarm" activeColor="blue"></Menu.Item>
          <Menu.Item as={TogglableButton} onClick={ToggleInteriorAlarm} state={interiorAlarmState} text="Interior Alarm" activeColor="red"></Menu.Item>
      </Menu>
      <Outlet />
    </div>
    
    
  )
};

export default Layout;
