import React from "react";
import './Power.css';
import SVG from 'react-inlinesvg';


function SVGDiagram(props) {
    let {filename, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, 
        var11, var12, var13, var14, var15, var16, var17, var18, var19, var20,
        children } = props
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
        ["{var13}", var13],
        ["{var14}", var14],
        ["{var15}", var15],
        ["{var16}", var16],
        ["{var17}", var17],
        ["{var18}", var18],
        ["{var19}", var19],
        ["{var20}", var20],        
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

    return (
        <div className="base_svg">
            <SVG src={svg}/>
            {children}
        </div>
    )
}

export default SVGDiagram;
