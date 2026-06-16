/**
 * MiniMap - Overview minimap for graph navigation
 */

import React, { useRef, useEffect, useCallback } from 'react';
import { useGraphStore, getNodeColor } from './graphStore';

interface MiniMapProps {
  width?: number;
  height?: number;
}

export function MiniMap({ width = 160, height = 120 }: MiniMapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const {
    nodes,
    transform,
    setTransform,
    selectedNodeId,
  } = useGraphStore();

  // Calculate bounds
  const bounds = React.useMemo(() => {
    if (nodes.length === 0) return { minX: 0, maxX: 800, minY: 0, maxY: 600 };
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(node => {
      minX = Math.min(minX, node.x);
      maxX = Math.max(maxX, node.x);
      minY = Math.min(minY, node.y);
      maxY = Math.max(maxY, node.y);
    });
    
    // Add padding
    const padX = (maxX - minX) * 0.1 || 50;
    const padY = (maxY - minY) * 0.1 || 50;
    return {
      minX: minX - padX,
      maxX: maxX + padX,
      minY: minY - padY,
      maxY: maxY + padY,
    };
  }, [nodes]);

  // Draw minimap
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    const graphWidth = bounds.maxX - bounds.minX;
    const graphHeight = bounds.maxY - bounds.minY;
    const scaleX = width / graphWidth;
    const scaleY = height / graphHeight;
    const scale = Math.min(scaleX, scaleY);

    // Center offset
    const offsetX = (width - graphWidth * scale) / 2;
    const offsetY = (height - graphHeight * scale) / 2;

    // Background
    ctx.fillStyle = '#faf9f5';
    ctx.fillRect(0, 0, width, height);

    // Draw nodes
    nodes.forEach(node => {
      const x = offsetX + (node.x - bounds.minX) * scale;
      const y = offsetY + (node.y - bounds.minY) * scale;
      const size = Math.max(2, (node.degree + 1) * 0.5);
      
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fillStyle = node.id === selectedNodeId 
        ? '#e05640' 
        : getNodeColor(node.type);
      ctx.fill();
    });

    // Draw viewport rectangle
    const viewportWidth = window.innerWidth / transform.scale;
    const viewportHeight = window.innerHeight / transform.scale;
    const viewportX = offsetX + (-transform.x / transform.scale - bounds.minX) * scale;
    const viewportY = offsetY + (-transform.y / transform.scale - bounds.minY) * scale;
    
    ctx.strokeStyle = '#e05640';
    ctx.lineWidth = 1.5;
    ctx.strokeRect(
      viewportX,
      viewportY,
      viewportWidth * scale,
      viewportHeight * scale
    );
  }, [nodes, transform, bounds, width, height, selectedNodeId]);

  // Handle click to navigate
  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const graphWidth = bounds.maxX - bounds.minX;
    const graphHeight = bounds.maxY - bounds.minY;
    const scaleX = width / graphWidth;
    const scaleY = height / graphHeight;
    const scale = Math.min(scaleX, scaleY);

    const offsetX = (width - graphWidth * scale) / 2;
    const offsetY = (height - graphHeight * scale) / 2;

    const graphX = (clickX - offsetX) / scale + bounds.minX;
    const graphY = (clickY - offsetY) / scale + bounds.minY;

    // Center viewport on clicked position
    const newX = -graphX * transform.scale + window.innerWidth / 2;
    const newY = -graphY * transform.scale + window.innerHeight / 2;

    setTransform({ x: newX, y: newY });
  }, [bounds, width, height, transform.scale, setTransform]);

  if (nodes.length === 0) return null;

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20">
      <div className="bg-white/95 backdrop-blur-md border border-[#e7e1d8] rounded-xl shadow-lg overflow-hidden">
        <div className="px-3 py-2 border-b border-[#f0ebe3] bg-[#faf9f5]">
          <span className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">
            Tổng quan
          </span>
        </div>
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onClick={handleClick}
          className="cursor-pointer block"
        />
      </div>
    </div>
  );
}
