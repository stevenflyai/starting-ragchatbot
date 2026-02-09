# Frontend Changes

## Summary

Seven new features were implemented across three frontend files: `index.html`, `style.css`, and `script.js`.

## Files Modified

- `frontend/index.html` — Added new HTML structure for theme toggle, hamburger menu, sidebar overlay, chat history section, and chat search bar
- `frontend/style.css` — Added light theme CSS variables, styles for all 7 new features, and improved responsive design
- `frontend/script.js` — Added all JavaScript logic for the 7 features

## Features Implemented

### 1. Dark/Light Theme Toggle
- **Location**: Sidebar top row, next to "+ NEW CHAT" button
- **How it works**: Sun icon (dark mode) / Moon icon (light mode) toggles between themes. Uses `data-theme` attribute on `<html>` element with CSS custom properties for all colors.
- **Persistence**: Theme preference saved to `localStorage` and restored on page load.

### 2. Message Copy Button
- **Location**: Below each assistant message (appears on hover)
- **How it works**: Clicking "Copy" copies the raw text content of the assistant's response to clipboard. Shows "Copied!" confirmation for 2 seconds. Includes fallback using `document.execCommand('copy')` for non-secure contexts.

### 3. Chat History Sidebar
- **Location**: New collapsible "Chat History" section in the sidebar
- **How it works**: Conversations are automatically saved to `localStorage` after each response. Each entry shows the first user message as title, relative timestamp, and a delete button (visible on hover). Clicking a history item restores that conversation. Maximum of 20 sessions stored.
- **Persistence**: All chat history persisted in `localStorage`.

### 4. Typing Indicator with Elapsed Time
- **Location**: Loading message shown while waiting for API response
- **How it works**: Displays bouncing dots alongside a live timer showing "Thinking... X.Xs" that updates every 100ms. Timer is cleared when the response arrives or an error occurs.

### 5. Responsive Sidebar Toggle (Hamburger Menu)
- **Location**: Fixed position top-left corner, visible only on screens <= 768px
- **How it works**: Three-line hamburger button toggles sidebar as a fixed overlay. Includes animated X transformation when open. Clicking the dark overlay behind the sidebar also closes it. Sidebar slides in from the left with CSS transition.

### 6. Search Within Chat
- **Location**: Search bar above chat messages (toggled via magnifying glass icon next to input, or Ctrl/Cmd+F)
- **How it works**: Typing in the search bar filters messages in real-time. Non-matching messages are hidden. Matching text is highlighted with yellow `<mark>` elements using a DOM TreeWalker for accurate text node targeting. Shows match count. Press Escape or click X to clear.

### 7. Message Reactions/Feedback (Thumbs Up/Down)
- **Location**: Below each assistant message, next to the copy button (appears on hover)
- **How it works**: Up/down arrow buttons toggle reaction state. Only one reaction per message at a time — clicking the same reaction again removes it. Active reaction is highlighted with the primary color. Reactions stored in memory (not persisted to backend).

## CSS Architecture

- Light theme uses `[data-theme="light"]` selector to override CSS custom properties
- New variables added: `--highlight-bg`, `--highlight-text`, `--reaction-bg`, `--reaction-active`
- All color transitions use `0.3s ease` for smooth theme switching
- Mobile breakpoint at 768px converts sidebar to fixed overlay
- Cache-bust version bumped from `v=9` to `v=10` in HTML references
