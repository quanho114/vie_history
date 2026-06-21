/**
 * ControlPanel - Filters and settings sidebar for Graph
 * Features: Node type toggles, search, display settings
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Eye,
  EyeOff,
  Settings,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Box,
  Circle,
  AlignLeft,
  ChevronLeft,
} from 'lucide-react';
import { useGraphStore, NODE_LABELS, getNodeColor, type NodeType } from './graphStore';

interface ControlPanelProps {
  onFitView: () => void;
}

export function ControlPanel({ onFitView }: ControlPanelProps) {
  const {
    filters,
    setFilter,
    toggleNodeType,
    resetFilters,
    settings,
    setSetting,
    physics,
    setPhysics,
    localGraphDepth,
    setLocalGraphDepth,
    graphMode,
    setGraphMode,
    viewMode,
    setViewMode,
  } = useGraphStore();

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('historiai-graph-control-panel-collapsed');
      return saved ? JSON.parse(saved) === true : false;
    } catch {
      return false;
    }
  });

  const handleSetCollapsed = useCallback((collapsed: boolean) => {
    setIsCollapsed(collapsed);
    try {
      localStorage.setItem('historiai-graph-control-panel-collapsed', JSON.stringify(collapsed));
    } catch (err) {
      console.error('Failed to save control panel state:', err);
    }
  }, []);

  const [expandedSection, setExpandedSection] = useState<string | null>('filters');
  const [localSearch, setLocalSearch] = useState('');

  const toggleSection = (section: string) => {
    setExpandedSection(prev => prev === section ? null : section);
  };

  const handleSearchChange = useCallback((value: string) => {
    setLocalSearch(value);
    setFilter('search', value);
  }, [setFilter]);

  const nodeTypes = Object.entries(NODE_LABELS).filter(([key]) => key !== 'default');

  if (isCollapsed) {
    return (
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ duration: 0.2 }}
        onClick={() => handleSetCollapsed(false)}
        className="absolute top-4 left-4 z-20 w-11 h-11 bg-white/95 backdrop-blur-md border border-[#e7e1d8] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.06)] flex items-center justify-center hover:bg-[#faf9f5] hover:text-[var(--coral)] transition-all cursor-pointer text-[#8a8175]"
        title="Mở bảng điều khiển"
      >
        <Filter className="w-5 h-5" />
      </motion.button>
    );
  }

  return (
    <motion.div
      initial={{ x: -340, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -340, opacity: 0 }}
      transition={{ type: 'spring', damping: 26, stiffness: 220 }}
      className="absolute top-4 left-4 z-20 w-80 max-h-[calc(100%-2rem)] overflow-hidden flex flex-col"
    >
      {/* Main Panel */}
      <div className="bg-white/95 backdrop-blur-md border border-[#e7e1d8] rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.08)] overflow-hidden flex flex-col max-h-full">
        
        {/* Header */}
        <div className="p-4 border-b border-[#f0ebe3]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Box className="w-4 h-4 text-[var(--coral)]" />
              <h2 className="font-bold text-sm text-[#2d2a26]">Bản đồ tri thức</h2>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={resetFilters}
                className="p-1.5 hover:bg-[#f5f1ea] rounded-lg transition-colors border-none bg-transparent cursor-pointer"
                title="Đặt lại bộ lọc"
              >
                <RotateCcw className="w-3.5 h-3.5 text-[#8a8175]" />
              </button>
              <button
                onClick={() => handleSetCollapsed(true)}
                className="p-1.5 hover:bg-[#f5f1ea] rounded-lg transition-colors border-none bg-transparent cursor-pointer"
                title="Thu gọn bảng điều khiển"
              >
                <ChevronLeft className="w-4 h-4 text-[#8a8175]" />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
            <input
              type="text"
              value={localSearch}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Tìm kiếm..."
              className="w-full pl-9 pr-3 py-2.5 bg-[#faf9f5] border border-[#e7e1d8] rounded-xl text-sm text-[#2d2a26] placeholder-[#aaa39a] outline-none focus:border-[var(--coral)] focus:ring-1 focus:ring-[var(--coral)]/20 transition-all"
            />
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          
          {/* Graph Mode Toggle */}
          <div className="p-4 border-b border-[#f0ebe3]">
            <div className="flex gap-1 p-1 bg-[#f5f1ea] rounded-xl">
              <button
                onClick={() => setGraphMode('global')}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                  graphMode === 'global'
                    ? 'bg-white text-[#2d2a26] shadow-sm'
                    : 'text-[#8a8175] hover:text-[#2d2a26]'
                }`}
              >
                Toàn bộ
              </button>
              <button
                onClick={() => setGraphMode('local')}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                  graphMode === 'local'
                    ? 'bg-white text-[#2d2a26] shadow-sm'
                    : 'text-[#8a8175] hover:text-[#2d2a26]'
                }`}
              >
                Cục bộ
              </button>
            </div>

            {graphMode === 'local' && (
              <div className="mt-3">
                <label className="text-xs text-[#8a8175] font-medium">Độ sâu kết nối</label>
                <input
                  type="range"
                  min={1}
                  max={4}
                  value={localGraphDepth}
                  onChange={(e) => setLocalGraphDepth(parseInt(e.target.value))}
                  className="w-full mt-1 accent-[var(--coral)]"
                />
                <div className="flex justify-between text-[10px] text-[#aaa39a]">
                  <span>1</span>
                  <span className="font-semibold text-[var(--coral)]">{localGraphDepth}</span>
                  <span>4</span>
                </div>
              </div>
            )}
          </div>

          {/* Filters Section */}
          <div className="border-b border-[#f0ebe3]">
            <button
              onClick={() => toggleSection('filters')}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-[#faf9f5] transition-colors"
            >
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-[#8a8175]" />
                <span className="text-sm font-semibold text-[#2d2a26]">Bộ lọc</span>
              </div>
              {expandedSection === 'filters' ? (
                <ChevronUp className="w-4 h-4 text-[#8a8175]" />
              ) : (
                <ChevronDown className="w-4 h-4 text-[#8a8175]" />
              )}
            </button>

            <AnimatePresence>
              {expandedSection === 'filters' && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[#8a8175]">Loại thực thể</span>
                      <button
                        onClick={() => {
                          const allEnabled = nodeTypes.every(([key]) => filters.nodeTypes[key]);
                          nodeTypes.forEach(([key]) => {
                            if (allEnabled !== filters.nodeTypes[key]) {
                              toggleNodeType(key);
                            }
                          });
                        }}
                        className="text-[10px] text-[var(--coral)] hover:underline"
                      >
                        {nodeTypes.every(([key]) => filters.nodeTypes[key]) ? 'Tắt tất cả' : 'Bật tất cả'}
                      </button>
                    </div>
                    {nodeTypes.map(([key, label]) => (
                      <label
                        key={key}
                        className="flex items-center gap-2.5 py-1.5 px-2 rounded-lg hover:bg-[#faf9f5] cursor-pointer transition-colors"
                      >
                        <div className="relative">
                          <input
                            type="checkbox"
                            checked={filters.nodeTypes[key] ?? true}
                            onChange={() => toggleNodeType(key)}
                            className="sr-only"
                          />
                          <div
                            className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                              filters.nodeTypes[key]
                                ? 'border-[var(--coral)] bg-[var(--coral)]'
                                : 'border-[#d0cbc4]'
                            }`}
                          >
                            {filters.nodeTypes[key] && (
                              <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                        </div>
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: getNodeColor(key) }}
                        />
                        <span className="text-xs font-medium text-[#4a4a4a]">{label}</span>
                      </label>
                    ))}

                    {/* Orphan nodes toggle */}
                    <label className="flex items-center gap-2.5 py-1.5 px-2 rounded-lg hover:bg-[#faf9f5] cursor-pointer transition-colors">
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={filters.showOrphans}
                          onChange={() => setFilter('showOrphans', !filters.showOrphans)}
                          className="sr-only"
                        />
                        <div
                          className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                            filters.showOrphans
                              ? 'border-[var(--coral)] bg-[var(--coral)]'
                              : 'border-[#d0cbc4]'
                          }`}
                        >
                          {filters.showOrphans && (
                            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </div>
                      <span className="text-xs font-medium text-[#4a4a4a]">Hiện node cô lập</span>
                    </label>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Display Settings */}
          <div className="border-b border-[#f0ebe3]">
            <button
              onClick={() => toggleSection('display')}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-[#faf9f5] transition-colors"
            >
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#8a8175]" />
                <span className="text-sm font-semibold text-[#2d2a26]">Hiển thị</span>
              </div>
              {expandedSection === 'display' ? (
                <ChevronUp className="w-4 h-4 text-[#8a8175]" />
              ) : (
                <ChevronDown className="w-4 h-4 text-[#8a8175]" />
              )}
            </button>

            <AnimatePresence>
              {expandedSection === 'display' && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-4 space-y-4">
                    {/* Show Labels */}
                    <label className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlignLeft className="w-3.5 h-3.5 text-[#8a8175]" />
                        <span className="text-xs font-medium text-[#4a4a4a]">Nhãn node</span>
                      </div>
                      <button
                        onClick={() => setSetting('showLabels', !settings.showLabels)}
                        className={`w-9 h-5 rounded-full transition-all relative ${
                          settings.showLabels ? 'bg-[var(--coral)]' : 'bg-[#d0cbc4]'
                        }`}
                      >
                        <div
                          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${
                            settings.showLabels ? 'translate-x-4' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                    </label>

                    {/* Show Arrows */}
                    <label className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <svg className="w-3.5 h-3.5 text-[#8a8175]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <path d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                        <span className="text-xs font-medium text-[#4a4a4a]">Mũi tên</span>
                      </div>
                      <button
                        onClick={() => setSetting('showArrows', !settings.showArrows)}
                        className={`w-9 h-5 rounded-full transition-all relative ${
                          settings.showArrows ? 'bg-[var(--coral)]' : 'bg-[#d0cbc4]'
                        }`}
                      >
                        <div
                          className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${
                            settings.showArrows ? 'translate-x-4' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                    </label>

                    {/* Node Size */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <Circle className="w-3.5 h-3.5 text-[#8a8175]" />
                          <span className="text-xs font-medium text-[#4a4a4a]">Kích thước node</span>
                        </div>
                        <span className="text-[10px] text-[#aaa39a]">{settings.nodeSize}px</span>
                      </div>
                      <input
                        type="range"
                        min={4}
                        max={16}
                        value={settings.nodeSize}
                        onChange={(e) => setSetting('nodeSize', parseInt(e.target.value))}
                        className="w-full accent-[var(--coral)]"
                      />
                    </div>

                    {/* Link Thickness */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <svg className="w-3.5 h-3.5 text-[#8a8175]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                            <path d="M4 12h16" />
                          </svg>
                          <span className="text-xs font-medium text-[#4a4a4a]">Độ dày cạnh</span>
                        </div>
                        <span className="text-[10px] text-[#aaa39a]">{settings.linkThickness}px</span>
                      </div>
                      <input
                        type="range"
                        min={0.5}
                        max={4}
                        step={0.5}
                        value={settings.linkThickness}
                        onChange={(e) => setSetting('linkThickness', parseFloat(e.target.value))}
                        className="w-full accent-[var(--coral)]"
                      />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* View Mode Toggle */}
          <div className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#8a8175]">Chế độ xem</span>
              <div className="flex gap-1 p-1 bg-[#f5f1ea] rounded-lg">
                <button
                  onClick={() => setViewMode('2d')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                    viewMode === '2d'
                      ? 'bg-white text-[#2d2a26] shadow-sm'
                      : 'text-[#8a8175] hover:text-[#2d2a26]'
                  }`}
                >
                  2D
                </button>
                <button
                  onClick={() => setViewMode('3d')}
                  className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                    viewMode === '3d'
                      ? 'bg-white text-[#2d2a26] shadow-sm'
                      : 'text-[#8a8175] hover:text-[#2d2a26]'
                  }`}
                >
                  3D
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#f0ebe3] bg-[#faf9f5]">
          <button
            onClick={onFitView}
            className="w-full py-2.5 bg-[var(--coral)] hover:bg-[var(--coral-dark)] text-white rounded-xl text-xs font-semibold transition-colors flex items-center justify-center gap-2"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            Khớp với khung nhìn
          </button>
        </div>
      </div>
    </motion.div>
  );
}
