import React, { useState } from 'react';

const DoughnutChart = ({ assets }) => {
  const [hoveredAsset, setHoveredAsset] = useState(null);

  // Sort by allocation and group smaller assets into "Others"
  const sorted = [...assets].sort((a, b) => b.allocation - a.allocation);
  const topAssets = sorted.slice(0, 5);
  const otherAllocation = sorted.slice(5).reduce((acc, curr) => acc + curr.allocation, 0);

  const chartData = [...topAssets];
  if (otherAllocation > 0) {
    chartData.push({ symbol: 'Others', allocation: otherAllocation, name: 'Other Assets' });
  }

  const PALETTE = ['#F7931A', '#627EEA', '#00df9a', '#E84142', '#2775CA', '#F0B90B', '#8C8C8C', '#A020F0'];

  const dataWithColors = chartData.map((item, index) => ({
    ...item,
    color: PALETTE[index % PALETTE.length]
  }));

  // Math for SVG arcs
  let cumulativePercent = 0;
  const getCoordinatesForPercent = (percent) => {
    const x = Math.cos(2 * Math.PI * percent);
    const y = Math.sin(2 * Math.PI * percent);
    return [x, y];
  };

  const slices = dataWithColors.map((asset) => {
    const start = cumulativePercent;
    const end = cumulativePercent + (asset.allocation / 100);
    cumulativePercent = end;

    const [startX, startY] = getCoordinatesForPercent(start);
    const [endX, endY] = getCoordinatesForPercent(end);
    const largeArcFlag = asset.allocation > 50 ? 1 : 0;
    
    // Handle 100% allocation case (full circle)
    const pathData = asset.allocation >= 100 
      ? `M 1 0 A 1 1 0 1 1 -1 0 A 1 1 0 1 1 1 0`
      : `M ${startX} ${startY} A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY} L 0 0`;

    return { ...asset, pathData };
  });

  const activeSlice = hoveredAsset || dataWithColors[0] || { symbol: '-', allocation: 0 };

  return (
    <div className="chart-wrapper">
       <div className="chart-inner">
          <svg viewBox="-1.1 -1.1 2.2 2.2" style={{transform: 'rotate(-90deg)'}}>
            {slices.map((slice, i) => (
              <path 
                key={i} 
                d={slice.pathData} 
                fill={slice.color} 
                stroke="var(--input-bg)" 
                strokeWidth="0.04" 
                onMouseEnter={() => setHoveredAsset(slice)}
                onMouseLeave={() => setHoveredAsset(null)}
                className="chart-slice"
                style={{ opacity: hoveredAsset && hoveredAsset.symbol !== slice.symbol ? 0.3 : 1 }}
              />
            ))}
            {/* Center Hole to make it a Doughnut */}
            <circle cx="0" cy="0" r="0.82" fill="var(--input-bg)" pointerEvents="none" />
          </svg>
          
          <div className="chart-center-text">
             <span className="chart-label">{hoveredAsset ? 'Allocation' : 'Top Asset'}</span>
             <span className="chart-value-lg" style={{color: activeSlice.color || 'var(--text-primary)'}}>
                 {activeSlice.symbol}
             </span>
             <span className="chart-label">{activeSlice.allocation.toFixed(1)}%</span>
          </div>
       </div>

       <div className="chart-legend">
          {dataWithColors.map((item, i) => (
             <div 
                key={i} 
                className="legend-item" 
                onMouseEnter={() => setHoveredAsset(item)}
                onMouseLeave={() => setHoveredAsset(null)}
                style={{opacity: hoveredAsset && hoveredAsset.symbol !== item.symbol ? 0.3 : 1}}
             >
                <div className="legend-left">
                    <span className="legend-dot" style={{background: item.color}}></span>
                    <span className="legend-text">{item.symbol}</span>
                </div>
                <span className="legend-percent">{item.allocation.toFixed(1)}%</span>
             </div>
          ))}
       </div>
    </div>
  );
};

export default DoughnutChart;