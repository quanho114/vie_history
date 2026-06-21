/**
 * GraphView3D - Three.js WebGL 3D Graph Renderer
 * Features: 3D visualization, orbit controls, depth-based effects
 */

import React, { useRef, useMemo, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Html, Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';
import { useGraphStore, getNodeColor, type GraphNode, type GraphEdge } from './graphStore';

// ============================================================================
// 3D Node Component
// ============================================================================

interface NodeMeshProps {
  node: GraphNode;
  position: [number, number, number];
  isSelected: boolean;
  isHovered: boolean;
  isConnected: boolean;
  onClick: () => void;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
}

function NodeMesh({
  node,
  position,
  isSelected,
  isHovered,
  isConnected,
  onClick,
  onPointerEnter,
  onPointerLeave,
}: NodeMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const color = getNodeColor(node.type);

  // Scale based on state
  const targetScale = isSelected ? 1.4 : isHovered ? 1.2 : 1;
  
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.scale.lerp(
        new THREE.Vector3(targetScale, targetScale, targetScale),
        0.15
      );
    }
  });

  // Opacity based on connection state
  const opacity = isConnected || isSelected ? 1 : 0.25;

  return (
    <group position={position}>
      {/* Glow effect for selected */}
      {isSelected && (
        <Sphere args={[0.8, 16, 16]}>
          <meshBasicMaterial color={color} transparent opacity={0.2} />
        </Sphere>
      )}

      {/* Main sphere */}
      <Sphere
        ref={meshRef}
        args={[0.5, 24, 24]}
        onClick={onClick}
        onPointerEnter={onPointerEnter}
        onPointerLeave={onPointerLeave}
      >
        <meshStandardMaterial
          color={color}
          metalness={0.3}
          roughness={0.6}
          transparent
          opacity={opacity}
        />
      </Sphere>

      {/* Label */}
      {(isSelected || isHovered) && (
        <Html center distanceFactor={15} style={{ pointerEvents: 'none' }}>
          <div
            style={{
              background: 'rgba(255,255,255,0.95)',
              padding: '4px 8px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 600,
              color: '#2d2a26',
              whiteSpace: 'nowrap',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              border: isSelected ? '2px solid #e05640' : '1px solid #e7e1d8',
            }}
          >
            {node.name.length > 20 ? node.name.slice(0, 18) + '...' : node.name}
          </div>
        </Html>
      )}
    </group>
  );
}

// ============================================================================
// 3D Edge Component
// ============================================================================

interface EdgeLineProps {
  edge: GraphEdge;
  sourcePos: THREE.Vector3;
  targetPos: THREE.Vector3;
  isHighlighted: boolean;
}

function EdgeLine({ edge, sourcePos, targetPos, isHighlighted }: EdgeLineProps) {
  const points = useMemo(() => {
    return [sourcePos, targetPos];
  }, [sourcePos, targetPos]);

  return (
    <Line
      points={points}
      color={isHighlighted ? '#e05640' : '#d0cbc4'}
      lineWidth={isHighlighted ? 2 : 1}
      transparent
      opacity={isHighlighted ? 0.8 : 0.4}
    />
  );
}

// ============================================================================
// Main Graph Scene
// ============================================================================

function GraphScene() {
  const {
    nodes,
    edges,
    selectedNodeId,
    hoveredNodeId,
    setSelectedNodeId,
    setHoveredNodeId,
    getConnectedNodeIds,
  } = useGraphStore();

  const connectedIds = selectedNodeId ? getConnectedNodeIds(selectedNodeId) : new Set<string>();

  // Center and scale metrics to adapt raw pixel values to Three.js coordinates
  const { centerX, centerY, maxR, targetRadius } = useMemo(() => {
    if (nodes.length === 0) return { centerX: 0, centerY: 0, maxR: 1, targetRadius: 18 };
    
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(n => {
      minX = Math.min(minX, n.x);
      maxX = Math.max(maxX, n.x);
      minY = Math.min(minY, n.y);
      maxY = Math.max(maxY, n.y);
    });

    const cX = (minX + maxX) / 2;
    const cY = (minY + maxY) / 2;

    // Calculate maximum radius in 2D space
    let mR = 1;
    nodes.forEach(n => {
      const dx = n.x - cX;
      const dy = n.y - cY;
      const r = Math.sqrt(dx * dx + dy * dy);
      if (r > mR) mR = r;
    });

    return { centerX: cX, centerY: cY, maxR: mR, targetRadius: 16 };
  }, [nodes]);

  // Stable, deterministic mapping from 2D coordinates to 3D Sphere Constellation
  const getNode3DPosition = useCallback((node: GraphNode, index: number): THREE.Vector3 => {
    const dx = node.x - centerX;
    const dy = node.y - centerY;
    const theta = Math.atan2(dy, dx);
    const r = Math.sqrt(dx * dx + dy * dy);
    
    // Polar angle phi maps 2D radius to 3D latitude (0 is North Pole, PI is South Pole)
    const phi = (r / maxR) * Math.PI * 0.9;
    
    // Add deterministic depth layers based on node index to make the sphere feel rich and voluminous
    const depthLayer = 0.85 + (index % 4) * 0.1; 
    const R = targetRadius * depthLayer;

    // Calculate spherical coordinates
    const x3d = R * Math.sin(phi) * Math.cos(theta);
    const y3d = R * Math.cos(phi); // Elevates nodes in the Y axis!
    const z3d = R * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x3d, y3d, z3d);
  }, [centerX, centerY, maxR, targetRadius]);

  // Create node map for quick lookup
  const nodeMap = useMemo(() => {
    return new Map(nodes.map(n => [n.id, n]));
  }, [nodes]);

  // Get normalized 3D position for a node ID
  const getNodePosition = useCallback((nodeId: string): THREE.Vector3 => {
    const nodeIndex = nodes.findIndex(n => n.id === nodeId);
    const node = nodeMap.get(nodeId);
    if (!node || nodeIndex === -1) return new THREE.Vector3(0, 0, 0);
    return getNode3DPosition(node, nodeIndex);
  }, [nodeMap, nodes, getNode3DPosition]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, 10, -10]} intensity={0.4} />

      {/* Grid helper positioned below the sphere */}
      <gridHelper args={[100, 20, '#e7e1d8', '#f5f1ea']} position={[0, -22, 0]} />

      {/* Edges */}
      {edges.map(edge => {
        const source = nodeMap.get(edge.source);
        const target = nodeMap.get(edge.target);
        if (!source || !target) return null;

        const isHighlighted = selectedNodeId === edge.source || selectedNodeId === edge.target;
        const sourcePos = getNodePosition(edge.source);
        const targetPos = getNodePosition(edge.target);

        return (
          <EdgeLine
            key={edge.id}
            edge={edge}
            sourcePos={sourcePos}
            targetPos={targetPos}
            isHighlighted={isHighlighted}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node, index) => {
        const pos = getNode3DPosition(node, index);
        return (
          <NodeMesh
            key={node.id}
            node={node}
            position={[pos.x, pos.y, pos.z]}
            isSelected={selectedNodeId === node.id}
            isHovered={hoveredNodeId === node.id}
            isConnected={connectedIds.has(node.id)}
            onClick={() => setSelectedNodeId(node.id)}
            onPointerEnter={() => setHoveredNodeId(node.id)}
            onPointerLeave={() => setHoveredNodeId(null)}
          />
        );
      })}

      {/* Camera controls */}
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        minDistance={5}
        maxDistance={100}
        autoRotate={false}
        autoRotateSpeed={0.5}
      />
    </>
  );
}

// ============================================================================
// Main Component
// ============================================================================

interface GraphView3DProps {
  width: number;
  height: number;
}

export function GraphView3D({ width, height }: GraphView3DProps) {
  const { nodes, loading } = useGraphStore();

  if (nodes.length === 0) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center bg-[#FAF9F5]"
      >
        <p className="text-[#8a8175]">Không có dữ liệu</p>
      </div>
    );
  }

  return (
    <div style={{ width, height }} className="relative">
      {/* Loading indicator */}
      {loading && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-white/90 px-4 py-2 rounded-xl shadow-lg">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-stone-200 border-t-[var(--coral)] rounded-full animate-spin" />
            <span className="text-xs text-[#6f675d]">Đang tải 3D...</span>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="absolute bottom-4 left-4 z-10 bg-white/90 px-3 py-2 rounded-xl shadow-lg">
        <p className="text-[10px] text-[#8a8175]">
          <span className="font-semibold">Kéo</span> để xoay | <span className="font-semibold">Cuộn</span> để zoom | <span className="font-semibold">Click</span> để chọn
        </p>
      </div>

      <Canvas
        camera={{ position: [0, 30, 30], fov: 60 }}
        style={{ background: 'linear-gradient(180deg, #FAF9F5 0%, #f5f1ea 100%)' }}
        gl={{ antialias: true, alpha: true }}
      >
        <GraphScene />
      </Canvas>
    </div>
  );
}
