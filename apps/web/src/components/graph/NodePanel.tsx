/**
 * NodePanel - Node detail and edit panel
 * Features: Node info, connections, quick actions
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  ExternalLink,
  Trash2,
  Edit3,
  Link2,
  ArrowRight,
  Clock,
  BookOpen,
  User,
  MapPin,
  Building,
  FileText,
  Calendar,
  Swords,
} from 'lucide-react';
import { useGraphStore, getNodeColor, getNodeLabel, getEdgeLabel, type NodeType } from './graphStore';

const NODE_ICONS: Record<string, React.ReactNode> = {
  event: <Calendar className="w-4 h-4" />,
  person: <User className="w-4 h-4" />,
  place: <MapPin className="w-4 h-4" />,
  organization: <Building className="w-4 h-4" />,
  period: <Clock className="w-4 h-4" />,
  document: <FileText className="w-4 h-4" />,
  battle: <Swords className="w-4 h-4" />,
  agreement: <FileText className="w-4 h-4" />,
  concept: <BookOpen className="w-4 h-4" />,
};

interface NodePanelProps {
  onClose: () => void;
  onNavigateToNode: (nodeId: string) => void;
}

export function NodePanel({ onClose, onNavigateToNode }: NodePanelProps) {
  const { selectedNodeId, nodes, edges, setSelectedNodeId } = useGraphStore();

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  if (!selectedNode) return null;

  // Get connections
  const outgoingEdges = edges.filter(e => e.source === selectedNode.id);
  const incomingEdges = edges.filter(e => e.target === selectedNode.id);

  const getNodeById = (id: string) => nodes.find(n => n.id === id);

  const handleNavigate = (nodeId: string) => {
    setSelectedNodeId(nodeId);
    onNavigateToNode(nodeId);
  };

  return (
    <div className="absolute top-4 right-4 z-20 w-80">
      <div className="bg-white/95 backdrop-blur-md border border-[#e7e1d8] rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.08)] overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-[#f0ebe3]">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: `${getNodeColor(selectedNode.type)}20` }}
              >
                <span style={{ color: getNodeColor(selectedNode.type) }}>
                  {NODE_ICONS[selectedNode.type.toLowerCase()] || <BookOpen className="w-4 h-4" />}
                </span>
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#2d2a26] leading-tight">{selectedNode.name}</h3>
                <p className="text-xs text-[#8a8175] mt-0.5">{getNodeLabel(selectedNode.type)}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-[#f5f1ea] rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-[#8a8175]" />
            </button>
          </div>

          {/* Stats */}
          <div className="flex gap-3 mt-3 pt-3 border-t border-[#f0ebe3]">
            <div className="flex items-center gap-1.5">
              <Link2 className="w-3.5 h-3.5 text-[#8a8175]" />
              <span className="text-xs text-[#8a8175]">
                <span className="font-semibold text-[#2d2a26]">{outgoingEdges.length + incomingEdges.length}</span> kết nối
              </span>
            </div>
            {selectedNode.description && (
              <div className="flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-[#8a8175]" />
                <span className="text-xs text-[#8a8175]">Có mô tả</span>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
          
          {/* Description */}
          {selectedNode.description && (
            <div className="p-4 border-b border-[#f0ebe3]">
              <h4 className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider mb-2">Mô tả</h4>
              <p className="text-xs text-[#4a4a4a] leading-relaxed">{selectedNode.description}</p>
            </div>
          )}

          {/* Outgoing Connections */}
          {outgoingEdges.length > 0 && (
            <div className="p-4 border-b border-[#f0ebe3]">
              <h4 className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider mb-3">
                Kết nối ra ({outgoingEdges.length})
              </h4>
              <div className="space-y-2">
                {outgoingEdges.map(edge => {
                  const targetNode = getNodeById(edge.target);
                  if (!targetNode) return null;
                  return (
                    <button
                      key={edge.id}
                      onClick={() => handleNavigate(targetNode.id)}
                      className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-[#faf9f5] transition-colors group"
                    >
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: `${getNodeColor(targetNode.type)}20` }}
                      >
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getNodeColor(targetNode.type) }}
                        />
                      </div>
                      <div className="flex-1 min-w-0 text-left">
                        <p className="text-xs font-semibold text-[#2d2a26] truncate group-hover:text-[var(--coral)] transition-colors">
                          {targetNode.name}
                        </p>
                        <p className="text-[10px] text-[#8a8175]">{getEdgeLabel(edge.edge_type)}</p>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-[#d0cbc4] group-hover:text-[var(--coral)] transition-colors" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Incoming Connections */}
          {incomingEdges.length > 0 && (
            <div className="p-4">
              <h4 className="text-[10px] font-bold text-[#aaa39a] uppercase tracking-wider mb-3">
                Kết nối vào ({incomingEdges.length})
              </h4>
              <div className="space-y-2">
                {incomingEdges.map(edge => {
                  const sourceNode = getNodeById(edge.source);
                  if (!sourceNode) return null;
                  return (
                    <button
                      key={edge.id}
                      onClick={() => handleNavigate(sourceNode.id)}
                      className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-[#faf9f5] transition-colors group"
                    >
                      <div className="flex-1 min-w-0 text-right">
                        <p className="text-xs font-semibold text-[#2d2a26] truncate group-hover:text-[var(--coral)] transition-colors">
                          {sourceNode.name}
                        </p>
                        <p className="text-[10px] text-[#8a8175]">{getEdgeLabel(edge.edge_type)}</p>
                      </div>
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: `${getNodeColor(sourceNode.type)}20` }}
                      >
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: getNodeColor(sourceNode.type) }}
                        />
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-[#d0cbc4] rotate-180 group-hover:text-[var(--coral)] transition-colors" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {outgoingEdges.length === 0 && incomingEdges.length === 0 && (
            <div className="p-6 text-center">
              <Link2 className="w-8 h-8 text-[#d0cbc4] mx-auto mb-2" />
              <p className="text-xs text-[#8a8175]">Không có kết nối nào</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="p-3 border-t border-[#f0ebe3] bg-[#faf9f5] flex gap-2">
          <button className="flex-1 py-2 px-3 bg-white border border-[#e7e1d8] hover:border-[var(--coral)] rounded-xl text-xs font-semibold text-[#4a4a4a] hover:text-[var(--coral)] transition-colors flex items-center justify-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5" />
            Chi tiết
          </button>
          <button className="flex-1 py-2 px-3 bg-white border border-[#e7e1d8] hover:border-[var(--coral)] rounded-xl text-xs font-semibold text-[#4a4a4a] hover:text-[var(--coral)] transition-colors flex items-center justify-center gap-1.5">
            <Edit3 className="w-3.5 h-3.5" />
            Chỉnh sửa
          </button>
        </div>
      </div>
    </div>
  );
}
