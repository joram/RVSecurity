import React from "react";
import './App.css';
import {Button} from "semantic-ui-react";

function doActionOnServer(){
    console.log("button push")
    fetch('http://localhost:8000/action1', {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
          msg: "Hey Tom!"
      })
    }).then(response => {
        return response.json()
    }).then(data => {
        console.log("got from server: ", data)
    })



}

function App() {
  return (
    <div className="App">
      <header className="App-header">
      <Button onClick={doActionOnServer}>Press Me NOw</Button>
      <Button onClick={doActionOnServer}>Press Me NOw 2</Button>
      </header>
    </div>
  )
}

export default App;
