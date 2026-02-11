// Global state
let currentPRs = [];
let currentPage = 1;
let totalResults = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await init();
});

async function init() {
    // Check auth status
    const authStatus = await checkAuth();
    if (!authStatus.authenticated) {
        showAuthBanner(authStatus.error);
    }

    // Load default query
    const defaultQuery = await fetch('/api/default-query').then(r => r.json());
    document.getElementById('search-input').value = defaultQuery.query;

    // Auto-execute search
    await executeSearch(defaultQuery.query);

    // Set up event listeners
    document.getElementById('search-btn').addEventListener('click', () => {
        const query = document.getElementById('search-input').value;
        executeSearch(query);
    });

    document.getElementById('search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const query = document.getElementById('search-input').value;
            executeSearch(query);
        }
    });

    document.getElementById('refresh-btn').addEventListener('click', () => {
        const query = document.getElementById('search-input').value;
        currentPage = 1;
        document.getElementById('pr-cards-container').innerHTML = '';
        executeSearch(query);
    });
}

async function checkAuth() {
    const response = await fetch('/api/auth/status');
    return await response.json();
}

function showAuthBanner(message) {
    const banner = document.getElementById('auth-banner');
    banner.textContent = '⚠️ ' + message;
    banner.classList.remove('hidden');
}

async function executeSearch(query) {
    showLoading('Searching PRs...');

    const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, page: currentPage, per_page: 10 })
    });

    const data = await response.json();

    if (data.error) {
        showToast(data.error, 'error');
        hideLoading();
        return;
    }

    currentPRs = data.prs;
    totalResults = data.total;

    hideLoading();
    renderPRCards(data.prs);
}

function renderPRCards(prs) {
    const container = document.getElementById('pr-cards-container');

    if (prs.length === 0) {
        container.innerHTML = '<div class="loading">No PRs found</div>';
        return;
    }

    prs.forEach(pr => {
        const card = createPRCard(pr);
        container.appendChild(card);

        // Fetch job data in background
        loadPRJobs(pr.owner, pr.repo, pr.number, card);
    });
}

function createPRCard(pr) {
    const card = document.createElement('div');
    card.className = 'pr-card';
    card.id = `pr-${pr.owner}-${pr.repo}-${pr.number}`;

    const age = getAge(pr.created_at);

    card.innerHTML = `
        <div class="pr-header">
            <div class="pr-title">
                PR #${pr.number} - ${pr.title}
            </div>
            <div class="pr-meta">
                ${pr.owner}/${pr.repo} • ${pr.author} • ${age}
            </div>
        </div>
        <div class="job-section" id="e2e-${pr.owner}-${pr.repo}-${pr.number}">
            <div class="job-section-header">▶ E2E Jobs (loading...)</div>
            <div class="job-list"></div>
        </div>
        <div class="job-section" id="payload-${pr.owner}-${pr.repo}-${pr.number}">
            <div class="job-section-header">▶ Payload Jobs (loading...)</div>
            <div class="job-list"></div>
        </div>
    `;

    return card;
}

async function loadPRJobs(owner, repo, number, cardElement) {
    try {
        const response = await fetch(`/api/pr/${owner}/${repo}/${number}`);
        const data = await response.json();

        updateCardWithJobs(cardElement, data, owner, repo, number);
    } catch (error) {
        showCardError(cardElement, error.message);
    }
}

function updateCardWithJobs(cardElement, data, owner, repo, number) {
    // Update E2E section
    const e2eSection = cardElement.querySelector(`#e2e-${owner}-${repo}-${number}`);
    const e2eHeader = e2eSection.querySelector('.job-section-header');
    const e2eList = e2eSection.querySelector('.job-list');

    const e2eFailed = data.e2e.failed || [];
    const e2eRunning = data.e2e.running || [];

    e2eHeader.textContent = `▶ E2E Jobs (${e2eFailed.length} failed | ${e2eRunning.length} running)`;
    e2eHeader.onclick = () => e2eList.classList.toggle('expanded');

    if (e2eFailed.length > 0) {
        e2eList.innerHTML = e2eFailed.map(job => `
            <div class="job-item">
                <div class="job-name">❌ ${job.name} (${job.consecutive} consecutive)</div>
                <div class="job-actions">
                    <button class="btn" onclick="retestJob('${owner}', '${repo}', ${number}, ['${job.name}'], 'e2e')">Retest</button>
                    <button class="btn btn-secondary" disabled>Analyze</button>
                </div>
            </div>
        `).join('');

        e2eList.innerHTML += `<button class="btn" onclick="retestAllE2E('${owner}', '${repo}', ${number})">Retest All E2E</button>`;
    } else {
        e2eList.innerHTML = '<div style="padding: 0.5rem;">✅ No failed jobs</div>';
    }

    // Update Payload section
    const payloadSection = cardElement.querySelector(`#payload-${owner}-${repo}-${number}`);
    const payloadHeader = payloadSection.querySelector('.job-section-header');
    const payloadList = payloadSection.querySelector('.job-list');

    const payloadFailed = data.payload.failed || [];
    const payloadRunning = data.payload.running || [];

    payloadHeader.textContent = `▶ Payload Jobs (${payloadFailed.length} failed | ${payloadRunning.length} running)`;
    payloadHeader.onclick = () => payloadList.classList.toggle('expanded');

    if (payloadFailed.length > 0) {
        payloadList.innerHTML = payloadFailed.map(job => `
            <div class="job-item">
                <div class="job-name">❌ ${job.name} (${job.consecutive} consecutive)</div>
                <div class="job-actions">
                    <button class="btn" onclick="retestJob('${owner}', '${repo}', ${number}, ['${job.name}'], 'payload')">Retest</button>
                    <button class="btn btn-secondary" disabled>Analyze</button>
                </div>
            </div>
        `).join('');

        payloadList.innerHTML += `<button class="btn" onclick="retestAllPayload('${owner}', '${repo}', ${number})">Retest All Payload</button>`;
    } else {
        payloadList.innerHTML = '<div style="padding: 0.5rem;">✅ No failed jobs</div>';
    }
}

async function retestJob(owner, repo, pr, jobs, type) {
    const response = await fetch('/api/retest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner, repo, pr, jobs, type })
    });

    const result = await response.json();

    if (result.error === 'auth_failed') {
        showAuthBanner('GitHub CLI not authenticated. Run: gh auth login');
        disableAllRetestButtons();
    } else if (result.success) {
        showToast(`✅ Retest triggered for ${jobs.length} job(s)`, 'success');
    } else {
        showToast(`❌ Error: ${result.error}`, 'error');
    }
}

function retestAllE2E(owner, repo, pr) {
    const card = document.getElementById(`pr-${owner}-${repo}-${pr}`);
    const e2eSection = card.querySelector(`#e2e-${owner}-${repo}-${pr}`);
    const jobItems = e2eSection.querySelectorAll('.job-item');

    const jobs = Array.from(jobItems).map(item => {
        const nameElement = item.querySelector('.job-name');
        const match = nameElement.textContent.match(/❌ (.+?) \(/);
        return match ? match[1] : null;
    }).filter(Boolean);

    retestJob(owner, repo, pr, jobs, 'e2e');
}

function retestAllPayload(owner, repo, pr) {
    const card = document.getElementById(`pr-${owner}-${repo}-${pr}`);
    const payloadSection = card.querySelector(`#payload-${owner}-${repo}-${pr}`);
    const jobItems = payloadSection.querySelectorAll('.job-item');

    const jobs = Array.from(jobItems).map(item => {
        const nameElement = item.querySelector('.job-name');
        const match = nameElement.textContent.match(/❌ (.+?) \(/);
        return match ? match[1] : null;
    }).filter(Boolean);

    retestJob(owner, repo, pr, jobs, 'payload');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showLoading(message) {
    const container = document.getElementById('pr-cards-container');
    container.innerHTML = `<div class="loading">${message}</div>`;
}

function hideLoading() {
    const loading = document.querySelector('.loading');
    if (loading && loading.textContent.includes('Searching')) {
        loading.remove();
    }
}

function showCardError(cardElement, message) {
    cardElement.innerHTML += `<div style="color: var(--primary); padding: 1rem;">⚠️ Error: ${message}</div>`;
}

function disableAllRetestButtons() {
    document.querySelectorAll('button').forEach(btn => {
        if (btn.textContent.includes('Retest')) {
            btn.disabled = true;
        }
    });
}

function getAge(createdAt) {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now - created;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'today';
    if (diffDays === 1) return '1 day old';
    return `${diffDays} days old`;
}
