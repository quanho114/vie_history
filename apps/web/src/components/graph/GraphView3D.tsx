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
  isSelected: boolean;
  isHovered: boolean;
  isConnected: boolean;
  onClick: () => void;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
}

function NodeMesh({
  node,
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
    <group position={[node.x, 0, node.y]}>
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

  // Create node map for quick lookup
  const nodeMap = useMemo(() => {
    return new Map(nodes.map(n => [n.id, n]));
  }, [nodes]);

  // Get 3D position for a node
  const getNodePosition = useCallback((nodeId: string): THREE.Vector3 => {
    const node = nodeMap.get(nodeId);
    if (!node) return new THREE.Vector3(0, 0, 0);
    return new THREE.Vector3(node.x, 0, node.y);
  }, [nodeMap]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.6} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, 10, -10]} intensity={0.4} />

      {/* Grid helper */}
      <gridHelper args={[100, 20, '#e7e1d8', '#f5f1ea']} position={[0, -0.1, 0]} />

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
      {nodes.map(node => (
        <NodeMesh
          key={node.id}
          node={node}
          isSelected={selectedNodeId === node.id}
          isHovered={hoveredNodeId === node.id}
          isConnected={connectedIds.has(node.id)}
          onClick={() => setSelectedNodeId(node.id)}
          onPointerEnter={() => setHoveredNodeId(node.id)}
          onPointerLeave={() => setHoveredNodeId(null)}
        />
      ))}

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
