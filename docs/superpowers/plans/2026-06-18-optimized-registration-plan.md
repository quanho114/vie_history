# HistoriAI Optimized Multiphase Registration Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a modern, high-end 2-step registration workflow that splits credentials from academic profiles to reduce cognitive load and collect professional researcher context without database migrations.

**Architecture:** Use local React state to track the active step (`registerStep: 1 | 2`) and form fields. Transition between Step 1 and Step 2 using Framer Motion slide animations. Upon successful registration API response, trigger a background profile update request to save the additional academic metadata (`fullName`, `role`, `institution`) in the user settings JSON.

**Tech Stack:** React, TypeScript, TailwindCSS, Framer Motion, Zustand

---

### Task 1: Initialize New State Variables & Validation Helpers

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx:75-90`

- [ ] **Step 1: Add new local state variables for Step 2 registration attributes**

Add these state definitions inside `LoginPage` component:
```typescript
  const [registerStep, setRegisterStep] = useState<1 | 2>(1);
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState("enthusiast");
  const [institution, setInstitution] = useState("");
  const [agreeTerms, setAgreeTerms] = useState(false);
```

- [ ] **Step 2: Add validation logic helpers for Step 1 credentials**

Create a helper function to validate Step 1 fields before allowing transitioning to Step 2:
```typescript
  const validateStep1 = (): boolean => {
    useAuthStore.setState({ error: null });
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      useAuthStore.setState({ error: "Email không hợp lệ" });
      return false;
    }
    if (username.trim().length < 3) {
      useAuthStore.setState({ error: "Tên người dùng phải có ít nhất 3 ký tự" });
      return false;
    }
    if (password.length < 8) {
      useAuthStore.setState({ error: "Mật khẩu phải có ít nhất 8 ký tự" });
      return false;
    }
    if (password !== confirmPassword) {
      useAuthStore.setState({ error: "Mật khẩu xác nhận không trùng khớp" });
      return false;
    }
    return true;
  };
```

- [ ] **Step 3: Reset step counter when switching tabs**

Locate the `setIsRegister` calls and modify them to reset `registerStep` to `1` and clean up fields:
```typescript
  // In the active tab trigger handles:
  onClick={() => {
    setIsRegister(false);
    setRegisterStep(1);
    useAuthStore.setState({ error: null });
  }}
```

- [ ] **Step 4: Commit state and validation changes**

Run:
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat(auth): add multiphase registration states and step 1 validation logic"
```

---

### Task 2: Build the Multiphase Form UI & Sliding Transitions

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx:415-545`

- [ ] **Step 1: Implement the slide transition variants**

Define variants for horizontal page sliding animations:
```typescript
const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 100 : -100,
    opacity: 0
  }),
  center: {
    x: 0,
    opacity: 1
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 100 : -100,
    opacity: 0
  })
};
```

- [ ] **Step 2: Re-structure the register inputs section to support steps**

In the form body, replace the single list of fields with conditional rendering based on `registerStep`. Wrap them in an `<AnimatePresence mode="wait">`:
```tsx
              <form onSubmit={handleSubmit} className="space-y-4 overflow-hidden relative min-h-[340px]">
                <AnimatePresence initial={false} custom={registerStep}>
                  {registerStep === 1 ? (
                    <motion.div
                      key="step1"
                      custom={1}
                      variants={slideVariants}
                      initial="enter"
                      animate="center"
                      exit="exit"
                      transition={{ duration: 0.2 }}
                      className="space-y-4"
                    >
                      {/* Email */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Email</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <Mail size={14} />
                          </span>
                          <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            placeholder="you@example.com"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      {/* Username */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Tên người dùng</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <User size={14} />
                          </span>
                          <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            minLength={3}
                            placeholder="yourname"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      {/* Password */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Mật khẩu</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <Lock size={14} />
                          </span>
                          <input
                            type={showPassword ? "text" : "password"}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                            placeholder="••••••••"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-10 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      {/* Confirm Password */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Xác nhận mật khẩu</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <Lock size={14} />
                          </span>
                          <input
                            type={showPassword ? "text" : "password"}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            minLength={8}
                            placeholder="••••••••"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-10 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => {
                          if (validateStep1()) {
                            setRegisterStep(2);
                          }
                        }}
                        className="w-full bg-[#cc785c] hover:bg-[#b86246] text-white py-3 px-4 rounded-xl text-xs font-semibold tracking-wider uppercase flex items-center justify-center gap-2 cursor-pointer transition-all duration-200 active:scale-[0.98] mt-4 border border-[#b86246]/10"
                      >
                        <span>Tiếp tục thiết lập hồ sơ</span>
                        <ArrowRight size={14} />
                      </button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="step2"
                      custom={2}
                      variants={slideVariants}
                      initial="enter"
                      animate="center"
                      exit="exit"
                      transition={{ duration: 0.2 }}
                      className="space-y-4"
                    >
                      {/* Full Name */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Họ và tên *</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <User size={14} />
                          </span>
                          <input
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            required
                            placeholder="Nguyễn Văn A"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      {/* Research Role */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Vai trò nghiên cứu *</label>
                        <select
                          value={role}
                          onChange={(e) => setRole(e.target.value)}
                          className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 px-3 text-sm text-[#2D2A26] outline-none focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                        >
                          <option value="researcher">Nhà nghiên cứu / Giảng viên</option>
                          <option value="student">Học sinh / Sinh viên</option>
                          <option value="enthusiast">Độc giả tự do</option>
                        </select>
                      </div>

                      {/* Institution */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase tracking-wider text-[#6C6A64] block">Đơn vị công tác / Trường học</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-[#9F9D99]">
                            <BookOpen size={14} />
                          </span>
                          <input
                            type="text"
                            value={institution}
                            onChange={(e) => setInstitution(e.target.value)}
                            placeholder="Ví dụ: Đại học Quốc gia Hà Nội"
                            className="w-full bg-[#FBFBFA] border border-[#E2DFDA] rounded-xl py-2.5 pl-9 pr-4 text-sm text-[#2D2A26] outline-none placeholder:text-[#A8A59E] focus:bg-white focus:border-[#cc785c] focus:ring-4 focus:ring-[#cc785c]/10 transition-all duration-200 box-border shadow-[0_1px_2px_rgba(0,0,0,0.01)]"
                          />
                        </div>
                      </div>

                      {/* Agree to Terms */}
                      <label className="flex items-start gap-2.5 pt-1 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={agreeTerms}
                          onChange={(e) => setAgreeTerms(e.target.checked)}
                          required
                          className="mt-0.5 rounded border-[#E2DFDA] text-[#cc785c] focus:ring-[#cc785c] transition-all cursor-pointer"
                        />
                        <span className="text-[11px] text-[#6C6A64] leading-normal">
                          Tôi đồng ý với điều khoản sử dụng & chính sách học thuật của hệ thống.
                        </span>
                      </label>

                      <div className="flex gap-3 pt-2">
                        <button
                          type="button"
                          onClick={() => setRegisterStep(1)}
                          className="flex-1 bg-white hover:bg-[#F9F8F6] text-[#6C6A64] border border-[#E5E3DF] py-3 px-4 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 active:scale-[0.98]"
                        >
                          Quay lại
                        </button>
                        <button
                          type="submit"
                          disabled={isLoading || !fullName.trim() || !agreeTerms}
                          className="flex-1 bg-[#cc785c] hover:bg-[#b86246] text-white py-3 px-4 rounded-xl text-xs font-semibold tracking-wider uppercase flex items-center justify-center gap-2 cursor-pointer transition-all duration-200 active:scale-[0.98] border border-[#b86246]/10 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isLoading ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <>
                              <LogIn size={14} />
                              <span>Đăng ký</span>
                            </>
                          )}
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>
```

- [ ] **Step 3: Commit UI code changes**

Run:
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat(auth): build multi-step UI layout with horizontal slide animations"
```

---

### Task 3: Integrate Registration Submission with Settings Synchronization

**Files:**
- Modify: `apps/web/src/pages/LoginPage.tsx:246-270`

- [ ] **Step 1: Update the submit handler to update the profile with academic details**

Inside `handleSubmit`, implement registration post-update hook:
```typescript
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isRegister) {
      if (!fullName.trim()) {
        useAuthStore.setState({ error: "Vui lòng nhập họ và tên" });
        return;
      }
      if (!agreeTerms) {
        useAuthStore.setState({ error: "Bạn phải đồng ý với điều khoản sử dụng" });
        return;
      }
    }
    
    useAuthStore.setState({ isLoading: true, error: null });
    try {
      let response;
      if (isRegister) {
        // Step 1: Register credentials
        response = await authApi.register(email, username, password);
        
        // Step 2: Synchronize academic metadata inside settings using the returned token
        if (response.access_token) {
          localStorage.setItem("token", response.access_token);
          try {
            await authApi.updateProfile({
              settings: {
                fullName,
                role,
                institution,
              }
            });
          } catch (profileErr) {
            console.error("Failed to sync academic profile settings:", profileErr);
            // Non-blocking for registration success
          }
        }
      } else {
        response = await authApi.login(email, password);
      }
      
      const target = "/chat";
      setTransitionTarget(target);
      setPendingAuthResponse(response);
      setIsTransitioning(true);
      useAuthStore.setState({ isLoading: false });
    } catch (err: any) {
      useAuthStore.setState({
        error: err.message || "Đăng ký hoặc đăng nhập thất bại",
        isLoading: false,
      });
    }
  };
```

- [ ] **Step 2: Commit API integration changes**

Run:
```bash
git add apps/web/src/pages/LoginPage.tsx
git commit -m "feat(auth): sync registration academic details to profile settings"
```

---

### Task 3: Verification & Build Integrity Check

- [ ] **Step 1: Verify web app build builds successfully**

Run: `npm run build` inside `apps/web`
Expected: Done without any TypeScript errors in LoginPage.tsx

- [ ] **Step 2: Verify tab toggle resets states**

Ensure that changing tabs resets `registerStep` to `1` and clears inputs correctly.
