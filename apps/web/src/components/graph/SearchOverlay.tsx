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
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg z-50"
          >
            <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#e7e1d8]">
              
              {/* Search Input */}
              <div className="flex items-center gap-3 px-4 py-4 border-b border-[#f0ebe3]">
                <Search className="w-5 h-5 text-[#8a8175]" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => handleSearch(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Tìm kiếm thực thể..."
                  className="flex-1 text-sm text-[#2d2a26] placeholder-[#aaa39a] outline-none bg-transparent"
                />
                {loading && (
                  <div className="w-4 h-4 border-2 border-[#e7e1d8] border-t-[var(--coral)] rounded-full animate-spin" />
                )}
                <button
                  onClick={onClose}
                  className="px-2 py-1 bg-[#f5f1ea] rounded-lg text-xs text-[#8a8175] hover:text-[#2d2a26] transition-colors"
                >
                  ESC
                </button>
              </div>

              {/* Results */}
              <div className="max-h-[320px] overflow-y-auto">
                {results.length > 0 && (
                  <div className="p-2">
                    <p className="px-3 py-2 text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider">
                      {results.length} kết quả
                    </p>
                    {results.map((node, index) => (
                      <button
                        key={node.id}
                        onClick={() => handleSelect(node)}
                        onMouseEnter={() => setSelectedIndex(index)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${
                          index === selectedIndex ? 'bg-[#faf9f5]' : 'hover:bg-[#faf9f5]'
                        }`}
                      >
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${getNodeColor(node.type)}15` }}
                        >
                          <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: getNodeColor(node.type) }}
                          />
                        </div>
                        <div className="flex-1 text-left">
                          <p className="text-sm font-semibold text-[#2d2a26]">{node.name}</p>
                          <p className="text-[10px] text-[#8a8175]">{getNodeLabel(node.type)}</p>
                        </div>
                        {index === selectedIndex && (
                          <ArrowRight className="w-4 h-4 text-[var(--coral)]" />
                        )}
                      </button>
                    ))}
                  </div>
                )}

                {query.length === 0 && recentSearches.length > 0 && (
                  <div className="p-2">
                    <p className="px-3 py-2 text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3 h-3" />
                      Tìm kiếm gần đây
                    </p>
                    {recentSearches.map((search, index) => (
                      <button
                        key={search}
                        onClick={() => handleSearch(search)}
                        onMouseEnter={() => setSelectedIndex(index)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors ${
                          index === selectedIndex ? 'bg-[#faf9f5]' : 'hover:bg-[#faf9f5]'
                        }`}
                      >
                        <Hash className="w-4 h-4 text-[#d0cbc4]" />
                        <span className="text-sm text-[#4a4a4a]">{search}</span>
                      </button>
                    ))}
                  </div>
                )}

                {query.length >= 2 && results.length === 0 && !loading && (
                  <div className="p-8 text-center">
                    <Search className="w-10 h-10 text-[#d0cbc4] mx-auto mb-3" />
                    <p className="text-sm text-[#8a8175]">Không tìm thấy kết quả nào</p>
                    <p className="text-xs text-[#aaa39a] mt-1">Thử từ khóa khác</p>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-3 border-t border-[#f0ebe3] bg-[#faf9f5] flex items-center justify-between text-[10px] text-[#aaa39a]">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#e7e1d8]">↑</kbd>
                    <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#e7e1d8]">↓</kbd>
                    để di chuyển
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#e7e1d8]">↵</kbd>
                    để chọn
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-white rounded border border-[#e7e1d8]">ESC</kbd>
                  để đóng
                </span>
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
