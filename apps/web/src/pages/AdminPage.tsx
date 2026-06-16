import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  FileText,
  TrendingUp,
  CheckCircle,
  XCircle,
  Loader2,
  Database,
  Activity,
  GitBranch,
  Users,
  Key,
  ShieldAlert,
  Clock
} from "lucide-react"

interface Stats {
  documents: {
    total: number
    pending: number
    approved: number
    rejected: number
  }
  jobs: {
    total: number
    queued: number
    running: number
    failed: number
  }
}

export function AdminPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"stats" | "users" | "reset_requests">("stats")

  // User management states
  const [users, setUsers] = useState<any[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [resettingUser, setResettingUser] = useState<any | null>(null)
  const [newPassword, setNewPassword] = useState("")
  const [resetMessage, setResetMessage] = useState("")
  const [resetError, setResetError] = useState("")

  // Reset requests states
  const [resetRequests, setResetRequests] = useState<any[]>([])
  const [requestsLoading, setRequestsLoading] = useState(false)
  const [approvingRequest, setApprovingRequest] = useState<any | null>(null)
  const [approvePassword, setApprovePassword] = useState("")
  const [approveMessage, setApproveMessage] = useState("")
  const [approveError, setApproveError] = useState("")

  useEffect(() => {
    fetch("/api/v1/admin/stats", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then(setStats)
      .catch(() => {})
      .finally(() => setIsLoading(false))
  }, [])

  const fetchUsers = () => {
    setUsersLoading(true)
    fetch("/api/v1/admin/users", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setUsers(data)
        } else {
          setUsers([])
        }
      })
      .catch(() => setUsers([]))
      .finally(() => setUsersLoading(false))
  }

  useEffect(() => {
    if (activeTab === "users") {
      fetchUsers()
    }
  }, [activeTab])

  const fetchResetRequests = () => {
    setRequestsLoading(true)
    fetch("/api/v1/admin/reset-requests", {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setResetRequests(data)
        } else {
          setResetRequests([])
        }
      })
      .catch(() => setResetRequests([]))
      .finally(() => setRequestsLoading(false))
  }

  useEffect(() => {
    if (activeTab === "reset_requests") {
      fetchResetRequests()
    }
  }, [activeTab])

  const handleApproveRequest = (e: React.FormEvent) => {
    e.preventDefault()
    if (!approvingRequest || approvePassword.length < 8) return

    setApproveError("")
    setApproveMessage("")

    fetch(`/api/v1/admin/reset-requests/${approvingRequest.id}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({ new_password: approvePassword }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Phê duyệt thất bại")
        }
        return res.json()
      })
      .then((data) => {
        setApproveMessage(data.message || "Đặt lại mật khẩu thành công!")
        setApprovePassword("")
        fetchResetRequests()
        setTimeout(() => {
          setApprovingRequest(null)
          setApproveMessage("")
        }, 1500)
      })
      .catch((err) => {
        setApproveError(err.message)
      })
  }

  const handleRejectRequest = (requestId: string) => {
    if (!confirm("Bạn có chắc chắn muốn từ chối yêu cầu này không?")) return

    fetch(`/api/v1/admin/reset-requests/${requestId}/reject`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Từ chối thất bại")
        }
        return res.json()
      })
      .then(() => {
        fetchResetRequests()
      })
      .catch((err) => {
        alert(err.message)
      })
  }

  // Initial fetch for requests count on mount
  useEffect(() => {
    fetchResetRequests()
  }, [])

  const handleResetPassword = (e: React.FormEvent) => {
    e.preventDefault()
    if (!resettingUser || newPassword.length < 8) return

    setResetError("")
    setResetMessage("")

    fetch(`/api/v1/admin/users/${resettingUser.id}/reset-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: JSON.stringify({ new_password: newPassword }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail || "Reset password failed")
        }
        return res.json()
      })
      .then(() => {
        setResetMessage(`Đặt lại mật khẩu thành công cho ${resettingUser.username}!`)
        setNewPassword("")
        setTimeout(() => {
          setResettingUser(null)
          setResetMessage("")
        }, 1500)
      })
      .catch((err) => {
        setResetError(err.message)
      })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#faf8f4]">
        <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-[#faf8f4] relative selection:bg-[#cc785c]/10 selection:text-[#cc785c] p-3 md:p-5">
      
      {/* Outer frame matching classic book layout */}
      <div className="flex-1 flex flex-col bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl overflow-hidden relative shadow-[0_4px_30px_rgba(20,20,19,0.015)]">
        
        {/* Premium Header */}
        <header className="px-8 py-5 border-b border-[#e6dfd8] bg-white/80 backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-4 z-10">
          <div className="flex flex-wrap items-center gap-6">
            
            {/* Fine Header Brand Container */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#cc785c]/10 flex items-center justify-center border border-[#cc785c]/20 text-[#cc785c] relative overflow-hidden group">
                <svg 
                  viewBox="0 0 500 500" 
                  className="w-8 h-8 absolute opacity-10 text-[#cc785c] group-hover:rotate-45 transition-transform duration-700 pointer-events-none"
                  fill="none" 
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <circle cx="250" cy="250" r="240" stroke="currentColor" strokeWidth="6" strokeDasharray="15 15" />
                  <circle cx="250" cy="250" r="210" stroke="currentColor" strokeWidth="6" />
                  <circle cx="250" cy="250" r="140" stroke="currentColor" strokeWidth="4" />
                  <polygon 
                    points="250,195 254,232 288,212 264,241 298,250 264,259 288,288 254,268 250,305 246,268 212,288 236,259 202,250 236,241 212,212 246,232" 
                    fill="currentColor" 
                  />
                </svg>
                <TrendingUp className="w-4.5 h-4.5 text-[#cc785c] z-10" />
              </div>
              <div>
                <h2 className="text-xl font-serif font-medium text-[#141413]">Ban Quản Trị</h2>
                <p className="text-[9px] text-[#8e8b82] tracking-widest uppercase font-semibold mt-0.5">Hệ thống Lịch Sử HistoriAI</p>
              </div>
            </div>

            {/* Premium Flat Editorial Tabs */}
            <div className="flex items-center border-b border-transparent">
              <button
                onClick={() => setActiveTab("stats")}
                className={`px-4 py-2.5 text-xs font-semibold tracking-wider transition-all duration-200 border-b-2 cursor-pointer bg-transparent outline-none ${
                  activeTab === "stats"
                    ? "border-[#cc785c] text-[#cc785c]"
                    : "border-transparent text-[#6c6a64] hover:text-[#141413]"
                }`}
              >
                Thống kê hệ thống
              </button>
              <div className="w-[1px] h-3 bg-[#e6dfd8] mx-1"></div>
              <button
                onClick={() => setActiveTab("users")}
                className={`px-4 py-2.5 text-xs font-semibold tracking-wider transition-all duration-200 border-b-2 cursor-pointer bg-transparent outline-none ${
                  activeTab === "users"
                    ? "border-[#cc785c] text-[#cc785c]"
                    : "border-transparent text-[#6c6a64] hover:text-[#141413]"
                }`}
              >
                Quản lý người dùng
              </button>
              <div className="w-[1px] h-3 bg-[#e6dfd8] mx-1"></div>
              <button
                onClick={() => setActiveTab("reset_requests")}
                className={`px-4 py-2.5 text-xs font-semibold tracking-wider transition-all duration-200 border-b-2 cursor-pointer bg-transparent outline-none flex items-center gap-1.5 ${
                  activeTab === "reset_requests"
                    ? "border-[#cc785c] text-[#cc785c]"
                    : "border-transparent text-[#6c6a64] hover:text-[#141413]"
                }`}
              >
                <span>Yêu cầu khôi phục MK</span>
                {resetRequests.filter((r) => r.status === "pending").length > 0 && (
                  <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-[#cc785c] px-1 text-[9px] font-bold text-white">
                    {resetRequests.filter((r) => r.status === "pending").length}
                  </span>
                )}
              </button>
            </div>
          </div>

          <Link
            to="/graph/drafts/review"
            className="flex items-center gap-2 px-4 py-2.5 bg-[#cc785c] hover:bg-[#a9583e] text-white text-xs font-semibold rounded-xl transition-all shadow-[0_2px_8px_rgba(204,120,92,0.15)] hover:shadow-[0_4px_15px_rgba(204,120,92,0.25)] border-0 cursor-pointer active:scale-95 flex-shrink-0 self-start md:self-auto"
          >
            <GitBranch className="w-3.5 h-3.5" /> Bảng Tiến hóa Tri thức (HITL)
          </Link>
        </header>

        {/* Main content scroll area */}
        <div className="flex-1 overflow-y-auto p-8 relative z-0">

          {activeTab === "stats" && (
            stats ? (
              <div className="grid gap-10 max-w-5xl relative z-10">
                
                {/* Document Stats */}
                <div>
                  <h3 className="font-display text-lg font-medium text-[#141413] mb-5 flex items-center gap-2">
                    <span className="text-[#cc785c] text-sm">✦</span>
                    Tài liệu lưu trữ
                  </h3>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                      label="Tổng số"
                      value={stats.documents.total}
                      icon={<Database className="w-4 h-4" />}
                      type="default"
                    />
                    <StatCard
                      label="Đã duyệt"
                      value={stats.documents.approved}
                      icon={<CheckCircle className="w-4 h-4" />}
                      type="success"
                    />
                    <StatCard
                      label="Chờ duyệt"
                      value={stats.documents.pending}
                      icon={<Loader2 className="w-4 h-4 animate-pulse" />}
                      type="warning"
                    />
                    <StatCard
                      label="Từ chối"
                      value={stats.documents.rejected}
                      icon={<XCircle className="w-4 h-4" />}
                      type="danger"
                    />
                  </div>
                </div>

                {/* Job Stats */}
                <div>
                  <h3 className="font-display text-lg font-medium text-[#141413] mb-5 flex items-center gap-2">
                    <span className="text-[#cc785c] text-sm">✦</span>
                    Tiến trình hệ thống (Jobs)
                  </h3>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                    <StatCard
                      label="Tổng số"
                      value={stats.jobs.total}
                      icon={<Database className="w-4 h-4" />}
                      type="default"
                    />
                    <StatCard
                      label="Đang chạy"
                      value={stats.jobs.running}
                      icon={<Loader2 className="w-4 h-4 animate-spin" />}
                      type="info"
                    />
                    <StatCard
                      label="Đang chờ"
                      value={stats.jobs.queued}
                      icon={<Clock className="w-4 h-4" />}
                      type="warning"
                    />
                    <StatCard
                      label="Thất bại"
                      value={stats.jobs.failed}
                      icon={<XCircle className="w-4 h-4" />}
                      type="danger"
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center py-16 relative z-10">
                <p className="text-[#8e8b82] font-serif italic text-sm">Không thể tải dữ liệu thống kê hệ thống</p>
              </div>
            )
          )}

          {activeTab === "users" && (
            <div className="max-w-5xl space-y-6 relative z-10">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-medium text-[#141413] flex items-center gap-2">
                  <span className="text-[#cc785c] text-sm">✦</span>
                  Danh sách thành viên hệ thống
                </h3>
              </div>

              {usersLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white/90 border border-[#e6dfd8] rounded-xl overflow-hidden shadow-[0_4px_20px_rgba(20,20,19,0.015)] backdrop-blur-md">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/30 text-[10px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Tên người dùng</th>
                          <th className="py-4 px-6">Email</th>
                          <th className="py-4 px-6">Vai trò</th>
                          <th className="py-4 px-6">Ngày tạo</th>
                          <th className="py-4 px-6 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {users.map((u) => (
                          <tr key={u.id} className="hover:bg-[#efe9de]/10 transition-colors">
                            <td className="py-4 px-6 font-medium text-[#141413]">{u.username}</td>
                            <td className="py-4 px-6 text-[#6c6a64]">{u.email}</td>
                            <td className="py-4 px-6">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wider ${
                                u.role === "admin"
                                  ? "bg-[#b55a4c]/10 text-[#b55a4c] border border-[#b55a4c]/20"
                                  : "bg-[#4a7b9c]/10 text-[#4a7b9c] border border-[#4a7b9c]/20"
                              }`}>
                                {u.role}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82]">
                              {new Date(u.created_at).toLocaleDateString("vi-VN", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                              })}
                            </td>
                            <td className="py-4 px-6 text-right">
                              <button
                                onClick={() => setResettingUser(u)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#e6dfd8] text-[#cc785c] hover:border-[#cc785c] hover:bg-[#cc785c]/5 rounded-lg text-xs font-semibold transition-all cursor-pointer bg-white outline-none active:scale-95 shadow-sm"
                              >
                                <Key size={12} />
                                Đặt lại mật khẩu
                              </button>
                            </td>
                          </tr>
                        ))}
                        {users.length === 0 && (
                          <tr>
                            <td colSpan={5} className="py-12 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không tìm thấy tài khoản người dùng nào.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "reset_requests" && (
            <div className="max-w-5xl space-y-6 relative z-10">
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-medium text-[#141413] flex items-center gap-2">
                  <span className="text-[#cc785c] text-sm">✦</span>
                  Sổ lưu yêu cầu khôi phục mật khẩu
                </h3>
              </div>

              {requestsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-6 h-6 animate-spin text-[#cc785c]" />
                </div>
              ) : (
                <div className="bg-white/90 border border-[#e6dfd8] rounded-xl overflow-hidden shadow-[0_4px_20px_rgba(20,20,19,0.015)] backdrop-blur-md">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#e6dfd8] bg-[#efe9de]/30 text-[10px] font-bold uppercase tracking-widest text-[#6c6a64]">
                          <th className="py-4 px-6">Email</th>
                          <th className="py-4 px-6">Tên người dùng</th>
                          <th className="py-4 px-6">Ghi chú / Lý do</th>
                          <th className="py-4 px-6">Trạng thái</th>
                          <th className="py-4 px-6">Ngày gửi</th>
                          <th className="py-4 px-6 text-right">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e6dfd8]/40 text-xs text-[#141413]">
                        {resetRequests.map((r) => (
                          <tr key={r.id} className="hover:bg-[#efe9de]/10 transition-colors">
                            <td className="py-4 px-6 font-medium text-[#141413]">{r.email}</td>
                            <td className="py-4 px-6 text-[#6c6a64]">{r.username || "-"}</td>
                            <td className="py-4 px-6 text-[#6c6a64] max-w-xs truncate" title={r.reason || ""}>
                              {r.reason || "-"}
                            </td>
                            <td className="py-4 px-6">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase tracking-wider ${
                                r.status === "pending"
                                  ? "bg-[#b88a44]/10 text-[#b88a44] border border-[#b88a44]/20"
                                  : r.status === "approved"
                                  ? "bg-[#4c7a5c]/10 text-[#4c7a5c] border border-[#4c7a5c]/20"
                                  : r.status === "rejected"
                                  ? "bg-[#b55a4c]/10 text-[#b55a4c] border border-[#b55a4c]/20"
                                  : "bg-[#6c6a64]/10 text-[#6c6a64] border border-[#6c6a64]/20"
                              }`}>
                                {r.status === "pending" ? "Đang chờ" : r.status === "approved" ? "Đã duyệt" : r.status === "rejected" ? "Từ chối" : r.status}
                              </span>
                            </td>
                            <td className="py-4 px-6 text-[#8e8b82]">
                              {new Date(r.created_at).toLocaleString("vi-VN", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit"
                              })}
                            </td>
                            <td className="py-4 px-6 text-right space-x-2">
                              {r.status === "pending" ? (
                                <>
                                  <button
                                    onClick={() => setApprovingRequest(r)}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#4c7a5c] text-white hover:bg-[#3d624a] rounded-lg text-xs font-semibold transition-all border-0 cursor-pointer shadow-sm active:scale-95"
                                  >
                                    <Key size={12} />
                                    Cấp lại MK
                                  </button>
                                  <button
                                    onClick={() => handleRejectRequest(r.id)}
                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#e6dfd8] text-[#b55a4c] hover:border-[#b55a4c] hover:bg-[#b55a4c]/5 rounded-lg text-xs font-semibold transition-all cursor-pointer bg-white active:scale-95"
                                  >
                                    Từ chối
                                  </button>
                                </>
                              ) : (
                                <span className="text-[#8e8b82] text-xs italic">Đã xử lý</span>
                              )}
                            </td>
                          </tr>
                        ))}
                        {resetRequests.length === 0 && (
                          <tr>
                            <td colSpan={6} className="py-12 text-center text-[#8e8b82] font-serif italic text-sm">
                              Không tìm thấy yêu cầu khôi phục mật khẩu nào.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Reset password Modal */}
      {resettingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
          <form
            onSubmit={handleResetPassword}
            className="bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl p-6 max-w-[390px] w-full shadow-2xl space-y-4 text-left relative overflow-hidden"
          >
            {/* Fine Modal Inset Frame */}
            <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl" />

            <div className="flex items-center gap-3 border-b border-[#e6dfd8] pb-3 text-[#cc785c] relative z-10">
              <div className="w-8 h-8 rounded-lg bg-[#cc785c]/10 flex items-center justify-center text-[#cc785c] border border-[#cc785c]/20">
                <ShieldAlert size={16} />
              </div>
              <h3 className="font-display text-lg font-medium text-[#141413]">Đặt lại mật khẩu</h3>
            </div>

            <div className="space-y-1 relative z-10">
              <span className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest">Tài khoản</span>
              <p className="text-xs font-semibold text-[#141413] bg-white py-2 px-3 rounded-lg border border-[#e6dfd8]">
                {resettingUser.username} ({resettingUser.email})
              </p>
            </div>

            <div className="space-y-1.5 relative z-10">
              <label className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest block">Mật khẩu mới</label>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Nhập tối thiểu 8 ký tự"
                className="w-full bg-white border border-[#e6dfd8] rounded-xl py-2.5 px-3 text-xs text-[#141413] outline-none placeholder:text-[#8e8b82]/40 focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/5 transition-all box-border"
              />
            </div>

            {resetMessage && (
              <p className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 py-2 px-3 rounded-lg relative z-10">
                {resetMessage}
              </p>
            )}

            {resetError && (
              <p className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 py-2 px-3 rounded-lg relative z-10">
                {resetError}
              </p>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 relative z-10">
              <button
                type="button"
                onClick={() => {
                  setResettingUser(null)
                  setNewPassword("")
                  setResetError("")
                  setResetMessage("")
                }}
                className="px-4 py-2 border border-[#e6dfd8] bg-white hover:bg-[#efe9de]/30 text-[#6c6a64] rounded-xl text-xs font-semibold cursor-pointer transition-colors"
              >
                Hủy bỏ
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-[#cc785c] hover:bg-[#b86246] text-white rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 shadow-sm"
              >
                Xác nhận
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Approve Reset Request Modal */}
      {approvingRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
          <form
            onSubmit={handleApproveRequest}
            className="bg-[#faf8f4] border border-[#e6dfd8] rounded-2xl p-6 max-w-[390px] w-full shadow-2xl space-y-4 text-left relative overflow-hidden"
          >
            {/* Fine Modal Inset Frame */}
            <div className="absolute inset-2 border border-[#e6dfd8]/40 pointer-events-none rounded-xl" />

            <div className="flex items-center gap-3 border-b border-[#e6dfd8] pb-3 text-[#4c7a5c] relative z-10">
              <div className="w-8 h-8 rounded-lg bg-[#4c7a5c]/10 flex items-center justify-center text-[#4c7a5c] border border-[#4c7a5c]/20">
                <ShieldAlert size={16} />
              </div>
              <h3 className="font-display text-lg font-medium text-[#141413]">Phê duyệt & Đặt lại mật khẩu</h3>
            </div>

            <div className="space-y-1 relative z-10">
              <span className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest">Yêu cầu từ</span>
              <p className="text-xs font-semibold text-[#141413] bg-white py-2 px-3 rounded-lg border border-[#e6dfd8]">
                {approvingRequest.email} {approvingRequest.username ? `(${approvingRequest.username})` : ""}
              </p>
              {approvingRequest.reason && (
                <div className="text-[11px] text-[#8a6d3b] mt-2 bg-[#fcf8e3] p-2.5 rounded-lg border border-[#faebcc] leading-relaxed">
                  <span className="font-bold block text-[10px] uppercase tracking-wider mb-0.5">Lý do khôi phục:</span>
                  "{approvingRequest.reason}"
                </div>
              )}
            </div>

            <div className="space-y-1.5 relative z-10">
              <label className="text-[9px] text-[#6c6a64] uppercase font-bold tracking-widest block">Mật khẩu mới cấp</label>
              <input
                type="password"
                required
                minLength={8}
                value={approvePassword}
                onChange={(e) => setApprovePassword(e.target.value)}
                placeholder="Nhập tối thiểu 8 ký tự"
                className="w-full bg-white border border-[#e6dfd8] rounded-xl py-2.5 px-3 text-xs text-[#141413] outline-none placeholder:text-[#8e8b82]/40 focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/5 transition-all box-border"
              />
            </div>

            {approveMessage && (
              <p className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 py-2 px-3 rounded-lg relative z-10">
                {approveMessage}
              </p>
            )}

            {approveError && (
              <p className="text-xs font-semibold text-red-700 bg-red-50 border border-red-200 py-2 px-3 rounded-lg relative z-10">
                {approveError}
              </p>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 relative z-10">
              <button
                type="button"
                onClick={() => {
                  setApprovingRequest(null)
                  setApprovePassword("")
                  setApproveError("")
                  setApproveMessage("")
                }}
                className="px-4 py-2 border border-[#e6dfd8] bg-white hover:bg-[#efe9de]/30 text-[#6c6a64] rounded-xl text-xs font-semibold cursor-pointer transition-colors"
              >
                Hủy bỏ
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-[#4c7a5c] hover:bg-[#3d624a] text-white rounded-xl text-xs font-semibold cursor-pointer transition-colors border-0 shadow-sm"
              >
                Xác nhận & Cấp
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  icon,
  type = "default",
}: {
  label: string
  value: number
  icon: React.ReactNode
  type?: "default" | "success" | "warning" | "danger" | "info"
}) {
  const themeMap = {
    default: {
      cardHover: "hover:border-[#cc785c]/40 hover:shadow-[0_6px_20px_rgba(204,120,92,0.04)]",
      valColor: "text-[#141413]",
      iconBg: "bg-[#6c6a64]/5 text-[#6c6a64] border-[#6c6a64]/10",
      accentBg: "bg-[#6c6a64]/10",
    },
    success: {
      cardHover: "hover:border-[#4c7a5c]/40 hover:shadow-[0_6px_20px_rgba(76,122,92,0.05)]",
      valColor: "text-[#4c7a5c]",
      iconBg: "bg-[#4c7a5c]/5 text-[#4c7a5c] border-[#4c7a5c]/10",
      accentBg: "bg-[#4c7a5c]/20",
    },
    warning: {
      cardHover: "hover:border-[#b88a44]/40 hover:shadow-[0_6px_20px_rgba(184,138,68,0.05)]",
      valColor: "text-[#b88a44]",
      iconBg: "bg-[#b88a44]/5 text-[#b88a44] border-[#b88a44]/10",
      accentBg: "bg-[#b88a44]/20",
    },
    danger: {
      cardHover: "hover:border-[#b55a4c]/40 hover:shadow-[0_6px_20px_rgba(181,90,76,0.05)]",
      valColor: "text-[#b55a4c]",
      iconBg: "bg-[#b55a4c]/5 text-[#b55a4c] border-[#b55a4c]/10",
      accentBg: "bg-[#b55a4c]/20",
    },
    info: {
      cardHover: "hover:border-[#4a7b9c]/40 hover:shadow-[0_6px_20px_rgba(74,123,156,0.05)]",
      valColor: "text-[#4a7b9c]",
      iconBg: "bg-[#4a7b9c]/5 text-[#4a7b9c] border-[#4a7b9c]/10",
      accentBg: "bg-[#4a7b9c]/20",
    },
  }

  const currentTheme = themeMap[type]

  return (
    <div className={`relative overflow-hidden bg-white/90 border border-[#e6dfd8] rounded-xl p-5 transition-all duration-300 hover:-translate-y-0.5 group ${currentTheme.cardHover} shadow-[0_2px_10px_rgba(20,20,19,0.01)]`}>
      {/* Delicate Double-Borders inside the card */}
      <div className="absolute inset-1.5 border border-[#e6dfd8]/30 pointer-events-none rounded-[10px]" />
      
      {/* Top Accent Line */}
      <div className={`absolute top-0 left-0 right-0 h-[3px] ${currentTheme.accentBg}`} />

      <div className="flex items-center justify-between mb-4 relative z-10">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[#6c6a64]">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border group-hover:scale-105 transition-transform duration-300 ${currentTheme.iconBg}`}>
          {icon}
        </div>
      </div>
      <p className={`text-4xl font-display font-medium tracking-tight relative z-10 ${currentTheme.valColor}`}>{value}</p>
    </div>
  )
}
