import React, { useEffect, useState } from "react";
import BatteryGauge from "react-battery-gauge";
import HomePage from './HomePage.svg';
import SVGDiagram from "../page-power/SVGDiagram";
import { fetchFromServer } from '../utils/api';
import Gauge from '../components/gauge1'



function Home() {
  let [data, setData] = useState({});
  
  const getData = () => {
    fetchFromServer('/data/home')
      .then(function (myJson) {
        setData(myJson)
      })
      .catch(function (error) {
        console.error('Error fetching data:', error);
        // Set some default data so the page doesn't crash
        setData({
          var17: 'N/A',
          var18: 'N/A', 
          var13: 'N/A',
          var14: 'N/A',
          battery_percent: 0
        });
      });
  }


  useEffect(() => {
    const interval = setInterval(() => {
      getData();

    }, 1000);  // 1000 ms = 1 second
    return () => clearInterval(interval);
  }, [])

  return (

    <div className="Home">
      <SVGDiagram
        filename={HomePage}
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
        var13={data.var13}
        var14={data.var14}
        var15={data.var15}
        var16={data.var16}
        var17={data.var17}
        var18={data.var18}
        var19={data.var19}
        var20={data.var20}

      >
      <div id ="battery">
        <BatteryGauge
          value={data.battery_percent}
          size={150}
          padding={5}
          aspectRatio={0.5}
        />
      </div>
    <div id="first_gauge">
      <Gauge value={data.var17} label={"Fresh"} id="fresh" startColor="#24E9EF" endColor="24E9EF"/>
    </div>
    <div id="second_gauge">
      <Gauge value={data.var18} label={"Propane"} id="propane" startColor="#FF0000" endColor="FF0000"/>
    </div>

    <div id="third_gauge">
      <Gauge value={data.var13} label="Gray" id="gray" startColor="#484848" endColor="484848"/>
    </div>
    <div id="fourth_gauge">
      <Gauge value={data.var14} label="Black" id="black" startColor="#000000" endColor="000000"/>
    </div>

      </SVGDiagram>
    </div>
  )
}

export default Home;
