// Global state
let currentPRs = [];
let currentPage = 1;
let totalResults = 0;

// Track retested jobs: Map<"owner/repo/pr/jobName", {timestamp, pollInterval}>
const retestedJobs = new Map();
const POLL_INTERVAL = 5000; // 5 seconds
const MAX_POLL_TIME = 5 * 60 * 1000; // 5 minutes

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
    try {
        const response = await fetch('/api/auth/status');
        return await response.json();
    } catch (error) {
        console.error('Auth check failed:', error);
        return { authenticated: false, error: 'Failed to check authentication status' };
    }
}

function showAuthBanner(message) {
    const banner = document.getElementById('auth-banner');
    banner.textContent = '⚠️ ' + message;
    banner.classList.remove('hidden');
}

async function executeSearch(query) {
    showLoading('Searching PRs...');

    try {
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
    } catch (error) {
        console.error('Search failed:', error);
        showToast('Search failed: ' + error.message, 'error');
        hideLoading();
    }
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

    // Create PR header with safe text content
    const prHeader = document.createElement('div');
    prHeader.className = 'pr-header';

    const prTitle = document.createElement('div');
    prTitle.className = 'pr-title';
    prTitle.textContent = `PR #${pr.number} - ${pr.title}`;

    const prMeta = document.createElement('div');
    prMeta.className = 'pr-meta';
    prMeta.textContent = `${pr.owner}/${pr.repo} • ${pr.author} • ${age}`;

    prHeader.appendChild(prTitle);
    prHeader.appendChild(prMeta);

    // Create E2E section
    const e2eSection = document.createElement('div');
    e2eSection.className = 'job-section';
    e2eSection.id = `e2e-${pr.owner}-${pr.repo}-${pr.number}`;

    const e2eHeader = document.createElement('div');
    e2eHeader.className = 'job-section-header';
    e2eHeader.textContent = '▶ E2E Jobs (loading...)';

    const e2eList = document.createElement('div');
    e2eList.className = 'job-list';

    e2eSection.appendChild(e2eHeader);
    e2eSection.appendChild(e2eList);

    // Create Payload section
    const payloadSection = document.createElement('div');
    payloadSection.className = 'job-section';
    payloadSection.id = `payload-${pr.owner}-${pr.repo}-${pr.number}`;

    const payloadHeader = document.createElement('div');
    payloadHeader.className = 'job-section-header';
    payloadHeader.textContent = '▶ Payload Jobs (loading...)';

    const payloadList = document.createElement('div');
    payloadList.className = 'job-list';

    payloadSection.appendChild(payloadHeader);
    payloadSection.appendChild(payloadList);

    // Assemble card
    card.appendChild(prHeader);
    card.appendChild(e2eSection);
    card.appendChild(payloadSection);

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

    let e2eFailed = data.e2e.failed || [];
    const e2eRunning = data.e2e.running || [];

    // Filter out retested jobs that are now running
    e2eFailed = e2eFailed.filter(job => {
        const jobKey = `${owner}/${repo}/${number}/${job.name}`;
        const retestInfo = retestedJobs.get(jobKey);
        if (retestInfo) {
            // Check if job is now running
            const isRunning = e2eRunning.some(r => r.name === job.name);
            if (isRunning) {
                // Job started running, stop polling for this job
                clearInterval(retestInfo.pollInterval);
                retestedJobs.delete(jobKey);
                return false; // Remove from failed list
            }
        }
        return true; // Keep in failed list
    });

    e2eHeader.textContent = `▶ E2E Jobs (${e2eFailed.length} failed | ${e2eRunning.length} running)`;

    // Remove old listener and add new one
    const newE2eHeader = e2eHeader.cloneNode(true);
    e2eHeader.parentNode.replaceChild(newE2eHeader, e2eHeader);
    newE2eHeader.addEventListener('click', () => e2eList.classList.toggle('expanded'));

    // Clear existing content
    e2eList.innerHTML = '';

    if (e2eFailed.length > 0) {
        e2eFailed.forEach(job => {
            const jobItem = document.createElement('div');
            jobItem.className = 'job-item';

            const jobName = document.createElement('div');
            jobName.className = 'job-name';
            jobName.textContent = `❌ ${job.name} (${job.consecutive} consecutive)`;

            const jobActions = document.createElement('div');
            jobActions.className = 'job-actions';

            const retestBtn = document.createElement('button');
            retestBtn.className = 'btn';
            retestBtn.dataset.owner = owner;
            retestBtn.dataset.repo = repo;
            retestBtn.dataset.number = number;
            retestBtn.dataset.jobName = job.name;
            retestBtn.dataset.jobType = 'e2e';

            // Check if job is being polled
            const jobKey = `${owner}/${repo}/${number}/${job.name}`;
            if (retestedJobs.has(jobKey)) {
                retestBtn.textContent = '⏳ Retesting...';
                retestBtn.disabled = true;
            } else {
                retestBtn.textContent = 'Retest';
                retestBtn.addEventListener('click', (e) => {
                    // Immediately update button state
                    e.target.textContent = '⏳ Retesting...';
                    e.target.disabled = true;
                    retestJob(owner, repo, number, [job.name], 'e2e');
                });
            }

            const analyzeBtn = document.createElement('button');
            analyzeBtn.className = 'btn btn-secondary';
            analyzeBtn.textContent = 'Analyze';
            analyzeBtn.disabled = true;

            jobActions.appendChild(retestBtn);
            jobActions.appendChild(analyzeBtn);

            jobItem.appendChild(jobName);
            jobItem.appendChild(jobActions);

            e2eList.appendChild(jobItem);
        });

        const retestAllBtn = document.createElement('button');
        retestAllBtn.className = 'btn';
        retestAllBtn.textContent = 'Retest All E2E';
        retestAllBtn.addEventListener('click', () => retestAllE2E(owner, repo, number));
        e2eList.appendChild(retestAllBtn);
    } else {
        const noFailures = document.createElement('div');
        noFailures.style.padding = '0.5rem';
        noFailures.textContent = '✅ No failed jobs';
        e2eList.appendChild(noFailures);
    }

    // Update Payload section
    const payloadSection = cardElement.querySelector(`#payload-${owner}-${repo}-${number}`);
    const payloadHeader = payloadSection.querySelector('.job-section-header');
    const payloadList = payloadSection.querySelector('.job-list');

    let payloadFailed = data.payload.failed || [];
    const payloadRunning = data.payload.running || [];

    // Filter out retested jobs that are now running
    payloadFailed = payloadFailed.filter(job => {
        const jobKey = `${owner}/${repo}/${number}/${job.name}`;
        const retestInfo = retestedJobs.get(jobKey);
        if (retestInfo) {
            // Check if job is now running
            const isRunning = payloadRunning.some(r => r.name === job.name);
            if (isRunning) {
                // Job started running, stop polling for this job
                clearInterval(retestInfo.pollInterval);
                retestedJobs.delete(jobKey);
                return false; // Remove from failed list
            }
        }
        return true; // Keep in failed list
    });

    payloadHeader.textContent = `▶ Payload Jobs (${payloadFailed.length} failed | ${payloadRunning.length} running)`;

    // Remove old listener and add new one
    const newPayloadHeader = payloadHeader.cloneNode(true);
    payloadHeader.parentNode.replaceChild(newPayloadHeader, payloadHeader);
    newPayloadHeader.addEventListener('click', () => payloadList.classList.toggle('expanded'));

    // Clear existing content
    payloadList.innerHTML = '';

    if (payloadFailed.length > 0) {
        payloadFailed.forEach(job => {
            const jobItem = document.createElement('div');
            jobItem.className = 'job-item';

            const jobName = document.createElement('div');
            jobName.className = 'job-name';
            jobName.textContent = `❌ ${job.name} (${job.consecutive} consecutive)`;

            const jobActions = document.createElement('div');
            jobActions.className = 'job-actions';

            const retestBtn = document.createElement('button');
            retestBtn.className = 'btn';
            retestBtn.dataset.owner = owner;
            retestBtn.dataset.repo = repo;
            retestBtn.dataset.number = number;
            retestBtn.dataset.jobName = job.name;
            retestBtn.dataset.jobType = 'payload';

            // Check if job is being polled
            const jobKey = `${owner}/${repo}/${number}/${job.name}`;
            if (retestedJobs.has(jobKey)) {
                retestBtn.textContent = '⏳ Retesting...';
                retestBtn.disabled = true;
            } else {
                retestBtn.textContent = 'Retest';
                retestBtn.addEventListener('click', (e) => {
                    // Immediately update button state
                    e.target.textContent = '⏳ Retesting...';
                    e.target.disabled = true;
                    retestJob(owner, repo, number, [job.name], 'payload');
                });
            }

            const analyzeBtn = document.createElement('button');
            analyzeBtn.className = 'btn btn-secondary';
            analyzeBtn.textContent = 'Analyze';
            analyzeBtn.disabled = true;

            jobActions.appendChild(retestBtn);
            jobActions.appendChild(analyzeBtn);

            jobItem.appendChild(jobName);
            jobItem.appendChild(jobActions);

            payloadList.appendChild(jobItem);
        });

        const retestAllBtn = document.createElement('button');
        retestAllBtn.className = 'btn';
        retestAllBtn.textContent = 'Retest All Payload';
        retestAllBtn.addEventListener('click', () => retestAllPayload(owner, repo, number));
        payloadList.appendChild(retestAllBtn);
    } else {
        const noFailures = document.createElement('div');
        noFailures.style.padding = '0.5rem';
        noFailures.textContent = '✅ No failed jobs';
        payloadList.appendChild(noFailures);
    }
}

async function retestJob(owner, repo, pr, jobs, type) {
    try {
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

            // Track retested jobs and start polling
            jobs.forEach(jobName => {
                const jobKey = `${owner}/${repo}/${pr}/${jobName}`;
                const startTime = Date.now();

                // Start polling for this PR
                const pollInterval = setInterval(() => {
                    const elapsed = Date.now() - startTime;

                    // Stop polling after MAX_POLL_TIME
                    if (elapsed > MAX_POLL_TIME) {
                        clearInterval(pollInterval);
                        retestedJobs.delete(jobKey);
                        return;
                    }

                    // Reload job data for this PR
                    const card = document.getElementById(`pr-${owner}-${repo}-${pr}`);
                    if (card) {
                        loadPRJobs(owner, repo, pr, card);
                    }
                }, POLL_INTERVAL);

                retestedJobs.set(jobKey, { startTime, pollInterval });
            });
        } else {
            showToast(`❌ Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Retest failed:', error);
        showToast('Retest failed: ' + error.message, 'error');
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
