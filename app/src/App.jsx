import React, { useState, useEffect } from "react";
import './App.css';
import {Button} from "semantic-ui-react";

function doActionOnServer(){
    console.log("button push")
    // the fetch stmt must change  localhost to proper Pi IP address
    fetch('http://localhost:8000/action1', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          msg: "Hey Tom! 1"
      })
    }).then(response => {
        return response.json()
    }).then(data => {
        console.log("got from server: ", data)
    })
}
function doActionOnServer2(){
  console.log("button push")
  // the fetch stmt must change  localhost to proper Pi IP address
  fetch('http://localhost:8000/action1', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        msg: "Hey Tom! 2"
    })
  }).then(response => {
      return response.json()
  }).then(data => {
      console.log("got from server: ", data)
  })
}

function StatusComponent(){
  let [message,setMessage]=useState("Tom")
  useEffect(() => {
    // Update the document title using the browser API
    fetch('http://localhost:8000/status', {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    }
      }).then(response => {
        return response.json()
        
      }).then(data=>{
        console.log(data)
        setMessage(JSON.stringify(data))
      })
  });
  return<>Hello World {message}</>
}

function App() {
  return (
    <div className="App">
      <header className="App-header">
      <Button onClick={doActionOnServer}>Press Me Now 1</Button>
      <Button onClick={doActionOnServer2}>Press Me Now 3</Button>
      <Button.Group>
        Alarm - 
        <Button>
          ON
        </Button>
        <Button>
          OFF
        </Button>
      </Button.Group>
      <StatusComponent></StatusComponent>
      </header>
    </div>
  )
}



export default App;
