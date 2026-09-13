/**
 * Enterprise AI Employee - Web Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const sessionListEl = document.getElementById('session-list');
  const sessionCountBadge = document.getElementById('session-count-badge');
  const currentSessionIdEl = document.getElementById('current-session-id');
  const currentSessionPill = document.getElementById('current-session-pill');
  const btnNewChat = document.getElementById('btn-new-chat');
  const btnClearCurrent = document.getElementById('btn-clear-current');
  
  const chatViewport = document.getElementById('chat-viewport');
  const welcomeScreen = document.getElementById('welcome-screen');
  const messagesList = document.getElementById('messages-list');
  const typingIndicator = document.getElementById('typing-indicator');

  const composerForm = document.getElementById('composer-form');
  const messageInput = document.getElementById('message-input');
  const btnSend = document.getElementById('btn-send');

  const toolsModal = document.getElementById('tools-modal');
  const btnOpenTools = document.getElementById('btn-open-tools');
  const btnCloseTools = document.getElementById('btn-close-tools');
  const toolsGrid = document.getElementById('tools-grid');
  const toolSearchInput = document.getElementById('tool-search-input');

  // State variables
  let currentSessionId = getOrGenerateSessionId();
  let availableTools = [];

  // Initialize
  init();

  function init() {
    updateSessionIdDisplay();
    fetchSessions();
    fetchTools();
    bindEvents();
  }

  function getOrGenerateSessionId() {
    return 'session-' + Math.random().toString(36).substring(2, 9) + '-' + Date.now().toString(36);
  }

  function updateSessionIdDisplay() {
    if (currentSessionIdEl) {
      currentSessionIdEl.textContent = currentSessionId.substring(0, 18) + '...';
    }
  }

  function bindEvents() {
    // New Chat
    btnNewChat.addEventListener('click', () => {
      currentSessionId = getOrGenerateSessionId();
      updateSessionIdDisplay();
      clearChatViewport();
      fetchSessions();
    });

    // Clear Session
    btnClearCurrent.addEventListener('click', async () => {
      if (confirm('Are you sure you want to clear history for this session?')) {
        try {
          await fetch(`/chat/${currentSessionId}`, { method: 'DELETE' });
          clearChatViewport();
          fetchSessions();
        } catch (e) {
          console.error('Error clearing session:', e);
        }
      }
    });

    // Copy Session ID
    currentSessionPill.addEventListener('click', () => {
      navigator.clipboard.writeText(currentSessionId);
      alert('Copied Session ID to clipboard!');
    });

    // Composer Form Submit
    composerForm.addEventListener('submit', (e) => {
      e.preventDefault();
      handleSendMessage();
    });

    // Auto-resize & Enter key in Textarea
    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + 'px';
    });

    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        composerForm.dispatchEvent(new Event('submit'));
      }
    });

    // Quick Prompt Cards & Chips
    document.addEventListener('click', (e) => {
      const promptCard = e.target.closest('.prompt-card, .chip-btn');
      if (promptCard) {
        const promptText = promptCard.getAttribute('data-prompt');
        if (promptText) {
          messageInput.value = promptText;
          handleSendMessage();
        }
      }
    });

    // Tools Modal Toggle
    btnOpenTools.addEventListener('click', () => {
      toolsModal.classList.remove('hidden');
    });

    btnCloseTools.addEventListener('click', () => {
      toolsModal.classList.add('hidden');
    });

    toolsModal.addEventListener('click', (e) => {
      if (e.target === toolsModal) {
        toolsModal.classList.add('hidden');
      }
    });

    // Search Filter for Tools
    toolSearchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      filterToolsGrid(query);
    });
  }

  // --- API Calls --- //

  async function fetchSessions() {
    try {
      const res = await fetch('/sessions');
      if (!res.ok) return;
      const data = await res.json();
      renderSessions(data.session_ids || []);
    } catch (e) {
      console.error('Failed to fetch sessions:', e);
    }
  }

  function renderSessions(sessionIds) {
    sessionCountBadge.textContent = sessionIds.length;
    sessionListEl.innerHTML = '';

    if (sessionIds.length === 0) {
      sessionListEl.innerHTML = '<div class="empty-state-sm">No active sessions</div>';
      return;
    }

    sessionIds.forEach(id => {
      const item = document.createElement('div');
      item.className = `session-item ${id === currentSessionId ? 'active' : ''}`;
      
      const titleSpan = document.createElement('span');
      titleSpan.className = 'session-title';
      titleSpan.innerHTML = `<i class="fa-regular fa-message"></i> ${id.substring(0, 16)}...`;

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn-delete-session';
      deleteBtn.title = 'Delete Session';
      deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';

      deleteBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await fetch(`/chat/${id}`, { method: 'DELETE' });
        if (id === currentSessionId) {
          currentSessionId = getOrGenerateSessionId();
          updateSessionIdDisplay();
          clearChatViewport();
        }
        fetchSessions();
      });

      item.appendChild(titleSpan);
      item.appendChild(deleteBtn);

      item.addEventListener('click', () => {
        currentSessionId = id;
        updateSessionIdDisplay();
        loadSessionHistory(id);
        fetchSessions();
      });

      sessionListEl.appendChild(item);
    });
  }

  async function loadSessionHistory(sessionId) {
    try {
      const res = await fetch(`/chat/${sessionId}/history`);
      if (!res.ok) return;
      const data = await res.json();
      const history = data.history || [];

      messagesList.innerHTML = '';
      if (history.length > 0) {
        welcomeScreen.classList.add('hidden');
        history.forEach(msg => appendMessage(msg.role === 'user' ? 'user' : 'assistant', msg.text));
      } else {
        welcomeScreen.classList.remove('hidden');
      }
      scrollToBottom();
    } catch (e) {
      console.error('Failed to load history:', e);
    }
  }

  async function fetchTools() {
    try {
      const res = await fetch('/tools');
      if (!res.ok) return;
      const data = await res.json();
      availableTools = data.tools || [];
      document.getElementById('sidebar-tools-badge').textContent = data.total_tools || availableTools.length;
      renderToolsGrid(availableTools);
    } catch (e) {
      console.error('Failed to fetch tools:', e);
    }
  }

  function renderToolsGrid(tools) {
    toolsGrid.innerHTML = '';
    if (tools.length === 0) {
      toolsGrid.innerHTML = '<div class="empty-state">No tools found</div>';
      return;
    }

    tools.forEach(tool => {
      const card = document.createElement('div');
      card.className = 'tool-card';

      card.innerHTML = `
        <div class="tool-card-name">
          <i class="fa-solid fa-gear"></i> ${tool.name}
        </div>
        <div class="tool-card-desc">
          ${escapeHtml(tool.description || 'Enterprise workspace tool.')}
        </div>
      `;
      toolsGrid.appendChild(card);
    });
  }

  function filterToolsGrid(query) {
    const filtered = availableTools.filter(t => 
      t.name.toLowerCase().includes(query) || (t.description && t.description.toLowerCase().includes(query))
    );
    renderToolsGrid(filtered);
  }

  async function handleSendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Hide welcome screen
    welcomeScreen.classList.add('hidden');

    // Append User message
    appendMessage('user', text);
    scrollToBottom();

    // Show typing indicator
    typingIndicator.classList.remove('hidden');
    scrollToBottom();

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: currentSessionId })
      });

      typingIndicator.classList.add('hidden');

      if (!res.ok) {
        const errorData = await res.json();
        appendMessage('assistant', `⚠️ Error: ${errorData.detail || 'Failed to process message'}`);
      } else {
        const data = await res.json();
        if (data.session_id) {
          currentSessionId = data.session_id;
          updateSessionIdDisplay();
        }
        appendMessage('assistant', data.reply);
        fetchSessions();
      }
    } catch (err) {
      typingIndicator.classList.add('hidden');
      appendMessage('assistant', `⚠️ Request failed: ${err.message}`);
    }

    scrollToBottom();
  }

  function appendMessage(sender, text) {
    const row = document.createElement('div');
    row.className = `message-row ${sender}`;

    const isUser = sender === 'user';
    const avatarClass = isUser ? 'user-avatar' : 'assistant-avatar';
    const avatarIcon = isUser ? 'fa-user' : 'fa-robot';

    const formattedContent = isUser ? escapeHtml(text) : formatMarkdown(text);
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    row.innerHTML = `
      <div class="avatar ${avatarClass}">
        <i class="fa-solid ${avatarIcon}"></i>
      </div>
      <div class="message-bubble-wrapper">
        <div class="message-bubble">
          ${formattedContent}
        </div>
        <span class="message-time">${timeStr}</span>
      </div>
    `;

    messagesList.appendChild(row);
  }

  function clearChatViewport() {
    messagesList.innerHTML = '';
    welcomeScreen.classList.remove('hidden');
  }

  function scrollToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  // --- Formatting Helpers --- //

  function formatMarkdown(content) {
    if (!content) return '';

    // Code blocks ```code```
    let html = content.replace(/```([\s\S]*?)```/g, (match, p1) => {
      return `<pre><code>${escapeHtml(p1.trim())}</code></pre>`;
    });

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, (match, p1) => {
      return `<code>${escapeHtml(p1)}</code>`;
    });

    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Bullet points starting with - or *
    html = html.replace(/^[\-*]\s+(.*)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Line breaks to <p>
    const paragraphs = html.split(/\n{2,}/).map(p => {
      if (p.startsWith('<pre>') || p.startsWith('<ul>')) return p;
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    });

    return paragraphs.join('');
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
