/**
 * GraphPage - Main Knowledge Graph page with Obsidian-style interface
 * Features: 2D/3D modes, global/local views, filters, search
 */

import React, { useEffect, useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Box,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Command,
  Keyboard,
  Search,
} from 'lucide-react';
import { useGraphStore, type GraphNode, type GraphEdge } from '../components/graph/graphStore';
import { GraphView2D } from '../components/graph/GraphView2D';
import { GraphView3D } from '../components/graph/GraphView3D';
import { ControlPanel } from '../components/graph/ControlPanel';
import { NodePanel } from '../components/graph/NodePanel';
import { SearchOverlay } from '../components/graph/SearchOverlay';
import { MiniMap } from '../components/graph/MiniMap';
import { graphApi } from '@/lib/api/brain';

// ============================================================================
// Edge Labels (Vietnamese)
// ============================================================================

const EDGE_LABELS: Record<string, string> = {
  CAUSED_BY: 'gây ra',
  LED_TO: 'dẫn đến',
  LED_BY: 'do',
  PARTICIPATED_IN: 'tham gia',
  HAPPENED_AT: 'tại',
  HAPPENED_AFTER: 'sau',
  PART_OF: 'thuộc',
  RELATED_TO: 'liên quan',
  SIGNED_BY: 'ký bởi',
  OPPOSED: 'đối đầu',
  MENTIONED_IN: 'đề cập',
};

function getEdgeLabel(et: string): string {
  return EDGE_LABELS[et] || et.toLowerCase().replace(/_/g, ' ');
}

interface RawNode {
  id: string;
  name: string;
  slug?: string;
  type?: string;
  node_type?: string;
  description?: string;
}

interface RawEdge {
  id: string;
  source_id?: string;
  source?: string;
  target_id?: string;
  target?: string;
  edge_type?: string;
  weight?: number;
}

// ============================================================================
// Main Component
// ============================================================================

export function GraphPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const {
    nodes,
    setNodes,
    edges,
    setEdges,
    loading,
    setLoading,
    error,
    setError,
    graphMode,
    selectedNodeId,
    setSelectedNodeId,
    showSearchOverlay,
    toggleSearchOverlay,
    showNodePanel,
    toggleNodePanel,
    transform,
    setTransform,
    resetTransform,
    setGraphMode,
    localGraphDepth,
    viewMode,
    setViewMode,
  } = useGraphStore();

  // Update dimensions on resize
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Load graph data
  useEffect(() => {
    const loadGraph = async () => {
      setLoading(true);
      setError(null);

      try {
        // Fetch nodes
        const nodesRes = await graphApi.getNodes('');
        const rawNodes = (nodesRes.nodes || []) as unknown as RawNode[];

        // Fetch edges
        const edgesRes = await graphApi.getEdges(1, 500);
        const rawEdges = (edgesRes.edges || []) as unknown as RawEdge[];

        if (rawNodes.length === 0) {
          setNodes([]);
          setEdges([]);
          setLoading(false);
          return;
        }

        // Calculate degrees
        const degreeMap: Record<string, number> = {};
        rawEdges.forEach((e: RawEdge) => {
          const s = e.source_id || e.source || '';
          const t = e.target_id || e.target || '';
          degreeMap[s] = (degreeMap[s] || 0) + 1;
          degreeMap[t] = (degreeMap[t] || 0) + 1;
        });

        // Find most connected node as center
        let maxDegree = -1;
        let centralId = '';
        rawNodes.forEach((n: RawNode) => {
          const deg = degreeMap[n.id] || 0;
          if (deg > maxDegree) {
            maxDegree = deg;
            centralId = n.id;
          }
        });

        // Initialize nodes with positions (restore from localStorage if exists to avoid fly-in jitter on F5!)
        const centerX = dimensions.width / 2;
        const centerY = dimensions.height / 2;

        let savedPositions: Record<string, { x: number, y: number, isPinned?: boolean }> = {};
        try {
          const saved = localStorage.getItem('historiai-graph-node-positions');
          if (saved) {
            savedPositions = JSON.parse(saved);
          }
        } catch (err) {
          console.error('Failed to parse saved node positions:', err);
        }

        const graphNodes: GraphNode[] = rawNodes.map((n: RawNode, i: number) => {
          const isCentral = n.id === centralId;
          const savedPos = savedPositions[n.id];

          if (savedPos && typeof savedPos.x === 'number' && typeof savedPos.y === 'number') {
            return {
              id: n.id,
              slug: n.slug || n.id,
              name: n.name,
              type: n.type || n.node_type || 'concept',
              description: n.description,
              x: savedPos.x,
              y: savedPos.y,
              vx: 0,
              vy: 0,
              degree: degreeMap[n.id] || 0,
              isCenter: isCentral,
              isPinned: savedPos.isPinned || false,
            };
          }

          const angle = (i / rawNodes.length) * 2 * Math.PI;
          const radius = isCentral ? 0 : 60 + Math.random() * 180;

          return {
            id: n.id,
            slug: n.slug || n.id,
            name: n.name,
            type: n.type || n.node_type || 'concept',
            description: n.description,
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
            vx: 0,
            vy: 0,
            degree: degreeMap[n.id] || 0,
            isCenter: isCentral,
            isPinned: false,
          };
        });

        const graphEdges: GraphEdge[] = rawEdges.map((e: RawEdge) => ({
          id: e.id,
          source: e.source_id || e.source || '',
          target: e.target_id || e.target || '',
          label: getEdgeLabel(e.edge_type || ''),
          edge_type: e.edge_type || '',
          weight: e.weight || 1,
        }));

        setNodes(graphNodes);
        setEdges(graphEdges);
      } catch (e) {
        console.error('Failed to load graph:', e);
        setError('Lỗi tải bản đồ tri thức');
      } finally {
        setLoading(false);
      }
    };

    loadGraph();
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K for search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleSearchOverlay();
      }

      // Escape to close panels
      if (e.key === 'Escape') {
        if (showSearchOverlay) {
          toggleSearchOverlay();
        } else if (showNodePanel) {
          toggleNodePanel();
        } else if (selectedNodeId) {
          setSelectedNodeId(null);
        }
      }

      // G to toggle graph mode
      if (e.key === 'g' && !e.metaKey && !e.ctrlKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          setGraphMode(graphMode === 'global' ? 'local' : 'global');
        }
      }

      // F to fit view
      if (e.key === 'f' && !e.metaKey && !e.ctrlKey) {
        const target = e.target as HTMLElement;
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          handleFitView();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showSearchOverlay, showNodePanel, selectedNodeId, graphMode, toggleSearchOverlay, toggleNodePanel, setSelectedNodeId, setGraphMode]);

  // Fit view to content
  const handleFitView = useCallback(() => {
    if (nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    nodes.forEach(node => {
      minX = Math.min(minX, node.x);
      maxX = Math.max(maxX, node.x);
      minY = Math.min(minY, node.y);
      maxY = Math.max(maxY, node.y);
    });

    const graphWidth = maxX - minX + 100;
    const graphHeight = maxY - minY + 100;
    const scaleX = dimensions.width / graphWidth;
    const scaleY = dimensions.height / graphHeight;
    const scale = Math.min(scaleX, scaleY, 1.5);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    setTransform({
      x: dimensions.width / 2 - centerX * scale,
      y: dimensions.height / 2 - centerY * scale,
      scale,
    });
  }, [nodes, dimensions, setTransform]);

  // Navigate to node
  const handleNavigateToNode = useCallback((nodeId: string) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return;

    setTransform({
      x: dimensions.width / 2 - node.x * transform.scale,
      y: dimensions.height / 2 - node.y * transform.scale,
    });
  }, [nodes, dimensions, transform.scale, setTransform]);

  // Handle node selection from search
  const handleSelectFromSearch = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    handleNavigateToNode(nodeId);
  }, [setSelectedNodeId, handleNavigateToNode]);

  return (
    <div className="flex-1 flex overflow-hidden relative">

      {/* Background */}
      <div className="absolute inset-0 bg-[#FAF9F5]/45 bg-gradient-to-tr from-[#FAF9F5] via-white to-white" />

      {/* Graph Container */}
      <div ref={containerRef} className="flex-1 relative overflow-hidden">

        {/* Canvas Graph - 2D/3D Mode Toggle */}
        {nodes.length > 0 && (
          <AnimatePresence mode="wait">
            {viewMode === '2d' ? (
              <motion.div
                key="2d"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="absolute inset-0"
              >
                <GraphView2D width={dimensions.width} height={dimensions.height} />
              </motion.div>
            ) : (
              <motion.div
                key="3d"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="absolute inset-0"
              >
                <GraphView3D width={dimensions.width} height={dimensions.height} />
              </motion.div>
            )}
          </AnimatePresence>
        )}

        {/* Loading State */}
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 flex items-center justify-center bg-[#FAF9F5]/60 backdrop-blur-sm z-30"
          >
            <div className="bg-white/95 border border-[#e7e1d8] rounded-2xl p-6 shadow-lg text-center">
              <div className="w-10 h-10 border-2 border-stone-200 border-t-[var(--coral)] rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm font-semibold text-[#6f675d]">Đang khởi tạo bản đồ tri thức...</p>
            </div>
          </motion.div>
        )}

        {/* Error State */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 flex items-center justify-center z-30"
          >
            <div className="bg-red-50 text-red-700 px-6 py-4 rounded-2xl border border-red-200 text-sm text-center max-w-sm shadow-lg">
              {error}
            </div>
          </motion.div>
        )}

        {/* Empty State */}
        {!loading && !error && nodes.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute inset-0 flex items-center justify-center z-30"
          >
            <div className="text-center">
              <Box className="w-16 h-16 text-[#d0cbc4] mx-auto mb-4" />
              <h3 className="text-lg font-bold text-[#4a4a4a] mb-2">Chưa có dữ liệu đồ thị</h3>
              <p className="text-sm text-[#8a8175] max-w-xs">
                Hãy tạo wiki pages và chạy Brain Builder để tự động trích xuất tri thức.
              </p>
            </div>
          </motion.div>
        )}

        {/* Control Panel */}
        {nodes.length > 0 && (
          <ControlPanel onFitView={handleFitView} />
        )}

        {/* Node Panel */}
        <AnimatePresence>
          {showNodePanel && selectedNodeId && (
            <NodePanel
              onClose={() => setSelectedNodeId(null)}
              onNavigateToNode={handleNavigateToNode}
            />
          )}
        </AnimatePresence>


        {/* Unified Mini Toolbar (Search + Zoom Controls) */}
        {nodes.length > 0 && (
          <div className="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 bg-white/95 backdrop-blur-md border border-[#e7e1d8] rounded-2xl p-1.5 shadow-lg">
            {/* Search Button */}
            <button
              onClick={toggleSearchOverlay}
              className="px-3 h-9 rounded-xl flex items-center gap-1.5 text-[#8a8175] hover:text-[var(--coral)] hover:bg-[#faf9f5] transition-all text-xs font-semibold border-none bg-transparent cursor-pointer"
              title="Tìm kiếm (Cmd+K)"
            >
              <Search className="w-4 h-4" />
              <span className="hidden sm:inline">Tìm kiếm</span>
              <kbd className="hidden md:inline-flex h-4 items-center gap-0.5 rounded border border-[#e7e1d8] bg-[#faf9f5] px-1 text-[8px] font-mono font-medium text-[#aaa39a] leading-none">
                ⌘K
              </kbd>
            </button>

            <div className="w-px h-5 bg-[#e7e1d8]" />

            {/* Zoom In */}
            <button
              onClick={() => setTransform({ scale: Math.min(3, transform.scale + 0.15) })}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8a8175] hover:text-[var(--coral)] hover:bg-[#faf9f5] transition-all border-none bg-transparent cursor-pointer"
              title="Phóng to"
            >
              <ZoomIn className="w-4 h-4" />
            </button>

            {/* Zoom Out */}
            <button
              onClick={() => setTransform({ scale: Math.max(0.2, transform.scale - 0.15) })}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8a8175] hover:text-[var(--coral)] hover:bg-[#faf9f5] transition-all border-none bg-transparent cursor-pointer"
              title="Thu nhỏ"
            >
              <ZoomOut className="w-4 h-4" />
            </button>

            {/* Fit View */}
            <button
              onClick={handleFitView}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8a8175] hover:text-[var(--coral)] hover:bg-[#faf9f5] transition-all border-none bg-transparent cursor-pointer"
              title="Khớp với khung nhìn"
            >
              <Maximize2 className="w-4 h-4" />
            </button>

            {/* Reset */}
            <button
              onClick={resetTransform}
              className="w-9 h-9 rounded-xl flex items-center justify-center text-[#8a8175] hover:text-[var(--coral)] hover:bg-[#faf9f5] transition-all border-none bg-transparent cursor-pointer"
              title="Đặt lại"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Search Overlay */}
        <SearchOverlay
          isOpen={showSearchOverlay}
          onClose={toggleSearchOverlay}
          onSelectNode={handleSelectFromSearch}
        />
      </div>
    </div>
  );
}
