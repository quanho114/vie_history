# Design Spec: HistoriAI Optimized Multiphase Registration Flow

**Date**: 2026-06-18  
**Topic**: Upgrading the registration system to a premium 2-step flow with comprehensive academic profile attributes.

---

## 1. Product Overview

- **Goal**: Modernize the registration workflow for HistoriAI. Instead of a standard one-step form, we split authentication credentials from the user's research profile. This reduces cognitive load, prevents layout shifting, and captures valuable academic context.
- **Academic Context**: As a premium research assistant, HistoriAI customizes searches based on the user's academic profile. Capturing these attributes (Full Name, Role, Institution) directly during sign-up makes the onboarding experience tailored and elite.
- **Compatibility**: All extra academic fields (`fullName`, `role`, `institution`) are stored within the user's `settings` JSON on the database via a post-registration profile update, avoiding any database migrations.

---

## 2. Detailed Registration Steps & Fields

The registration form will adapt a 2-step wizard flow within the existing Form Card:

### 2.1 Step 1: Account Credentials (Thông tin tài khoản)
- **Email Input**: Standard email address validation.
- **Username Input**: Minimum 3 characters, unique slug.
- **Password Input**: Minimum 8 characters.
- **Confirm Password Input**: Must match password field exactly.
- **Navigation**: "Tiếp theo" button. Translates to Step 2 upon passing client-side validations.

### 2.2 Step 2: Academic Profile (Hồ sơ nghiên cứu)
- **Full Name (Họ và tên)**: String input for academic personalization.
- **Research Role (Vai trò nghiên cứu)**: Custom segmented selector or custom dropdown card.
  - `researcher` (Nhà nghiên cứu / Giảng viên)
  - `student` (Sinh viên / Học sinh)
  - `enthusiast` (Độc giả quan tâm lịch sử)
- **Institution (Đơn vị học thuật/Trường học)**: Text input (optional but highly recommended).
- **Terms Consent Checkbox (Điều khoản & Chính sách)**: Mandatory check to enable registration.
- **Navigation**: "Quay lại" (returns to Step 1) and "Đăng ký thành viên" (submits entire dataset).

---

## 3. Visual Styling & Transitions

To keep consistent with the "Neo-Heritage (Ethereal Archive)" aesthetic, the form components will feature:

- **Height Stability**: The Form Card height will remain completely stable. The two steps will occupy identical heights to prevent any jarring layout shifts.
- **Cinematic Transitions**: We use `framer-motion` for horizontal slide transitions when moving between steps:
  - Moving forward (Step 1 → Step 2): Step 1 slides out to the left, Step 2 slides in from the right.
  - Moving backward (Step 2 → Step 1): Step 2 slides out to the right, Step 1 slides in from the left.
- **Role Select Cards**: Segmented or tactile custom cards styled with thin grey borders (`border-[#E2DFDA]`) that highlight in soft terracotta (`border-[#cc785c] bg-[#cc785c]/5`) when selected.

---

## 4. Validations & Submission Integration

### 4.1 Client-Side Validations
- **Step 1 Validation**:
  - Checks if the email is structurally valid.
  - Ensures the username is at least 3 characters.
  - Validates password length >= 8.
  - Ensures `password === confirmPassword`. If not, raises a clear Vietnamese error message: *"Mật khẩu xác nhận không trùng khớp"*.
- **Step 2 Validation**:
  - Ensures Full Name is filled.
  - Validates that Terms Checkbox is checked.

### 4.2 API Integration Flow
Upon clicking "Đăng ký thành viên":
1. Triggers `authApi.register(email, username, password)`.
2. Once the registration request returns a successful response containing the user object and session token, the client stores the token in `localStorage`.
3. The client immediately dispatches a profile update call `authApi.updateProfile({ settings: { fullName, role, institution } })` to save the extra academic metadata.
4. Activates the application boot transition (`isTransitioning = true` and `isExiting = true`) to prepare the workspace and redirect to `/chat`.

---

## 5. Verification Plan

1. **Tab Switch Test**: Ensure switching between the Login and Register tabs resets the step to Step 1.
2. **Step 1 Validation Test**: Attempt to click "Tiếp theo" with mismatched passwords or empty fields; verify that error alerts appear and block navigation.
3. **Step Navigation Test**: Ensure transitioning back and forth between Step 1 and Step 2 retains the entered inputs.
4. **Step 2 Validation Test**: Verify that the "Đăng ký" button is disabled or triggers validation error if the Terms Checkbox is unchecked or Full Name is empty.
5. **API Payload Verification**: Check the browser's Network tab to confirm that:
   - `/auth/register` is called with `{ email, username, password }`.
   - `/auth/profile` is called with `{ settings: { fullName, role, institution } }` after registration succeeds.
