import React, {useEffect, useState} from "react";
import './App.css';
import Sophie from "./Sophie2.svg";
import SVGDiagram from "./SVGDiagram";


function App() {
    let [data, setData] = useState({});
    const getData=()=>{
        fetch('http://localhost:8000/data'
        ,{
          headers : {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
           }
        }
        )
          .then(function(response){
            return response.json();
          })
          .then(function(myJson) {
            setData(myJson)
          });
  }

    useEffect(() => {
      const interval = setInterval(() => {
        getData();

      }, 300);
      return () => clearInterval(interval);
    }, [])

        console.log('Logs every 0.5s', data);
    return (
        <div className="App">
            <SVGDiagram
                filename={Sophie}
                var1={data.var1}
                var2={data.var2}
                var3={data.var3}
                var4={data.var4}
                var5={data.var5}
                var6={data.var6}
                var7={data.var7}
                var8={data.var8}
                var9={data.var9}
                var10={data.var10}
                var11={data.var11}
                var12={data.var12}
            />
        </div>
    )
}

export default App;
