import React, { useEffect, useState } from "react";
import BatteryGauge from "react-battery-gauge";
import { fetchFromServer } from '../utils/api';
import Gauge from '../components/gauge1';
import './Home.css';

function Home() {
  let [data, setData] = useState({});

  const getData = () => {
    fetchFromServer('/data/home')
      .then(function (myJson) {
        setData(myJson);
      })
      .catch(function (error) {
        console.error('Error fetching data:', error);
        setData({
          var17: '0', var18: '0', var13: '0', var14: '0',
          battery_percent: 0
        });
      });
  };

  useEffect(() => {
    const interval = setInterval(getData, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="Home">
      <div className="home-wrapper">

        {/* ── Header bar ─────────────────────────── */}
        <div className="home-header">
          <span className="home-title">RV Status</span>
          <span className="home-time">{data.var20}</span>
        </div>

        {/* ── Main grid ──────────────────────────── */}
        <div className="home-grid">

          {/* ── Battery card ───────────────────── */}
          <div className="home-card home-card--battery">
            <div className="card-title">Battery</div>
            <div className="battery-body">
              <div className="battery-stats">
                <div className="stat-row">
                  <span className="stat-label">Voltage</span>
                  <span className="stat-value">{data.var7}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Power</span>
                  <span className="stat-value">{data.var19}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Remaining</span>
                  <span className="stat-value">{data.var15}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Status</span>
                  <span className="stat-value">{data.var16}</span>
                </div>
              </div>
              <div className="battery-widget">
                <BatteryGauge
                  value={data.battery_percent || 0}
                  size={110}
                  padding={4}
                  aspectRatio={0.5}
                />
              </div>
            </div>
          </div>

          {/* ── Power card ─────────────────────── */}
          <div className="home-card home-card--power">
            <div className="card-title">Power</div>
            <div className="power-row">
              <div className="power-item power-item--solar">
                <div className="power-item-header">
                  <span className="power-icon">☀️</span>
                  <span className="power-label">Solar</span>
                </div>
                <div className="power-value">{data.var5}</div>
              </div>
              <div className="power-item power-item--ac">
                <div className="power-item-header">
                  <span className="power-icon">🔌</span>
                  <span className="power-label">AC Coach</span>
                </div>
                <div className="power-value">{data.var12}</div>
              </div>
              <div className="power-item power-item--dc">
                <div className="power-item-header">
                  <span className="power-icon">⚡</span>
                  <span className="power-label">DC Load</span>
                </div>
                <div className="power-value">{data.var8}</div>
              </div>
            </div>
          </div>

          {/* ── Tanks card ─────────────────────── */}
          <div className="home-card home-card--tanks">
            <div className="card-title">Tanks</div>
            <div className="tanks-grid">
              <Gauge value={data.var17} label="Fresh"   id="fresh"   startColor="#24E9EF" endColor="#24E9EF" radius={50}/>
              <Gauge value={data.var18} label="Propane" id="propane" startColor="#FF8C00" endColor="#FF8C00" radius={50}/>
              <Gauge value={data.var13} label="Gray"    id="gray"    startColor="#888888" endColor="#888888" radius={50}/>
              <Gauge value={data.var14} label="Black"   id="black"   startColor="#333333" endColor="#333333" radius={50}/>
            </div>
          </div>

          {/* ── Tires card ─────────────────────── */}
          <div className="home-card home-card--tires">
            <div className="card-title">Tire Pressure</div>
            <div className="tire-diagram">
              <div className="tire-axle-label">Front</div>
              <div className="tire-axle">
                <div className="tire">
                  <div className="tire-label">LF</div>
                  <div className="tire-value">{data.var9}</div>
                </div>
                <div className="tire-chassis"/>
                <div className="tire">
                  <div className="tire-label">RF</div>
                  <div className="tire-value">{data.var10}</div>
                </div>
              </div>
              <div className="tire-axle-label">Rear</div>
              <div className="tire-axle">
                <div className="tire">
                  <div className="tire-label">LR Out</div>
                  <div className="tire-value">{data.var1}</div>
                </div>
                <div className="tire tire--inner">
                  <div className="tire-label">LR In</div>
                  <div className="tire-value">{data.var2}</div>
                </div>
                <div className="tire-chassis"/>
                <div className="tire tire--inner">
                  <div className="tire-label">RR In</div>
                  <div className="tire-value">{data.var3}</div>
                </div>
                <div className="tire">
                  <div className="tire-label">RR Out</div>
                  <div className="tire-value">{data.var4}</div>
                </div>
              </div>
            </div>
          </div>

        </div> {/* end home-grid */}
      </div>   {/* end home-wrapper */}
    </div>
  );
}

export default Home;

