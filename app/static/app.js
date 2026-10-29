/**
 * Enterprise AI Employee - Web Dashboard Controller
 * Full-featured interactive frontend with RAG Knowledge Base management,
 * Auth token configuration, interactive tool details, and chat export.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements - Navigation & Sessions
  const sessionListEl = document.getElementById('session-list');
  const sessionCountBadge = document.getElementById('session-count-badge');
  const currentSessionIdEl = document.getElementById('current-session-id');
  const currentSessionPill = document.getElementById('current-session-pill');
  const btnNewChat = document.getElementById('btn-new-chat');
  const btnClearCurrent = document.getElementById('btn-clear-current');
  const btnExportChat = document.getElementById('btn-export-chat');
  const headerModelName = document.getElementById('header-model-name');
  
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');

  // DOM Elements - Chat
  const chatViewport = document.getElementById('chat-viewport');
  const welcomeScreen = document.getElementById('welcome-screen');
  const messagesList = document.getElementById('messages-list');
  const typingIndicator = document.getElementById('typing-indicator');

  const composerForm = document.getElementById('composer-form');
  const messageInput = document.getElementById('message-input');
  const btnSend = document.getElementById('btn-send');

  // DOM Elements - Tools Modal
  const toolsModal = document.getElementById('tools-modal');
  const btnOpenTools = document.getElementById('btn-open-tools');
  const btnCloseTools = document.getElementById('btn-close-tools');
  const toolsGrid = document.getElementById('tools-grid');
  const toolSearchInput = document.getElementById('tool-search-input');

  // DOM Elements - Knowledge Base Modal
  const kbModal = document.getElementById('kb-modal');
  const btnOpenKb = document.getElementById('btn-open-kb');
  const btnCloseKb = document.getElementById('btn-close-kb');
  const kbStatDocs = document.getElementById('kb-stat-docs');
  const kbStatChunks = document.getElementById('kb-stat-chunks');
  const kbDocsList = document.getElementById('kb-docs-list');
  const btnRebuildKb = document.getElementById('btn-rebuild-kb');
  const kbUploadForm = document.getElementById('kb-upload-form');
  const fileDropzone = document.getElementById('file-dropzone');
  const kbFileInput = document.getElementById('kb-file-input');
  const btnUploadDoc = document.getElementById('btn-upload-doc');
  const dropzoneLabel = document.getElementById('dropzone-label');
  const kbUploadStatus = document.getElementById('kb-upload-status');

  // DOM Elements - Settings Modal
  const settingsModal = document.getElementById('settings-modal');
  const btnOpenSettings = document.getElementById('btn-open-settings');
  const btnCloseSettings = document.getElementById('btn-close-settings');
  const settingsAuthToken = document.getElementById('settings-auth-token');
  const btnToggleTokenVisibility = document.getElementById('btn-toggle-token-visibility');
  const btnSaveToken = document.getElementById('btn-save-token');
  const diagStatus = document.getElementById('diag-status');
  const diagVersion = document.getElementById('diag-version');
  const diagModel = document.getElementById('diag-model');
  const diagGeminiKey = document.getElementById('diag-gemini-key');

  // State variables
  let currentSessionId = getOrGenerateSessionId();
  let availableTools = [];
  let isSending = false;
  let selectedUploadFile = null;

  // Initialize
  init();

  function init() {
    updateSessionIdDisplay();
    loadSavedToken();
    checkHealth();
    fetchSessions();
    fetchTools();
    fetchKbStats();
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

  // --- Auth Token Helpers --- //
  function getAuthToken() {
    return localStorage.getItem('enterprise_ai_auth_token') || '';
  }

  function setAuthToken(token) {
    if (token) {
      localStorage.setItem('enterprise_ai_auth_token', token.trim());
    } else {
      localStorage.removeItem('enterprise_ai_auth_token');
    }
  }

  function loadSavedToken() {
    if (settingsAuthToken) {
      settingsAuthToken.value = getAuthToken();
    }
  }

  function getAuthHeaders(extraHeaders = {}) {
    const headers = { ...extraHeaders };
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  // --- Sidebar Toggle --- //
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
          await fetch(`/chat/${currentSessionId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
          });
          clearChatViewport();
          fetchSessions();
          showToast('Session history cleared');
        } catch (e) {
          console.error('Error clearing session:', e);
          showToast('Failed to clear session', true);
        }
      }
    });

    // Copy Session ID
    currentSessionPill.addEventListener('click', () => {
      navigator.clipboard.writeText(currentSessionId).then(() => {
        showToast('Session ID copied to clipboard');
      });
    });

    // Export Chat History
    if (btnExportChat) {
      btnExportChat.addEventListener('click', exportChatHistory);
    }

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

    // Quick Prompt Cards & Action Chips
    document.addEventListener('click', (e) => {
      const promptCard = e.target.closest('.prompt-card, .chip-btn');
      if (promptCard) {
        const promptText = promptCard.getAttribute('data-prompt');
        if (promptText) {
          messageInput.value = promptText;
          handleSendMessage();
        }
      }

      // Code Block Copy Button click
      const copyBtn = e.target.closest('.code-copy-btn');
      if (copyBtn) {
        const pre = copyBtn.closest('.code-block-wrapper').querySelector('pre');
        if (pre) {
          navigator.clipboard.writeText(pre.innerText).then(() => {
            copyBtn.classList.add('copied');
            copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
            setTimeout(() => {
              copyBtn.classList.remove('copied');
              copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
            }, 1800);
          });
        }
      }

      // Tools Accordion Toggle
      const accordionSummary = e.target.closest('.tools-accordion-summary');
      if (accordionSummary) {
        const accordion = accordionSummary.closest('.tools-accordion');
        if (accordion) {
          accordion.classList.toggle('open');
          const chevron = accordionSummary.querySelector('.chevron-icon');
          if (chevron) {
            chevron.style.transform = accordion.classList.contains('open') ? 'rotate(180deg)' : 'rotate(0deg)';
          }
        }
      }
    });

    // Tools Modal Toggle
    btnOpenTools.addEventListener('click', () => {
      toolsModal.classList.remove('hidden');
      closeSidebar();
    });
    btnCloseTools.addEventListener('click', () => toolsModal.classList.add('hidden'));

    // Knowledge Base Modal Toggle
    if (btnOpenKb) {
      btnOpenKb.addEventListener('click', () => {
        kbModal.classList.remove('hidden');
        closeSidebar();
        fetchKbStats();
        fetchKbDocuments();
      });
    }
    if (btnCloseKb) {
      btnCloseKb.addEventListener('click', () => kbModal.classList.add('hidden'));
    }

    // Settings Modal Toggle
    if (btnOpenSettings) {
      btnOpenSettings.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
        closeSidebar();
        loadSavedToken();
        checkHealth();
      });
    }
    if (btnCloseSettings) {
      btnCloseSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));
    }

    // Modal background clicks to dismiss
    [toolsModal, kbModal, settingsModal].forEach(modal => {
      if (!modal) return;
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      });
    });

    // Escape key to close any active modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        [toolsModal, kbModal, settingsModal].forEach(m => m && m.classList.add('hidden'));
        closeSidebar();
      }
    });

    // Search Filter for Tools
    toolSearchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      filterToolsGrid(query);
    });

    // KB Dropzone & Upload
    if (fileDropzone) {
      fileDropzone.addEventListener('click', () => kbFileInput.click());

      fileDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropzone.classList.add('drag-over');
      });

      fileDropzone.addEventListener('dragleave', () => {
        fileDropzone.classList.remove('drag-over');
      });

      fileDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropzone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
          handleFileSelected(e.dataTransfer.files[0]);
        }
      });

      kbFileInput.addEventListener('change', () => {
        if (kbFileInput.files.length > 0) {
          handleFileSelected(kbFileInput.files[0]);
        }
      });
    }

    if (kbUploadForm) {
      kbUploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        handleDocumentUpload();
      });
    }

    if (btnRebuildKb) {
      btnRebuildKb.addEventListener('click', handleRebuildIndex);
    }

    // Settings Token Save
    if (btnSaveToken) {
      btnSaveToken.addEventListener('click', () => {
        setAuthToken(settingsAuthToken.value);
        showToast('API token saved');
      });
    }

    if (btnToggleTokenVisibility) {
      btnToggleTokenVisibility.addEventListener('click', () => {
        const isPassword = settingsAuthToken.type === 'password';
        settingsAuthToken.type = isPassword ? 'text' : 'password';
        btnToggleTokenVisibility.innerHTML = isPassword ? '<i class="fa-solid fa-eye-slash"></i>' : '<i class="fa-solid fa-eye"></i>';
      });
    }
  }

  // --- File Selection for Knowledge Base --- //
  function handleFileSelected(file) {
    const validExtensions = ['.md', '.txt'];
    const hasValidExt = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    if (!hasValidExt) {
      showKbStatus('Only .md and .txt files are supported.', 'error');
      selectedUploadFile = null;
      btnUploadDoc.disabled = true;
      fileDropzone.classList.remove('has-file');
      return;
    }

    selectedUploadFile = file;
    btnUploadDoc.disabled = false;
    fileDropzone.classList.add('has-file');
    dropzoneLabel.innerHTML = `Selected file: <strong>${escapeHtml(file.name)}</strong> (${(file.size / 1024).toFixed(1)} KB)`;
    hideKbStatus();
  }

  // --- API Calls --- //

  async function checkHealth() {
    try {
      const res = await fetch('/health');
      if (!res.ok) throw new Error('Health check failed');
      const data = await res.json();

      if (statusDot) statusDot.className = 'status-dot online';
      if (statusText) statusText.textContent = 'System Online';

      if (headerModelName && data.model) {
        headerModelName.textContent = data.model;
      }

      if (diagStatus) {
        diagStatus.textContent = 'Healthy';
        diagStatus.className = 'diag-value badge-ok';
      }
      if (diagVersion) diagVersion.textContent = data.version || '0.4.0';
      if (diagModel) diagModel.textContent = data.model || 'Gemini';
      if (diagGeminiKey) {
        if (data.gemini_configured) {
          diagGeminiKey.textContent = 'Configured';
          diagGeminiKey.className = 'diag-value badge-ok';
        } else {
          diagGeminiKey.textContent = 'Missing / Not set';
          diagGeminiKey.className = 'diag-value badge-warn';
        }
      }
    } catch (e) {
      if (statusDot) statusDot.className = 'status-dot offline';
      if (statusText) statusText.textContent = 'Service Offline';
      if (diagStatus) {
        diagStatus.textContent = 'Offline';
        diagStatus.className = 'diag-value badge-warn';
      }
    }
  }

  async function fetchSessions() {
    try {
      const res = await fetch('/sessions', { headers: getAuthHeaders() });
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
      titleSpan.innerHTML = `<i class="fa-regular fa-message"></i> ${escapeHtml(id.substring(0, 16))}...`;

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn-delete-session';
      deleteBtn.title = 'Delete Session';
      deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';

      deleteBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await fetch(`/chat/${id}`, {
          method: 'DELETE',
          headers: getAuthHeaders(),
        });
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
      const res = await fetch(`/chat/${sessionId}/history`, { headers: getAuthHeaders() });
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
      const res = await fetch('/tools', { headers: getAuthHeaders() });
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

    const categories = {
      'Company': ['get_company_info'],
      'Workspace': [
        'list_workspace_files', 'read_workspace_file', 'write_workspace_file',
        'append_workspace_file', 'delete_workspace_file', 'create_workspace_folder',
        'delete_workspace_folder', 'rename_workspace_item', 'move_workspace_item',
        'copy_workspace_item', 'workspace_tree', 'workspace_summary',
        'get_file_information', 'count_workspace_files'
      ],
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
          <i class="fa-solid fa-gear"></i> ${escapeHtml(tool.name)}
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

  // --- Knowledge Base (RAG) API & Rendering --- //

  async function fetchKbStats() {
    try {
      const res = await fetch('/knowledge-base/stats');
      if (!res.ok) return;
      const data = await res.json();
      if (kbStatDocs) kbStatDocs.textContent = data.documents || 0;
      if (kbStatChunks) kbStatChunks.textContent = data.chunks || 0;
    } catch (e) {
      console.error('Failed to fetch KB stats:', e);
    }
  }

  async function fetchKbDocuments() {
    if (!kbDocsList) return;
    try {
      const res = await fetch('/knowledge-base/documents');
      if (!res.ok) {
        kbDocsList.innerHTML = '<div class="empty-state">Could not load documents</div>';
        return;
      }
      const data = await res.json();
      const docs = data.documents || [];

      if (docs.length === 0) {
        kbDocsList.innerHTML = '<div class="empty-state">No documents indexed in knowledge_base/ yet</div>';
        return;
      }

      let html = `
        <table class="kb-docs-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Size</th>
              <th>Last Modified</th>
            </tr>
          </thead>
          <tbody>
      `;

      docs.forEach(d => {
        const sizeFormatted = d.size_bytes < 1024 ? `${d.size_bytes} B` : `${(d.size_bytes / 1024).toFixed(1)} KB`;
        const dateFormatted = new Date(d.last_modified * 1000).toLocaleDateString();
        html += `
          <tr>
            <td><i class="fa-regular fa-file-lines doc-icon"></i> ${escapeHtml(d.filename)}</td>
            <td>${sizeFormatted}</td>
            <td>${dateFormatted}</td>
          </tr>
        `;
      });

      html += '</tbody></table>';
      kbDocsList.innerHTML = html;
    } catch (e) {
      kbDocsList.innerHTML = '<div class="empty-state">Failed to fetch documents</div>';
    }
  }

  async function handleRebuildIndex() {
    btnRebuildKb.disabled = true;
    btnRebuildKb.classList.add('loading');
    btnRebuildKb.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Rebuilding...';

    try {
      const res = await fetch('/knowledge-base/rebuild', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      const data = await res.json();

      if (res.ok) {
        showToast('Knowledge Base index rebuilt successfully');
        fetchKbStats();
        fetchKbDocuments();
      } else {
        showToast(data.detail || 'Failed to rebuild index', true);
      }
    } catch (e) {
      showToast(`Rebuild error: ${e.message}`, true);
    } finally {
      btnRebuildKb.disabled = false;
      btnRebuildKb.classList.remove('loading');
      btnRebuildKb.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Rebuild Index';
    }
  }

  async function handleDocumentUpload() {
    if (!selectedUploadFile) return;

    btnUploadDoc.disabled = true;
    btnUploadDoc.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading & Indexing...';

    const formData = new FormData();
    formData.append('file', selectedUploadFile);

    try {
      const res = await fetch('/knowledge-base/upload', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        showKbStatus(`✓ ${data.message}`, 'success');
        showToast('Document uploaded and indexed');
        selectedUploadFile = null;
        fileDropzone.classList.remove('has-file');
        dropzoneLabel.innerHTML = 'Drag & drop <code>.md</code> or <code>.txt</code> file here, or click to browse';
        kbFileInput.value = '';
        fetchKbStats();
        fetchKbDocuments();
      } else {
        showKbStatus(`⚠️ ${data.detail || 'Upload failed'}`, 'error');
      }
    } catch (e) {
      showKbStatus(`⚠️ Upload error: ${e.message}`, 'error');
    } finally {
      btnUploadDoc.disabled = !selectedUploadFile;
      btnUploadDoc.innerHTML = '<i class="fa-solid fa-upload"></i> Upload & Re-Index';
    }
  }

  function showKbStatus(msg, type) {
    if (!kbUploadStatus) return;
    kbUploadStatus.textContent = msg;
    kbUploadStatus.className = `kb-status-alert ${type}`;
    kbUploadStatus.classList.remove('hidden');
  }

  function hideKbStatus() {
    if (kbUploadStatus) kbUploadStatus.classList.add('hidden');
  }

  // --- Export Chat History --- //

  async function exportChatHistory() {
    try {
      const res = await fetch(`/chat/${currentSessionId}/history`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Could not fetch history');
      const data = await res.json();
      const history = data.history || [];

      if (history.length === 0) {
        showToast('No messages to export', true);
        return;
      }

      let markdown = `# Enterprise AI Employee - Chat Export\n`;
      markdown += `**Session ID:** \`${currentSessionId}\`  \n`;
      markdown += `**Date:** ${new Date().toLocaleString()}  \n\n---\n\n`;

      history.forEach(item => {
        const roleName = item.role === 'user' ? 'User' : 'Enterprise AI Employee';
        markdown += `### ${roleName}\n\n${item.text}\n\n`;
      });

      const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `${currentSessionId}.md`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showToast('Chat history exported as Markdown');
    } catch (e) {
      showToast(`Export failed: ${e.message}`, true);
    }
  }

  // --- Chat Message Sending & Tool Rendering --- //

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
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ message: text, session_id: currentSessionId })
      });

      typingIndicator.classList.add('hidden');

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMsg = errorData.detail || `Server returned ${res.status}`;
        appendMessage('assistant', `⚠️ **Error:** ${errorMsg}`);
      } else {
        const data = await res.json();
        if (data.session_id) {
          currentSessionId = data.session_id;
          updateSessionIdDisplay();
        }

        // Show tools used with interactive accordion
        if (data.tools_executed && data.tools_executed.length > 0) {
          appendToolsAccordion(data.tools_executed);
        }

        appendMessage('assistant', data.reply);
        fetchSessions();
      }
    } catch (err) {
      typingIndicator.classList.add('hidden');
      appendMessage('assistant', `⚠️ **Network error:** ${err.message}`);
    }

    isSending = false;
    btnSend.disabled = false;
    btnSend.style.opacity = '1';
    scrollToBottom();
  }

  function appendToolsAccordion(tools) {
    const accordion = document.createElement('div');
    accordion.className = 'tools-accordion';

    const toolCount = tools.length;
    const toolNames = tools.map(t => t.tool).join(', ');

    let detailsHtml = '';
    tools.forEach((t, i) => {
      const argsFormatted = typeof t.args === 'object' ? JSON.stringify(t.args, null, 2) : String(t.args);
      detailsHtml += `
        <div class="tool-detail-item">
          <div class="tool-detail-title">
            <i class="fa-solid fa-wrench"></i> ${i + 1}. <strong>${escapeHtml(t.tool)}</strong>
          </div>
          <div class="tool-detail-body"><strong>Args:</strong>\n${escapeHtml(argsFormatted)}\n\n<strong>Result Snippet:</strong>\n${escapeHtml(t.result_snippet || '')}</div>
        </div>
      `;
    });

    accordion.innerHTML = `
      <div class="tools-accordion-summary">
        <span><i class="fa-solid fa-bolt"></i> Executed <strong>${toolCount} tool${toolCount > 1 ? 's' : ''}</strong> (${escapeHtml(toolNames)})</span>
        <i class="fa-solid fa-chevron-down chevron-icon" style="transition: transform 0.2s;"></i>
      </div>
      <div class="tools-accordion-content">
        ${detailsHtml}
      </div>
    `;

    messagesList.appendChild(accordion);
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

  // --- Toast Notification Helper --- //

  function showToast(message, isError = false) {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    if (isError) {
      toast.style.borderColor = '#ef4444';
      toast.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i> <span>${escapeHtml(message)}</span>`;
    } else {
      toast.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10b981;"></i> <span>${escapeHtml(message)}</span>`;
    }

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  // --- Formatting Helpers --- //

  function formatMarkdown(content) {
    if (!content) return '';

    // Code blocks ```code``` with header and copy button
    let html = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, p1) => {
      const language = lang || 'code';
      return `
        <div class="code-block-wrapper">
          <div class="code-block-header">
            <span>${escapeHtml(language)}</span>
            <button class="code-copy-btn" type="button"><i class="fa-regular fa-copy"></i> Copy</button>
          </div>
          <pre><code class="lang-${escapeHtml(language)}">${escapeHtml(p1.trim())}</code></pre>
        </div>
      `;
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

    // Paragraph line breaks
    const paragraphs = html.split(/\n{2,}/).map(p => {
      if (p.startsWith('<div class="code-block-wrapper"') || p.startsWith('<ul>') || p.startsWith('<h')) {
        return p;
      }
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    });

    return paragraphs.join('');
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return String(str);
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
