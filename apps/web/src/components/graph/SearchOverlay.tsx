/**
 * SearchOverlay - Command palette style search (Cmd+K)
 * Features: Fuzzy search, keyboard navigation, recent searches
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  X,
  ArrowRight,
  Clock,
  Hash,
} from 'lucide-react';
import { useGraphStore, getNodeColor, getNodeLabel } from './graphStore';
import { graphApi, type GraphNode as ApiGraphNode } from '@/lib/api/brain';

interface SearchOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectNode: (nodeId: string) => void;
}

export function SearchOverlay({ isOpen, onClose, onSelectNode }: SearchOverlayProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiGraphNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('historiai-graph-recent-searches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch {
        // Ignore parse errors
      }
    }
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Debounced search
  useSearch(query, (nodes) => {
    setResults(nodes);
    setLoading(false);
    setSelectedIndex(0);
  });

  const handleSearch = useCallback((value: string) => {
    setQuery(value);
    if (value.length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
  }, []);

  const addToRecent = useCallback((search: string) => {
    setRecentSearches(prev => {
      const filtered = prev.filter(s => s !== search);
      const newRecent = [search, ...filtered].slice(0, 5);
      localStorage.setItem('historiai-graph-recent-searches', JSON.stringify(newRecent));
      return newRecent;
    });
  }, []);

  const handleSelect = useCallback((node: ApiGraphNode) => {
    addToRecent(node.name);
    onSelectNode(node.id);
    onClose();
  }, [onSelectNode, onClose, addToRecent]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const items = results.length > 0 ? results : [];
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (items[selectedIndex]) {
          handleSelect(items[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
    }
  }, [results, selectedIndex, handleSelect, onClose]);

  const displayItems = results.length > 0 
    ? results 
    : recentSearches.map(s => ({ id: `recent-${s}`, name: s, type: 'recent' } as any));

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50 p-1.5"
          >
            {/* Double-Bezel Card Frame */}
            <div className="bg-[#1C2120]/5 backdrop-blur-2xl border border-white/30 rounded-[24px] p-1.5 shadow-[0_32px_64px_-12px_rgba(11,48,48,0.15)]">
              <div className="bg-white/95 rounded-[18px] overflow-hidden border border-[#e7e1d8] flex flex-col">
                
                {/* Search Input */}
                <div className="flex items-center gap-3 px-5 py-4 border-b border-[#f0ebe3] bg-white">
                  <Search className="w-4 h-4 text-[#8a8175]" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => handleSearch(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Tìm kiếm nhân vật, sự kiện, địa danh..."
                    className="flex-1 text-sm text-[#2d2a26] placeholder-[#aaa39a] bg-transparent p-0 border-none outline-none focus:outline-none focus:ring-0 focus:border-none focus:shadow-none"
                    style={{ border: 'none', outline: 'none', boxShadow: 'none' }}
                  />
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-[#e7e1d8] border-t-[var(--coral)] rounded-full animate-spin" />
                  ) : (
                    <kbd className="hidden sm:inline-flex h-5 items-center gap-0.5 rounded border border-[#e7e1d8] bg-[#faf9f5] px-1.5 text-[9px] font-mono font-medium text-[#aaa39a] leading-none">
                      ESC
                    </kbd>
                  )}
                </div>

                {/* Results */}
                <div className="max-h-[340px] overflow-y-auto p-2 bg-[#faf9f5]">
                  {results.length > 0 && (
                    <div className="space-y-1">
                      <p className="px-3 py-1.5 text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">
                        Kết quả ({results.length})
                      </p>
                      {results.map((node, index) => {
                        const isSelected = index === selectedIndex;
                        return (
                          <button
                            key={node.id}
                            onClick={() => handleSelect(node)}
                            onMouseEnter={() => setSelectedIndex(index)}
                            className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl transition-all duration-300 border-none cursor-pointer ${
                              isSelected 
                                ? 'bg-[#1c2120]/5 translate-x-1 shadow-sm' 
                                : 'bg-transparent hover:bg-[#1c2120]/3'
                            }`}
                          >
                            <div
                              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all"
                              style={{ 
                                backgroundColor: isSelected ? `${getNodeColor(node.type)}25` : `${getNodeColor(node.type)}12`,
                                transform: isSelected ? 'scale(1.05)' : 'scale(1)'
                              }}
                            >
                              <div
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: getNodeColor(node.type) }}
                              />
                            </div>
                            <div className="flex-1 text-left min-w-0">
                              <p className={`text-sm font-semibold truncate transition-colors ${
                                isSelected ? 'text-[var(--coral)]' : 'text-[#2d2a26]'
                              }`}>
                                {node.name}
                              </p>
                              <p className="text-[10px] text-[#8a8175] mt-0.5">{getNodeLabel(node.type)}</p>
                            </div>
                            <ArrowRight className={`w-3.5 h-3.5 transition-all ${
                              isSelected ? 'opacity-100 translate-x-0 text-[var(--coral)]' : 'opacity-0 -translate-x-2 text-[#8a8175]'
                            }`} />
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {query.length === 0 && recentSearches.length > 0 && (
                    <div className="space-y-1">
                      <p className="px-3 py-1.5 text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider flex items-center gap-1.5">
                        <Clock className="w-3 h-3" />
                        Tìm kiếm gần đây
                      </p>
                      {recentSearches.map((search, index) => {
                        const isSelected = index === selectedIndex;
                        return (
                          <button
                            key={search}
                            onClick={() => handleSearch(search)}
                            onMouseEnter={() => setSelectedIndex(index)}
                            className={`w-full flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl transition-all duration-300 border-none cursor-pointer ${
                              isSelected 
                                ? 'bg-[#1c2120]/5 translate-x-1 shadow-sm' 
                                : 'bg-transparent hover:bg-[#1c2120]/3'
                            }`}
                          >
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-white border border-[#e7e1d8]">
                              <Hash className="w-3.5 h-3.5 text-[#8a8175]" />
                            </div>
                            <div className="flex-1 text-left min-w-0">
                              <p className={`text-sm font-semibold truncate ${
                                isSelected ? 'text-[var(--coral)]' : 'text-[#4a4a4a]'
                              }`}>
                                {search}
                              </p>
                            </div>
                            <ArrowRight className={`w-3.5 h-3.5 transition-all ${
                              isSelected ? 'opacity-100 translate-x-0 text-[var(--coral)]' : 'opacity-0 -translate-x-2 text-[#8a8175]'
                            }`} />
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {query.length >= 2 && results.length === 0 && !loading && (
                    <div className="py-12 px-4 text-center">
                      <Search className="w-8 h-8 text-[#d0cbc4] mx-auto mb-3" />
                      <p className="text-xs font-semibold text-[#8a8175]">Không tìm thấy kết quả nào cho "{query}"</p>
                      <p className="text-[10px] text-[#aaa39a] mt-1">Vui lòng kiểm tra lại chính tả hoặc thử từ khóa khác</p>
                    </div>
                  )}

                  {query.length === 0 && recentSearches.length === 0 && (
                    <div className="py-12 px-4 text-center">
                      <Search className="w-8 h-8 text-[#d0cbc4] mx-auto mb-3" />
                      <p className="text-xs font-semibold text-[#8a8175]">Bắt đầu gõ để tìm kiếm thực thể lịch sử</p>
                      <p className="text-[10px] text-[#aaa39a] mt-1">Nhập nhân vật, sự kiện, địa điểm, thời kỳ...</p>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="px-5 py-3.5 border-t border-[#f0ebe3] bg-white flex items-center justify-between text-[10px] text-[#8a8175]">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1.5">
                      <kbd className="px-1.5 py-0.5 bg-[#faf9f5] rounded border border-[#e7e1d8] text-[9px] font-mono shadow-sm">↑</kbd>
                      <kbd className="px-1.5 py-0.5 bg-[#faf9f5] rounded border border-[#e7e1d8] text-[9px] font-mono shadow-sm">↓</kbd>
                      để di chuyển
                    </span>
                    <span className="flex items-center gap-1.5">
                      <kbd className="px-1.5 py-0.5 bg-[#faf9f5] rounded border border-[#e7e1d8] text-[9px] font-mono shadow-sm">↵</kbd>
                      để chọn
                    </span>
                  </div>
                  <span className="flex items-center gap-1.5">
                    <kbd className="px-1.5 py-0.5 bg-[#faf9f5] rounded border border-[#e7e1d8] text-[9px] font-mono shadow-sm">ESC</kbd>
                    để đóng
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Custom hook for debounced search
function useSearch(query: string, onResults: (nodes: ApiGraphNode[]) => void) {
  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (query.length < 2) {
      onResults([]);
      return;
    }

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await graphApi.getNodes(query);
        onResults(res.nodes || []);
      } catch (error) {
        console.error('Search failed:', error);
        onResults([]);
      }
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, onResults]);
}
