/**
 * GraphView2D - Canvas-based 2D Graph Renderer
 * Features: Force-directed physics, zoom/pan, node/edge rendering
 */

import React, { useRef, useEffect, useCallback, useMemo, useState } from 'react';
import { useGraphStore, type GraphNode, type GraphEdge, getNodeColor } from './graphStore';

interface GraphView2DProps {
  width: number;
  height: number;
}

export function GraphView2D({ width, height }: GraphView2DProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const isDraggingRef = useRef(false);
  const draggedNodeIdRef = useRef<string | null>(null);
  const lastMouseRef = useRef({ x: 0, y: 0 });
  
  // Use local ref for physics positions (avoids re-renders entirely!)
  const [simulationTrigger, setSimulationTrigger] = useState(0);
  const physicsNodesRef = useRef<GraphNode[]>([]);

  const {
    nodes,
    edges,
    transform,
    setTransform,
    selectedNodeId,
    setSelectedNodeId,
    hoveredNodeId,
    setHoveredNodeId,
    hoveredEdgeIndex,
    setHoveredEdgeIndex,
    physics,
    settings,
    graphMode,
    getConnectedNodeIds,
    updateNodePosition,
    pinNode,
    setNodes,
  } = useGraphStore();

  // Sync nodes from store to local physics ref
  useEffect(() => {
    if (nodes.length > 0) {
      const needsSync = physicsNodesRef.current.length === 0 || 
                        nodes.length !== physicsNodesRef.current.length || 
                        nodes.some((n, idx) => !physicsNodesRef.current[idx] || physicsNodesRef.current[idx].id !== n.id);
      
      if (needsSync) {
        physicsNodesRef.current = nodes.map(n => {
          const existing = physicsNodesRef.current.find(ex => ex.id === n.id);
          return existing ? { ...n, x: existing.x, y: existing.y, vx: existing.vx, vy: existing.vy } : { ...n };
        });
        setSimulationTrigger(prev => prev + 1);
      }
    }
  }, [nodes]);

  // Get node at position (reads from Ref for absolute real-time accuracy)
  const getNodeAtPosition = useCallback((screenX: number, screenY: number): GraphNode | null => {
    const { x: tx, y: ty, scale } = transform;
    const graphX = (screenX - tx) / scale;
    const graphY = (screenY - ty) / scale;
    const hitRadius = (settings.nodeSize + 8) / scale; // Slightly larger hitbox for better user interaction

    const currentNodes = physicsNodesRef.current.length > 0 ? physicsNodesRef.current : nodes;

    for (let i = currentNodes.length - 1; i >= 0; i--) {
      const node = currentNodes[i];
      const dx = node.x - graphX;
      const dy = node.y - graphY;
      if (dx * dx + dy * dy < hitRadius * hitRadius) {
        return node;
      }
    }
    return null;
  }, [nodes, transform, settings.nodeSize]);

  // Get edge at position (reads from Ref for absolute real-time accuracy)
  const getEdgeAtPosition = useCallback((screenX: number, screenY: number): number | null => {
    const { x: tx, y: ty, scale } = transform;
    const graphX = (screenX - tx) / scale;
    const graphY = (screenY - ty) / scale;
    const hitThreshold = 8 / scale;

    const currentNodes = physicsNodesRef.current.length > 0 ? physicsNodesRef.current : nodes;

    for (let i = 0; i < edges.length; i++) {
      const edge = edges[i];
      const source = currentNodes.find(n => n.id === edge.source);
      const target = currentNodes.find(n => n.id === edge.target);
      if (!source || !target) continue;

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const len2 = dx * dx + dy * dy;
      if (len2 === 0) continue;

      let t = ((graphX - source.x) * dx + (graphY - source.y) * dy) / len2;
      t = Math.max(0, Math.min(1, t));

      const projX = source.x + t * dx;
      const projY = source.y + t * dy;
      const dist = Math.sqrt((graphX - projX) ** 2 + (graphY - projY) ** 2);

      if (dist < hitThreshold) return i;
    }
    return null;
  }, [edges, nodes, transform]);

  // Helper to parse hex colors to rgba
  const hexToRgba = useCallback((hex: string, alpha: number) => {
    if (!hex.startsWith('#') || hex.length !== 7) return `rgba(180, 180, 180, ${alpha})`;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }, []);

  // Stable direct canvas draw function (Completely eliminates 60fps React re-renders!)
  const drawGraph = useCallback((ctx: CanvasRenderingContext2D, displayNodes: GraphNode[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const { x: tx, y: ty, scale } = transform;

    // Draw dot-grid background aligned with zoom & pan!
    const gridGap = 40; // spacing between dots in graph units
    const startX = Math.floor((-tx) / scale / gridGap) * gridGap - gridGap;
    const endX = startX + (width / scale) + gridGap * 2;
    const startY = Math.floor((-ty) / scale / gridGap) * gridGap - gridGap;
    const endY = startY + (height / scale) + gridGap * 2;

    ctx.fillStyle = 'rgba(180, 180, 180, 0.12)';
    for (let gx = startX; gx <= endX; gx += gridGap) {
      for (let gy = startY; gy <= endY; gy += gridGap) {
        ctx.beginPath();
        ctx.arc(gx, gy, 1.2 / Math.max(0.5, scale), 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.save();
    ctx.translate(tx, ty);
    ctx.scale(scale, scale);

    const connectedIds = selectedNodeId ? getConnectedNodeIds(selectedNodeId) : new Set<string>();
    const isFiltered = selectedNodeId !== null;

    // 1. Draw edges
    edges.forEach((edge, i) => {
      const source = displayNodes.find(n => n.id === edge.source);
      const target = displayNodes.find(n => n.id === edge.target);
      if (!source || !target) return;

      const isEdgeHovered = hoveredEdgeIndex === i;
      const isEdgeConnected = isFiltered && (edge.source === selectedNodeId || edge.target === selectedNodeId);

      let opacity = isFiltered ? (isEdgeConnected ? 0.85 : 0.08) : 0.35;
      let strokeWidth = settings.linkThickness;

      if (isEdgeHovered) {
        opacity = 0.95;
        strokeWidth = settings.linkThickness * 2;
      }

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 0.1) return;

      const sourceColorHex = getNodeColor(source.type);
      const targetColorHex = getNodeColor(target.type);

      // Gradient edge line
      let edgeStyle: string | CanvasGradient;
      if (isEdgeConnected || isEdgeHovered) {
        const gradient = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
        gradient.addColorStop(0, hexToRgba(sourceColorHex, opacity));
        gradient.addColorStop(1, hexToRgba(targetColorHex, opacity));
        edgeStyle = gradient;
      } else {
        edgeStyle = `rgba(180, 180, 180, ${opacity})`;
      }

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      
      if (settings.showArrows) {
        const targetRadius = (settings.nodeSize / 2) * (selectedNodeId === target.id ? 1.4 : 1.0) + 2;
        const endX = target.x - (dx / dist) * (targetRadius + 4);
        const endY = target.y - (dy / dist) * (targetRadius + 4);

        ctx.lineTo(endX, endY);
        
        // Draw wider glowing halo beneath active links
        if (isEdgeConnected || isEdgeHovered) {
          ctx.save();
          const glowGradient = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
          glowGradient.addColorStop(0, hexToRgba(sourceColorHex, opacity * 0.2));
          glowGradient.addColorStop(1, hexToRgba(targetColorHex, opacity * 0.2));
          ctx.strokeStyle = glowGradient;
          ctx.lineWidth = strokeWidth * 4;
          ctx.stroke();
          ctx.restore();
        }

        ctx.strokeStyle = edgeStyle;
        ctx.lineWidth = strokeWidth;
        ctx.stroke();

        // Arrowhead
        const angle = Math.atan2(dy, dx);
        const arrowSize = 6;
        ctx.beginPath();
        ctx.moveTo(endX, endY);
        ctx.lineTo(
          endX - arrowSize * Math.cos(angle - Math.PI / 6),
          endY - arrowSize * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
          endX - arrowSize * Math.cos(angle + Math.PI / 6),
          endY - arrowSize * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fillStyle = isEdgeConnected || isEdgeHovered ? hexToRgba(targetColorHex, opacity) : `rgba(180, 180, 180, ${opacity})`;
        ctx.fill();
      } else {
        ctx.lineTo(target.x, target.y);

        // Draw wider glowing halo beneath active links
        if (isEdgeConnected || isEdgeHovered) {
          ctx.save();
          const glowGradient = ctx.createLinearGradient(source.x, source.y, target.x, target.y);
          glowGradient.addColorStop(0, hexToRgba(sourceColorHex, opacity * 0.2));
          glowGradient.addColorStop(1, hexToRgba(targetColorHex, opacity * 0.2));
          ctx.strokeStyle = glowGradient;
          ctx.lineWidth = strokeWidth * 4;
          ctx.stroke();
          ctx.restore();
        }

        ctx.strokeStyle = edgeStyle;
        ctx.lineWidth = strokeWidth;
        ctx.stroke();
      }

      // Draw light particle flow along active edges
      if (isEdgeConnected || isEdgeHovered) {
        const time = (performance.now() * 0.0008) % 1;
        const particleCount = 1;
        ctx.fillStyle = hexToRgba(sourceColorHex, opacity * 0.95);
        for (let p = 0; p < particleCount; p++) {
          const t = (time + p / particleCount) % 1;
          const px = source.x + (target.x - source.x) * t;
          const py = source.y + (target.y - source.y) * t;
          ctx.beginPath();
          ctx.arc(px, py, 2.2 / scale, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    });

    // 2. Draw nodes
    displayNodes.forEach(node => {
      const color = getNodeColor(node.type);
      const isHovered = hoveredNodeId === node.id;
      const isSelected = selectedNodeId === node.id;
      const isConnected = isFiltered && connectedIds.has(node.id);

      let opacity = 1;
      let nodeScale = 1;

      if (isFiltered && !isConnected) {
        opacity = 0.15;
        nodeScale = 0.8;
      }

      if (isHovered) {
        nodeScale = 1.25;
      } else if (isSelected) {
        nodeScale = 1.35;
      }

      const radius = (settings.nodeSize / 2) * nodeScale;

      ctx.globalAlpha = opacity;

      // Outer glowing halo for selected or hovered node
      if (isSelected || isHovered) {
        const haloOpacity = isSelected ? 0.25 : 0.15;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 8, 0, Math.PI * 2);
        ctx.fillStyle = hexToRgba(color, haloOpacity);
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius + 4, 0, Math.PI * 2);
        ctx.fillStyle = hexToRgba(color, haloOpacity * 1.5);
        ctx.fill();
      }

      // Main node body with a subtle radial gradient (holographic/3D effect)
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      
      const radGrad = ctx.createRadialGradient(
        node.x - radius * 0.2, 
        node.y - radius * 0.2, 
        radius * 0.1, 
        node.x, 
        node.y, 
        radius
      );
      radGrad.addColorStop(0, '#ffffff'); // bright highlight
      radGrad.addColorStop(0.3, color);   // core color
      radGrad.addColorStop(1, hexToRgba(color, 0.85)); // darker edge
      ctx.fillStyle = radGrad;
      ctx.fill();

      // Border highlight for hover or select
      if (isHovered || isSelected) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = isSelected ? 2.0 : 1.2;
        ctx.stroke();
      }

      // Node text labels with beautiful rounded capsules
      if (settings.showLabels && (isSelected || isHovered || isConnected || scale > settings.labelThreshold)) {
        ctx.font = `${isSelected || isHovered ? 'bold ' : ''}10px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const labelText = node.name.length > 25 ? node.name.slice(0, 23) + '...' : node.name;
        const textWidth = ctx.measureText(labelText).width;
        
        const padX = 6;
        const padY = 3;
        const rectW = textWidth + padX * 2;
        const rectH = 10 + padY * 2;
        const rectX = node.x - rectW / 2;
        const rectY = node.y + radius + 5;

        // Background capsule
        ctx.beginPath();
        if (typeof ctx.roundRect === 'function') {
          ctx.roundRect(rectX, rectY, rectW, rectH, 6);
        } else {
          ctx.rect(rectX, rectY, rectW, rectH);
        }
        
        if (isSelected) {
          ctx.fillStyle = '#cc785c';
          ctx.fill();
          ctx.fillStyle = '#ffffff';
        } else if (isHovered) {
          ctx.fillStyle = '#f5f1ea';
          ctx.fill();
          ctx.strokeStyle = '#cc785c';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.fillStyle = '#cc785c';
        } else {
          ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
          ctx.fill();
          ctx.strokeStyle = 'rgba(231, 225, 216, 0.85)';
          ctx.lineWidth = 1;
          ctx.stroke();
          ctx.fillStyle = '#4a4a4a';
        }

        ctx.fillText(labelText, node.x, rectY + padY);
      }

      ctx.globalAlpha = 1;
    });

    ctx.restore();
  }, [width, height, transform, selectedNodeId, hoveredNodeId, hoveredEdgeIndex, settings, edges, hexToRgba]);

  // Physics simulation loop (Runs directly on HTML5 canvas context for 60fps buttery performance)
  useEffect(() => {
    if (physicsNodesRef.current.length === 0 || graphMode === 'local') return;

    const { repulsion, attraction, restLength } = physics;
    const centerX = width / 2;
    const centerY = height / 2;

    // Stable over-damped first-order physics parameters (Obsidian style)
    const repStrength = repulsion * 1.5;   // Comfortable spatial spacing
    const attrStrength = attraction * 2.5; // Stiff springs
    const localGravity = 0.003;            // Weak central pull to avoid drag resistance

    const simulate = () => {
      // Create fresh working positions from ref
      const nextNodes = physicsNodesRef.current.map(n => ({ ...n }));
      const nodeMap = new Map(nextNodes.map(n => [n.id, n]));

      // Clear/carry over velocity (Carry over only 12% to guarantee monotonic convergence & prevent all recoil oscillation)
      nextNodes.forEach(node => {
        node.vx = (node.vx || 0) * 0.12;
        node.vy = (node.vy || 0) * 0.12;
      });

      // 1. Repulsion forces between nodes (Capped to prevent extreme explosive impulses)
      for (let i = 0; i < nextNodes.length; i++) {
        const nodeA = nextNodes[i];
        if (nodeA.isPinned && nodeA.id !== draggedNodeIdRef.current) continue;

        for (let j = 0; j < nextNodes.length; j++) {
          if (i === j) continue;
          const nodeB = nextNodes[j];

          const dx = nodeA.x - nodeB.x;
          const dy = nodeA.y - nodeB.y;
          const distSq = dx * dx + dy * dy + 100;
          const dist = Math.sqrt(distSq);

          if (dist < 280) {
            const force = Math.min(22, repStrength / distSq);
            nodeA.vx += (dx / dist) * force;
            nodeA.vy += (dy / dist) * force;
          }
        }
      }

      // 2. Attraction spring forces along edges (Stretches smoothly with capped force)
      edges.forEach(edge => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) return;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.1;
        
        // Balanced spring attraction
        const force = (dist - restLength) * attrStrength * 0.08 * (edge.weight || 1);

        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (!source.isPinned || source.id === draggedNodeIdRef.current) {
          source.vx += fx;
          source.vy += fy;
        }
        if (!target.isPinned || target.id === draggedNodeIdRef.current) {
          target.vx -= fx;
          target.vy -= fy;
        }
      });

      // 3. Central gravity + strict speed capping
      let totalEnergy = 0;
      nextNodes.forEach(node => {
        if (node.id === draggedNodeIdRef.current) {
          node.vx = 0;
          node.vy = 0;
          return;
        }

        if (node.isPinned) return;

        // Apply extremely weak central gravity force
        node.vx -= (node.x - centerX) * localGravity;
        node.vy -= (node.y - centerY) * localGravity;

        // Speed cap to prevent extreme velocities
        const currentSpeed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        const maxSpeed = 22;
        if (currentSpeed > maxSpeed) {
          node.vx = (node.vx / currentSpeed) * maxSpeed;
          node.vy = (node.vy / currentSpeed) * maxSpeed;
        }

        // Apply displacement directly (forces behave as velocity directly in this frame)
        node.x += node.vx;
        node.y += node.vy;

        totalEnergy += node.vx * node.vx + node.vy * node.vy;
      });

      // Commit updated nodes back to Ref
      physicsNodesRef.current = nextNodes;

      // Draw directly onto the HTML5 canvas context in the animation frame thread!
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          drawGraph(ctx, nextNodes);
        }
      }

      // If stable and not dragging, and no selected/hovered nodes (which require particle animation), pause animation loop to save CPU
      const latestState = useGraphStore.getState();
      if (!draggedNodeIdRef.current && totalEnergy < 0.008 && !latestState.selectedNodeId && !latestState.hoveredNodeId) {
        setNodes(nextNodes);
        animationRef.current = undefined;
        return;
      }

      animationRef.current = requestAnimationFrame(simulate);
    };

    animationRef.current = requestAnimationFrame(simulate);
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [edges.length, graphMode, physics, width, height, simulationTrigger, drawGraph]);

  // Static draw trigger when user transforms, hovers, or selects
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const displayNodes = physicsNodesRef.current.length > 0 ? physicsNodesRef.current : nodes;
    drawGraph(ctx, displayNodes);

    // Wake up physics simulation/animation loop if we have active interactions to run particle flow
    if (!animationRef.current && (selectedNodeId !== null || hoveredNodeId !== null)) {
      setSimulationTrigger(prev => prev + 1);
    }
  }, [nodes, edges, transform, selectedNodeId, hoveredNodeId, hoveredEdgeIndex, settings, drawGraph]);

  // Mouse handlers
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAtPosition(x, y);
    if (node) {
      draggedNodeIdRef.current = node.id;
      pinNode(node.id, true);
      isDraggingRef.current = true;
      lastMouseRef.current = { x, y };
    } else {
      isDraggingRef.current = true;
      lastMouseRef.current = { x, y };
    }
  }, [getNodeAtPosition]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isDraggingRef.current && draggedNodeIdRef.current) {
      const { x: tx, y: ty, scale } = transform;
      const graphX = (x - tx) / scale;
      const graphY = (y - ty) / scale;

      // Update Ref directly so the running requestAnimationFrame simulation closure receives it
      physicsNodesRef.current = physicsNodesRef.current.map(n => 
        n.id === draggedNodeIdRef.current 
          ? { ...n, x: graphX, y: graphY, vx: 0, vy: 0 }
          : n
      );
      
      // We do NOT update React state on mousemove. This avoids any component re-renders and delivers zero delay!
      // Redraw immediately on canvas for absolute real-time cursor tracking
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          drawGraph(ctx, physicsNodesRef.current);
        }
      }

      // Wake up physics simulation if it went to sleep
      if (!animationRef.current) {
        setSimulationTrigger(prev => prev + 1);
      }
    } else if (isDraggingRef.current) {
      const dx = x - lastMouseRef.current.x;
      const dy = y - lastMouseRef.current.y;
      setTransform({ x: transform.x + dx, y: transform.y + dy });
      lastMouseRef.current = { x, y };
    } else {
      const node = getNodeAtPosition(x, y);
      setHoveredNodeId(node?.id || null);

      if (!node) {
        const edgeIdx = getEdgeAtPosition(x, y);
        setHoveredEdgeIndex(edgeIdx);
      } else {
        setHoveredEdgeIndex(null);
      }
    }
  }, [transform, getNodeAtPosition, getEdgeAtPosition, setHoveredNodeId, setHoveredEdgeIndex, setTransform, setSimulationTrigger, drawGraph]);

  const handleMouseUp = useCallback(() => {
    if (draggedNodeIdRef.current) {
      pinNode(draggedNodeIdRef.current, false);
      
      // Persist the final position of the node in the global Zustand store exactly ONCE upon release!
      const finalNode = physicsNodesRef.current.find(n => n.id === draggedNodeIdRef.current);
      if (finalNode) {
        updateNodePosition(finalNode.id, finalNode.x, finalNode.y, 0, 0);
      }

      // Wake up simulation when letting go so it floats back naturally
      if (!animationRef.current) {
        setSimulationTrigger(prev => prev + 1);
      }
    }
    isDraggingRef.current = false;
    draggedNodeIdRef.current = null;
  }, [pinNode, updateNodePosition, setSimulationTrigger]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggedNodeIdRef.current) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const node = getNodeAtPosition(x, y);
    setSelectedNodeId(node?.id || null);
  }, [getNodeAtPosition, setSelectedNodeId]);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const delta = -e.deltaY * 0.001;
    const newScale = Math.max(0.2, Math.min(3, transform.scale * (1 + delta)));

    const scaleFactor = newScale / transform.scale;
    const newX = x - (x - transform.x) * scaleFactor;
    const newY = y - (y - transform.y) * scaleFactor;

    setTransform({ x: newX, y: newY, scale: newScale });
  }, [transform, setTransform]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="cursor-grab active:cursor-grabbing"
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
      onWheel={handleWheel}
      style={{ width, height }}
    />
  );
}
