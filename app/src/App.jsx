import React from "react";
import './App.css';
import Sophie from "./Sophie2.svg";
import SVGDiagram from "./SVGDiagram";

function App() {
    return (
        <div className="App">
            <SVGDiagram
                filename={Sophie}
                var1={"hello world"}
            />
        </div>
    )
}

export default App;
