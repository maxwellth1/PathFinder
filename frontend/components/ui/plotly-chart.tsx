"use client"

import React from 'react';
import dynamic from 'next/dynamic';
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface PlotlyChartProps {
  plotData: string;
}

interface PlotlyChart extends React.Component<PlotlyChartProps> {
  el: HTMLDivElement | null;
}

const PlotlyChart = React.forwardRef<PlotlyChart, PlotlyChartProps>(({ plotData }, ref) => {
  if (!plotData) {
    return null;
  }

  try {
    const plot = JSON.parse(plotData);
    // Customize layout for dark mode
    const style = getComputedStyle(document.documentElement);
    const backgroundColor = `hsl(${style.getPropertyValue('--background')})`;
    const foregroundColor = `hsl(${style.getPropertyValue('--foreground')})`;
    const mutedForegroundColor = `hsl(${style.getPropertyValue('--muted-foreground')})`;

    plot.layout = {
      ...plot.layout,
      paper_bgcolor: backgroundColor,
      plot_bgcolor: backgroundColor,
      font: {
        color: foregroundColor
      },
      xaxis: {
        ...plot.layout.xaxis,
        gridcolor: mutedForegroundColor
      },
      yaxis: {
        ...plot.layout.yaxis,
        gridcolor: mutedForegroundColor
      }
    };

    return (
      <Plot
        data={plot.data}
        layout={plot.layout}
        style={{ width: '100%', height: '100%' }}
        useResizeHandler={true}
        ref={ref}
      />
    );
  } catch (error) {
    console.error("Failed to parse or render plot data:", error);
    return null;
  }
});

export default PlotlyChart;