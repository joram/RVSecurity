import React from "react";
import './App.css';
import SVG from 'react-inlinesvg';


function SVGDiagram(props) {
    let {filename, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var11, var12} = props
    let [svgText, setSvgText] = React.useState( null);

    let replacements = [
        ["{var1}", var1],
        ["{var2}", var2],
        ["{var3}", var3],
        ["{var4}", var4],
        ["{var5}", var5],
        ["{var6}", var6],
        ["{var7}", var7],
        ["{var8}", var8],
        ["{var9}", var9],
        ["{var10}", var10],
        ["{var11}", var11],
        ["{var12}", var12],
    ]
    if(svgText=== null) {
        fetch(filename)
            .then(r => r.text())
            .then(text => {
                setSvgText(text)
            })
    }

    let svg = svgText
    if(svgText!== null) {
        replacements.forEach(([from, to]) => {
            svg = svg.replace(from, to);
        })
    }

    console.log(svg)
    return (
        <div className="App">
            <SVG src={svg}/>
        </div>
    )
}

export default SVGDiagram;
