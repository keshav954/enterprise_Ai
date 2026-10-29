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
  
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  const sidebarToggle = document.getElementById('sidebar-toggle');

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
  let isSending = false;

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

  // --- Sidebar Toggle ---
  function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('active');
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('active');
  }

  function bindEvents() {
    // Sidebar toggle
    sidebarToggle.addEventListener('click', () => {
      if (sidebar.classList.contains('open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    sidebarOverlay.addEventListener('click', closeSidebar);

    // New Chat
    btnNewChat.addEventListener('click', () => {
      currentSessionId = getOrGenerateSessionId();
      updateSessionIdDisplay();
      clearChatViewport();
      fetchSessions();
      closeSidebar();
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
      navigator.clipboard.writeText(currentSessionId).then(() => {
        const pill = currentSessionPill;
        pill.style.borderColor = '#10b981';
        setTimeout(() => { pill.style.borderColor = ''; }, 1200);
      });
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
      closeSidebar();
    });

    btnCloseTools.addEventListener('click', () => {
      toolsModal.classList.add('hidden');
    });

    toolsModal.addEventListener('click', (e) => {
      if (e.target === toolsModal) {
        toolsModal.classList.add('hidden');
      }
    });

    // Escape key to close modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        toolsModal.classList.add('hidden');
        closeSidebar();
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
        closeSidebar();
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

    // Categorize tools
    const categories = {
      'Company': ['get_company_info'],
      'Workspace': ['list_workspace_files', 'read_workspace_file', 'write_workspace_file', 'append_workspace_file', 'delete_workspace_file', 'create_workspace_folder', 'delete_workspace_folder', 'rename_workspace_item', 'move_workspace_item', 'copy_workspace_item', 'workspace_tree', 'workspace_summary', 'get_file_information', 'count_workspace_files'],
      'Search': ['search_workspace_files', 'search_text_in_workspace', 'search_workspace_text', 'find_workspace_files'],
      'Code': ['read_multiple_workspace_files', 'read_workspace_lines', 'replace_text_in_file', 'list_python_files'],
      'Knowledge Base': ['search_knowledge_base', 'rebuild_knowledge_base'],
    };

    const categoryIcons = {
      'Company': 'fa-building',
      'Workspace': 'fa-folder-open',
      'Search': 'fa-magnifying-glass',
      'Code': 'fa-code',
      'Knowledge Base': 'fa-brain',
    };

    const categoryColors = {
      'Company': '#06b6d4',
      'Workspace': '#10b981',
      'Search': '#f59e0b',
      'Code': '#8b5cf6',
      'Knowledge Base': '#ec4899',
    };

    tools.forEach(tool => {
      let toolCategory = 'Other';
      for (const [cat, names] of Object.entries(categories)) {
        if (names.includes(tool.name)) {
          toolCategory = cat;
          break;
        }
      }

      const card = document.createElement('div');
      card.className = 'tool-card';
      const iconClass = categoryIcons[toolCategory] || 'fa-gear';
      const iconColor = categoryColors[toolCategory] || 'var(--accent-cyan)';

      card.innerHTML = `
        <div class="tool-card-header">
          <span class="tool-category-tag" style="color: ${iconColor}; border-color: ${iconColor}30; background: ${iconColor}15;">
            <i class="fa-solid ${iconClass}"></i> ${toolCategory}
          </span>
        </div>
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
    if (!text || isSending) return;

    isSending = true;

    // Reset input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Disable send button
    btnSend.disabled = true;
    btnSend.style.opacity = '0.5';

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

        // Show tools used if any
        if (data.tools_executed && data.tools_executed.length > 0) {
          const toolsSummary = data.tools_executed.map(t => 
            `🔧 **${t.tool}**`
          ).join('\n');
          appendToolsInfo(data.tools_executed);
        }

        appendMessage('assistant', data.reply);
        fetchSessions();
      }
    } catch (err) {
      typingIndicator.classList.add('hidden');
      appendMessage('assistant', `⚠️ Request failed: ${err.message}`);
    }

    isSending = false;
    btnSend.disabled = false;
    btnSend.style.opacity = '1';
    scrollToBottom();
  }

  function appendToolsInfo(tools) {
    const row = document.createElement('div');
    row.className = 'tools-executed-banner';

    const toolNames = tools.map(t => t.tool).join(', ');
    row.innerHTML = `
      <i class="fa-solid fa-wrench"></i>
      <span>Tools used: <strong>${escapeHtml(toolNames)}</strong></span>
      <span class="tools-count">${tools.length} tool${tools.length > 1 ? 's' : ''}</span>
    `;

    messagesList.appendChild(row);
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
    requestAnimationFrame(() => {
      chatViewport.scrollTop = chatViewport.scrollHeight;
    });
  }

  // --- Formatting Helpers --- //

  function formatMarkdown(content) {
    if (!content) return '';

    // Code blocks ```code```
    let html = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, p1) => {
      return `<pre><code class="lang-${lang}">${escapeHtml(p1.trim())}</code></pre>`;
    });

    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, (match, p1) => {
      return `<code>${escapeHtml(p1)}</code>`;
    });

    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Headers ## text
    html = html.replace(/^### (.*)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.*)$/gm, '<h2>$1</h2>');

    // Bullet points starting with - or *
    html = html.replace(/^[\-*]\s+(.*)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Numbered lists
    html = html.replace(/^\d+\.\s+(.*)$/gm, '<li>$1</li>');

    // Line breaks to <p>
    const paragraphs = html.split(/\n{2,}/).map(p => {
      if (p.startsWith('<pre>') || p.startsWith('<ul>') || p.startsWith('<h')) return p;
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
