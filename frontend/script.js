// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;
let thinkingTimerInterval = null;
let chatHistoryData = []; // Array of { id, title, messages, timestamp }
let messageReactions = {}; // messageId -> 'up' | 'down' | null

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton;
let themeToggle, sidebarToggle, sidebarOverlay, sidebar;
let chatSearchContainer, chatSearchInput, searchCount, clearSearch, searchToggle;
let chatHistory;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    themeToggle = document.getElementById('themeToggle');
    sidebarToggle = document.getElementById('sidebarToggle');
    sidebarOverlay = document.getElementById('sidebarOverlay');
    sidebar = document.getElementById('sidebar');
    chatSearchContainer = document.getElementById('chatSearchContainer');
    chatSearchInput = document.getElementById('chatSearchInput');
    searchCount = document.getElementById('searchCount');
    clearSearch = document.getElementById('clearSearch');
    searchToggle = document.getElementById('searchToggle');
    chatHistory = document.getElementById('chatHistory');

    loadThemePreference();
    loadChatHistory();
    setupEventListeners();
    createNewSession();
    loadCourseStats();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // New chat button
    newChatButton.addEventListener('click', startNewChat);

    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });

    // Feature 1: Theme toggle
    themeToggle.addEventListener('click', toggleTheme);

    // Feature 5: Sidebar toggle (mobile)
    sidebarToggle.addEventListener('click', toggleSidebar);
    sidebarOverlay.addEventListener('click', closeSidebar);

    // Feature 6: Chat search
    searchToggle.addEventListener('click', toggleSearchBar);
    chatSearchInput.addEventListener('input', performSearch);
    clearSearch.addEventListener('click', clearSearchBar);

    // Keyboard shortcut: Ctrl/Cmd+F to toggle search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            toggleSearchBar();
        }
        // Escape to close search
        if (e.key === 'Escape' && chatSearchContainer.classList.contains('active')) {
            clearSearchBar();
        }
    });
}

// ========================
// FEATURE 1: Theme Toggle
// ========================
function loadThemePreference() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// ========================
// FEATURE 5: Sidebar Toggle
// ========================
function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarToggle.classList.toggle('active');
    sidebarOverlay.classList.toggle('active');
}

function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarToggle.classList.remove('active');
    sidebarOverlay.classList.remove('active');
}

// ========================
// FEATURE 6: Chat Search
// ========================
function toggleSearchBar() {
    chatSearchContainer.classList.toggle('active');
    if (chatSearchContainer.classList.contains('active')) {
        chatSearchInput.focus();
    } else {
        clearSearchBar();
    }
}

function performSearch() {
    const query = chatSearchInput.value.trim().toLowerCase();
    const messages = chatMessages.querySelectorAll('.message');
    let matchCount = 0;

    messages.forEach(msg => {
        const contentEl = msg.querySelector('.message-content');
        if (!contentEl) return;

        // Remove previous highlights
        removeHighlights(contentEl);

        if (!query) {
            msg.classList.remove('search-hidden');
            return;
        }

        const textContent = contentEl.textContent.toLowerCase();
        if (textContent.includes(query)) {
            msg.classList.remove('search-hidden');
            highlightText(contentEl, query);
            matchCount++;
        } else {
            msg.classList.add('search-hidden');
        }
    });

    if (query) {
        searchCount.textContent = `${matchCount} found`;
    } else {
        searchCount.textContent = '';
    }
}

function highlightText(element, query) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null);
    const nodesToReplace = [];

    while (walker.nextNode()) {
        const node = walker.currentNode;
        const idx = node.textContent.toLowerCase().indexOf(query);
        if (idx >= 0) {
            nodesToReplace.push(node);
        }
    }

    nodesToReplace.forEach(node => {
        const text = node.textContent;
        const lowerText = text.toLowerCase();
        const fragment = document.createDocumentFragment();
        let lastIdx = 0;

        let idx = lowerText.indexOf(query, lastIdx);
        while (idx >= 0) {
            if (idx > lastIdx) {
                fragment.appendChild(document.createTextNode(text.slice(lastIdx, idx)));
            }
            const highlight = document.createElement('mark');
            highlight.className = 'search-highlight';
            highlight.textContent = text.slice(idx, idx + query.length);
            fragment.appendChild(highlight);
            lastIdx = idx + query.length;
            idx = lowerText.indexOf(query, lastIdx);
        }

        if (lastIdx < text.length) {
            fragment.appendChild(document.createTextNode(text.slice(lastIdx)));
        }

        node.parentNode.replaceChild(fragment, node);
    });
}

function removeHighlights(element) {
    element.querySelectorAll('.search-highlight').forEach(mark => {
        const parent = mark.parentNode;
        parent.replaceChild(document.createTextNode(mark.textContent), mark);
        parent.normalize();
    });
}

function clearSearchBar() {
    chatSearchInput.value = '';
    searchCount.textContent = '';
    chatSearchContainer.classList.remove('active');

    // Remove all highlights and show all messages
    const messages = chatMessages.querySelectorAll('.message');
    messages.forEach(msg => {
        msg.classList.remove('search-hidden');
        const contentEl = msg.querySelector('.message-content');
        if (contentEl) removeHighlights(contentEl);
    });
}

// ========================
// FEATURE 3: Chat History
// ========================
function loadChatHistory() {
    try {
        const saved = localStorage.getItem('chatHistory');
        if (saved) {
            chatHistoryData = JSON.parse(saved);
        }
    } catch (e) {
        chatHistoryData = [];
    }
    renderChatHistory();
}

function saveChatHistory() {
    // Keep only last 20 sessions
    if (chatHistoryData.length > 20) {
        chatHistoryData = chatHistoryData.slice(-20);
    }
    localStorage.setItem('chatHistory', JSON.stringify(chatHistoryData));
}

function saveCurrentSession() {
    if (!currentSessionId) return;

    const messages = [];
    chatMessages.querySelectorAll('.message').forEach(msg => {
        const contentEl = msg.querySelector('.message-content');
        if (!contentEl) return;
        const isUser = msg.classList.contains('user');
        const isWelcome = msg.classList.contains('welcome-message');
        if (isWelcome) return;
        messages.push({
            type: isUser ? 'user' : 'assistant',
            content: contentEl.innerHTML,
            rawContent: contentEl.textContent
        });
    });

    if (messages.length === 0) return;

    // Use first user message as title
    const firstUserMsg = messages.find(m => m.type === 'user');
    const title = firstUserMsg ? firstUserMsg.rawContent.slice(0, 60) : 'Untitled chat';

    const existingIdx = chatHistoryData.findIndex(h => h.id === currentSessionId);
    const entry = {
        id: currentSessionId,
        title,
        messages,
        timestamp: Date.now()
    };

    if (existingIdx >= 0) {
        chatHistoryData[existingIdx] = entry;
    } else {
        chatHistoryData.push(entry);
    }

    saveChatHistory();
    renderChatHistory();
}

function renderChatHistory() {
    if (!chatHistory) return;

    if (chatHistoryData.length === 0) {
        chatHistory.innerHTML = '<span class="no-history">No past chats</span>';
        return;
    }

    // Show most recent first
    const sorted = [...chatHistoryData].reverse();
    chatHistory.innerHTML = sorted.map(entry => {
        const date = new Date(entry.timestamp);
        const timeStr = formatRelativeTime(date);
        const isActive = entry.id === currentSessionId ? ' active' : '';
        return `
            <div class="history-item${isActive}" data-id="${entry.id}">
                <span class="history-item-text">${escapeHtml(entry.title)}</span>
                <span class="history-item-time">${timeStr}</span>
                <button class="history-item-delete" data-id="${entry.id}" title="Delete">&times;</button>
            </div>
        `;
    }).join('');

    // Add click handlers
    chatHistory.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', (e) => {
            if (e.target.classList.contains('history-item-delete')) return;
            const id = item.getAttribute('data-id');
            restoreSession(id);
        });
    });

    chatHistory.querySelectorAll('.history-item-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = btn.getAttribute('data-id');
            deleteHistoryItem(id);
        });
    });
}

function formatRelativeTime(date) {
    const now = Date.now();
    const diff = now - date.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'now';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function restoreSession(id) {
    const entry = chatHistoryData.find(h => h.id === id);
    if (!entry) return;

    // Save current session before switching
    saveCurrentSession();

    currentSessionId = entry.id;
    chatMessages.innerHTML = '';

    // Add welcome message
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);

    // Restore messages
    entry.messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.type}`;
        messageDiv.id = `message-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        let html = `<div class="message-content">${msg.content}</div>`;
        if (msg.type === 'assistant') {
            html += createMessageActionsHTML(messageDiv.id);
        }
        messageDiv.innerHTML = html;
        chatMessages.appendChild(messageDiv);

        if (msg.type === 'assistant') {
            attachActionListeners(messageDiv, msg.rawContent || messageDiv.querySelector('.message-content').textContent);
        }
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
    renderChatHistory();
    closeSidebar();
}

function deleteHistoryItem(id) {
    chatHistoryData = chatHistoryData.filter(h => h.id !== id);
    saveChatHistory();
    renderChatHistory();
}

// ========================
// Chat Functions
// ========================
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message with timer
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Start thinking timer
    const startTime = Date.now();
    const timerEl = loadingMessage.querySelector('.thinking-timer');
    thinkingTimerInterval = setInterval(() => {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        if (timerEl) timerEl.textContent = `Thinking... ${elapsed}s`;
    }, 100);

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();

        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        clearInterval(thinkingTimerInterval);
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

        // Save to chat history
        saveCurrentSession();

    } catch (error) {
        // Replace loading message with error
        clearInterval(thinkingTimerInterval);
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading-container">
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
                <span class="thinking-timer">Thinking... 0.0s</span>
            </div>
        </div>
    `;
    return messageDiv;
}

// ========================
// FEATURE 2: Copy Button
// FEATURE 7: Reactions
// ========================
function createMessageActionsHTML(messageId) {
    return `
        <div class="message-actions">
            <button class="copy-button" title="Copy to clipboard">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                <span class="copy-label">Copy</span>
            </button>
            <button class="reaction-button" data-reaction="up" title="Helpful">
                <span class="reaction-icon">\u25B2</span>
            </button>
            <button class="reaction-button" data-reaction="down" title="Not helpful">
                <span class="reaction-icon">\u25BC</span>
            </button>
        </div>
    `;
}

function attachActionListeners(messageDiv, rawContent) {
    const messageId = messageDiv.id;

    // Copy button
    const copyBtn = messageDiv.querySelector('.copy-button');
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(rawContent);
                const label = copyBtn.querySelector('.copy-label');
                copyBtn.classList.add('copied');
                label.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.classList.remove('copied');
                    label.textContent = 'Copy';
                }, 2000);
            } catch (e) {
                // Fallback for non-secure contexts
                const textarea = document.createElement('textarea');
                textarea.value = rawContent;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                const label = copyBtn.querySelector('.copy-label');
                copyBtn.classList.add('copied');
                label.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.classList.remove('copied');
                    label.textContent = 'Copy';
                }, 2000);
            }
        });
    }

    // Reaction buttons
    const reactionBtns = messageDiv.querySelectorAll('.reaction-button');
    reactionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const reaction = btn.getAttribute('data-reaction');
            const current = messageReactions[messageId];

            // Toggle: if same reaction clicked again, remove it
            if (current === reaction) {
                messageReactions[messageId] = null;
                btn.classList.remove('active');
            } else {
                // Remove active from all reaction buttons in this message
                reactionBtns.forEach(b => b.classList.remove('active'));
                messageReactions[messageId] = reaction;
                btn.classList.add('active');
            }
        });
    });
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = `message-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = messageId;

    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);

    let html = `<div class="message-content">${displayContent}</div>`;

    if (sources && sources.length > 0) {
        // Deduplicate sources (same HTML string = same source)
        const uniqueSources = [...new Set(sources)];
        const sourceChips = uniqueSources.map(s => `<span class="source-chip">${s}</span>`).join('');
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceChips}</div>
            </details>
        `;
    }

    // Add copy + reaction buttons for assistant messages (not welcome)
    if (type === 'assistant' && !isWelcome) {
        html += createMessageActionsHTML(messageId);
    }

    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Attach event listeners for copy/reactions
    if (type === 'assistant' && !isWelcome) {
        attachActionListeners(messageDiv, content);
    }

    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startNewChat() {
    // Save current session before starting new
    saveCurrentSession();

    // Clear backend session if one exists
    if (currentSessionId) {
        try {
            await fetch(`${API_URL}/sessions/${currentSessionId}`, { method: 'DELETE' });
        } catch (e) {
            // Session cleanup is best-effort
        }
    }
    createNewSession();
    chatInput.focus();
    closeSidebar();
}

function createNewSession() {
    currentSessionId = null;
    chatMessages.innerHTML = '';
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
    renderChatHistory();
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');

        const data = await response.json();
        console.log('Course data received:', data);

        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }

        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }

    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}
