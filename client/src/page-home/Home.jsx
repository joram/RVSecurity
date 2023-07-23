import React, { useEffect, useState } from "react";
import BatteryGauge from "react-battery-gauge";
import HomePage from './HomePage.svg';
import SVGDiagram from "../page-power/SVGDiagram";
import {IPADDR, PORT} from '../constants';
import GaugeTopDown from '../components/gauge1'
import GaugeBottomUp from "../components/gauge2";



function Home() {
  let [data, setData] = useState({});
  const getData = () => {
    let url = 'http://'.concat(IPADDR,':',PORT,'/data/home')
    fetch(url
      , {
        method: "GET",
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
      }
    )
      .then(function (response) {
        return response.json();
      })
      .then(function (myJson) {
        setData(myJson)
      });
  }


  useEffect(() => {
    const interval = setInterval(() => {
      getData();

    }, 1000);  // 1000 ms = 1 second
    return () => clearInterval(interval);
  }, [])

  return (

    <div dsclassName="Home">
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
          aspectRatio={0.52}
        />
      </div>
      <div id="first_gauge">
          <GaugeTopDown value={30} label={"Fresh"} id="fresh" />
      </div>
      <div id="second_gauge">
          <GaugeTopDown value={80} label={"Propane"} id="propane" />
      </div>

      <div id="third_gauge">
          <GaugeBottomUp value={50} label="Gray" id="gray"/>
      </div>
      <div id="fourth_gauge">
          <GaugeBottomUp value={10} label="Black" id="black" />
      </div>

      </SVGDiagram>
    </div>
  )
}

export default Home;
