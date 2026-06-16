/**
 * Zustand store for Graph Brain - Obsidian-style Knowledge Graph
 * Manages graph state machine: global/local modes, selection, filters, view settings
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================================================
// Types
// ============================================================================

export type NodeType = 'event' | 'person' | 'place' | 'organization' | 'period' | 'document' | 'agreement' | 'battle' | 'concept';

export type ViewMode = '2d' | '3d';

export type GraphMode = 'global' | 'local';

export interface GraphNode {
  id: string;
  slug: string;
  name: string;
  type: string;
  description?: string;
  // Physics simulation state
  x: number;
  y: number;
  vx: number;
  vy: number;
  degree: number;
  isCenter: boolean;
  isPinned?: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  edge_type: string;
  weight: number;
}

export interface ViewTransform {
  x: number;
  y: number;
  scale: number;
}

export interface FilterState {
  search: string;
  nodeTypes: Record<string, boolean>;
  showOrphans: boolean;
  minConnections: number;
  maxConnections: number;
}

export interface PhysicsSettings {
  repulsion: number;
  attraction: number;
  gravity: number;
  restLength: number;
  damping: number;
}

export interface GraphSettings {
  showLabels: boolean;
  showArrows: boolean;
  labelThreshold: number;
  nodeSize: number;
  linkThickness: number;
}

// ============================================================================
// Node Colors
// ============================================================================

export const NODE_COLORS: Record<string, string> = {
  event: '#ef4444',
  person: '#4f46e5',
  place: '#10b981',
  organization: '#8b5cf6',
  period: '#f59e0b',
  document: '#06b6d4',
  agreement: '#ec4899',
  battle: '#dc2626',
  concept: '#84cc16',
  default: '#8b8b8b',
};

export const NODE_LABELS: Record<string, string> = {
  event: 'Sự kiện',
  person: 'Nhân vật',
  place: 'Địa điểm',
  organization: 'Tổ chức',
  period: 'Giai đoạn',
  document: 'Tài liệu',
  agreement: 'Hiệp định',
  battle: 'Trận đánh',
  concept: 'Khái niệm',
  default: 'Khác',
};

// ============================================================================
// Edge Labels (Vietnamese)
// ============================================================================

export const EDGE_LABELS: Record<string, string> = {
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
  default: 'liên quan',
};

export function getEdgeLabel(et: string): string {
  return EDGE_LABELS[et] || et.toLowerCase().replace(/_/g, ' ');
}

export function getNodeColor(type: string): string {
  const key = type.toLowerCase() as NodeType;
  return NODE_COLORS[key] || NODE_COLORS.default;
}

export function getNodeLabel(type: string): string {
  const key = type.toLowerCase() as NodeType;
  return NODE_LABELS[key] || type;
}

// ============================================================================
// Store Interface
// ============================================================================

interface GraphState {
  // Graph Data
  nodes: GraphNode[];
  edges: GraphEdge[];
  
  // Loading states
  loading: boolean;
  error: string | null;
  
  // View Mode
  viewMode: ViewMode;
  graphMode: GraphMode;
  
  // Selection
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  hoveredEdgeIndex: number | null;
  contextMenuNodeId: string | null;
  
  // Local Graph
  localGraphDepth: number;
  
  // Transform
  transform: ViewTransform;
  
  // Filters
  filters: FilterState;
  
  // Settings
  settings: GraphSettings;
  physics: PhysicsSettings;
  
  // Panels
  showControlPanel: boolean;
  showSearchOverlay: boolean;
  showNodePanel: boolean;
  
  // ============================================================================
  // Actions
  // ============================================================================
  
  // Data
  setNodes: (nodes: GraphNode[]) => void;
  setEdges: (edges: GraphEdge[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // View Mode
  setViewMode: (mode: ViewMode) => void;
  toggleViewMode: () => void;
  
  // Graph Mode (global/local)
  setGraphMode: (mode: GraphMode) => void;
  toggleGraphMode: () => void;
  
  // Selection
  setSelectedNodeId: (id: string | null) => void;
  setHoveredNodeId: (id: string | null) => void;
  setHoveredEdgeIndex: (index: number | null) => void;
  setContextMenuNodeId: (id: string | null) => void;
  
  // Local Graph
  setLocalGraphDepth: (depth: number) => void;
  
  // Transform
  setTransform: (transform: Partial<ViewTransform>) => void;
  resetTransform: () => void;
  
  // Filters
  setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  toggleNodeType: (type: string) => void;
  resetFilters: () => void;
  
  // Settings
  setSetting: <K extends keyof GraphSettings>(key: K, value: GraphSettings[K]) => void;
  setPhysics: <K extends keyof PhysicsSettings>(key: K, value: PhysicsSettings[K]) => void;
  
  // Panels
  toggleControlPanel: () => void;
  toggleSearchOverlay: () => void;
  toggleNodePanel: () => void;
  
  // Node physics updates
  updateNodePosition: (id: string, x: number, y: number, vx?: number, vy?: number) => void;
  pinNode: (id: string, pinned: boolean) => void;
  
  // Computed
  getVisibleNodes: () => GraphNode[];
  getVisibleEdges: () => GraphEdge[];
  getConnectedNodeIds: (nodeId: string) => Set<string>;
}

// ============================================================================
// Default Values
// ============================================================================

const DEFAULT_TRANSFORM: ViewTransform = { x: 0, y: 0, scale: 1 };

const DEFAULT_FILTERS: FilterState = {
  search: '',
  nodeTypes: {
    event: true,
    person: true,
    place: true,
    organization: true,
    period: true,
    document: true,
    agreement: true,
    battle: true,
    concept: true,
  },
  showOrphans: true,
  minConnections: 0,
  maxConnections: Infinity,
};

const DEFAULT_SETTINGS: GraphSettings = {
  showLabels: true,
  showArrows: true,
  labelThreshold: 0.8,
  nodeSize: 8,
  linkThickness: 1,
};

const DEFAULT_PHYSICS: PhysicsSettings = {
  repulsion: 4500,
  attraction: 0.05,
  gravity: 0.0125,
  restLength: 70,
  damping: 0.81,
};

// Helper to persist node positions to localStorage
const saveNodePositions = (nodes: GraphNode[]) => {
  try {
    const positions: Record<string, { x: number, y: number, isPinned?: boolean }> = {};
    nodes.forEach(n => {
      positions[n.id] = { x: n.x, y: n.y, isPinned: n.isPinned };
    });
    localStorage.setItem('historiai-graph-node-positions', JSON.stringify(positions));
  } catch (err) {
    console.error('Failed to save node positions:', err);
  }
};

// ============================================================================
// Store
// ============================================================================

export const useGraphStore = create<GraphState>()(
  persist(
    (set, get) => ({
      // Initial state
      nodes: [],
      edges: [],
      loading: false,
      error: null,
      
      viewMode: '2d',
      graphMode: 'global',
      
      selectedNodeId: null,
      hoveredNodeId: null,
      hoveredEdgeIndex: null,
      contextMenuNodeId: null,
      
      localGraphDepth: 2,
      
      transform: DEFAULT_TRANSFORM,
      
      filters: DEFAULT_FILTERS,
      settings: DEFAULT_SETTINGS,
      physics: DEFAULT_PHYSICS,
      
      showControlPanel: true,
      showSearchOverlay: false,
      showNodePanel: false,
      
      // ============================================================================
      // Actions
      // ============================================================================
      
      // Data
      setNodes: (nodes) => {
        set({ nodes });
        saveNodePositions(nodes);
      },
      setEdges: (edges) => set({ edges }),
      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      
      // View Mode
      setViewMode: (mode) => set({ viewMode: mode }),
      toggleViewMode: () => set((s) => ({ viewMode: s.viewMode === '2d' ? '3d' : '2d' })),
      
      // Graph Mode
      setGraphMode: (mode) => set({ graphMode: mode }),
      toggleGraphMode: () => set((s) => ({ 
        graphMode: s.graphMode === 'global' ? 'local' : 'global',
        selectedNodeId: null,
      })),
      
      // Selection
      setSelectedNodeId: (id) => set({ 
        selectedNodeId: id,
        showNodePanel: id !== null,
      }),
      setHoveredNodeId: (id) => set({ hoveredNodeId: id }),
      setHoveredEdgeIndex: (index) => set({ hoveredEdgeIndex: index }),
      setContextMenuNodeId: (id) => set({ contextMenuNodeId: id }),
      
      // Local Graph
      setLocalGraphDepth: (depth) => set({ localGraphDepth: depth }),
      
      // Transform
      setTransform: (t) => set((s) => ({ 
        transform: { ...s.transform, ...t } 
      })),
      resetTransform: () => set({ transform: DEFAULT_TRANSFORM }),
      
      // Filters
      setFilter: (key, value) => set((s) => ({ 
        filters: { ...s.filters, [key]: value } 
      })),
      toggleNodeType: (type) => set((s) => ({
        filters: {
          ...s.filters,
          nodeTypes: {
            ...s.filters.nodeTypes,
            [type]: !s.filters.nodeTypes[type],
          }
        }
      })),
      resetFilters: () => set({ filters: DEFAULT_FILTERS }),
      
      // Settings
      setSetting: (key, value) => set((s) => ({ 
        settings: { ...s.settings, [key]: value } 
      })),
      setPhysics: (key, value) => set((s) => ({ 
        physics: { ...s.physics, [key]: value } 
      })),
      
      // Panels
      toggleControlPanel: () => set((s) => ({ showControlPanel: !s.showControlPanel })),
      toggleSearchOverlay: () => set((s) => ({ showSearchOverlay: !s.showSearchOverlay })),
      toggleNodePanel: () => set((s) => ({ showNodePanel: !s.showNodePanel })),
      
      // Node physics
      updateNodePosition: (id, x, y, vx = 0, vy = 0) => set((s) => {
        const nextNodes = s.nodes.map(n => n.id === id ? { ...n, x, y, vx, vy } : n);
        saveNodePositions(nextNodes);
        return { nodes: nextNodes };
      }),
      pinNode: (id, pinned) => set((s) => {
        const nextNodes = s.nodes.map(n => n.id === id ? { ...n, isPinned: pinned } : n);
        saveNodePositions(nextNodes);
        return { nodes: nextNodes };
      }),
      
      // Computed getters
      getVisibleNodes: () => {
        const { nodes, filters } = get();
        return nodes.filter(node => {
          // Type filter
          if (!filters.nodeTypes[node.type.toLowerCase()]) return false;
          // Search filter
          if (filters.search && !node.name.toLowerCase().includes(filters.search.toLowerCase())) {
            return false;
          }
          // Connection filter
          if (node.degree < filters.minConnections) return false;
          if (filters.maxConnections !== Infinity && node.degree > filters.maxConnections) return false;
          return true;
        });
      },
      
      getVisibleEdges: () => {
        const { edges, nodes } = get();
        const visibleNodeIds = new Set(get().getVisibleNodes().map(n => n.id));
        return edges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));
      },
      
      getConnectedNodeIds: (nodeId) => {
        const { edges } = get();
        const connected = new Set<string>();
        connected.add(nodeId);
        edges.forEach(e => {
          if (e.source === nodeId) connected.add(e.target);
          if (e.target === nodeId) connected.add(e.source);
        });
        return connected;
      },
    }),
    {
      name: 'historiai-graph-settings',
      partialize: (state) => ({
        viewMode: state.viewMode,
        filters: state.filters,
        settings: state.settings,
        physics: state.physics,
        localGraphDepth: state.localGraphDepth,
        showControlPanel: state.showControlPanel,
      }),
    }
  )
);

// ============================================================================
// Selectors (for performance)
// ============================================================================

export const selectNodes = (state: GraphState) => state.nodes;
export const selectEdges = (state: GraphState) => state.edges;
export const selectSelectedNodeId = (state: GraphState) => state.selectedNodeId;
export const selectHoveredNodeId = (state: GraphState) => state.hoveredNodeId;
export const selectTransform = (state: GraphState) => state.transform;
export const selectViewMode = (state: GraphState) => state.viewMode;
export const selectGraphMode = (state: GraphState) => state.graphMode;
