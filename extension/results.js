document.addEventListener("DOMContentLoaded", async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const taskId = urlParams.get('taskId');

    if (!taskId) {
        showError("Invalid Task ID provided.");
        return;
    }

    const tuneBtn = document.getElementById('sa-tune-btn');
    const dropdown = document.getElementById('sa-tune-dropdown');
    
    tuneBtn.addEventListener('click', () => {
        dropdown.classList.toggle('hidden');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!tuneBtn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });

    try {
        const cached = await new Promise(r => chrome.storage.local.get([`task_${taskId}`], res => r(res[`task_${taskId}`])));
        
        if (!cached || !cached.task || cached.status !== 'complete') {
            showError("Task data not found or not yet complete.");
            return;
        }

        renderPriorities(cached.task.priorities || []);
        renderMatrix(cached);
    } catch (e) {
        showError("Error loading task data: " + e.message);
    }
});

function renderPriorities(priorities) {
    const list = document.getElementById('sa-priorities-vertical');
    list.innerHTML = '';
    priorities.forEach(pri => {
        const item = document.createElement('div');
        item.className = 'dropdown-pri-item';
        item.style.cursor = 'default';
        
        const textSpan = document.createElement('span');
        textSpan.className = 'pri-text';
        textSpan.innerText = pri;
        textSpan.style.flex = "1";
        
        item.appendChild(textSpan);
        list.appendChild(item);
    });
}

function renderMatrix(data) {
    const container = document.getElementById('matrix-container');
    const loading = document.getElementById('loading-block');
    
    if (loading) loading.style.display = 'none';

    const products = data.products || [];
    const analysis = data.analysis || { overall_agent_summary: "Evaluation complete.", products: [] };
    const rootSummary = analysis.overall_agent_summary;

    const topRecId = analysis.products.find(x => x.is_top_recommendation)?.product_id;
    
    // Sort so top recommendation is first
    products.sort((a, b) => {
        if (a.id === topRecId) return -1;
        if (b.id === topRecId) return 1;
        return 0;
    });

    let html = `
    <div class="main-wrapper">
        <div class="global-agent-summary">
            <div class="agent-avatar">✨</div>
            <div class="agent-text">"${rootSummary}"</div>
        </div>
        <div class="comparison-grid">`;

    products.forEach(prod => {
        const aiInsight = analysis.products.find(x => x.product_id === prod.id) || { evaluations: {} };
        const isTop = prod.id === topRecId;

        let colClass = isTop ? "grid-col top-rec" : "grid-col";
        let topBadge = isTop ? '<div class="top-badge-matrix">⭐ Top Recommendation</div>' : "";
        
        let evalRows = '';
        const priorities = data.task.priorities || [];
        priorities.forEach(crit => {
             const evalPayload = aiInsight.evaluations[crit];
             let analysisText = "No data available from Agent.";
             let scoreClass = "sent-neutral";
             
             if (evalPayload) {
                 analysisText = evalPayload.analysis || analysisText;
                 const score = (evalPayload.score || '').toLowerCase();
                 if (score === 'positive') scoreClass = 'sent-positive';
                 else if (score === 'negative') scoreClass = 'sent-negative';
             }

             evalRows += `
             <div class="eval-row ${scoreClass}">
                <span class="eval-label">${crit}</span>
                <span class="eval-text">${analysisText}</span>
             </div>`;
        });

        const reviewsStr = prod.reviews_count ? ` (${prod.reviews_count.toLocaleString()} reviews)` : '';
        const ratingStr = prod.rating ? `⭐ ${prod.rating}${reviewsStr}` : 'No Rating';

        html += `
        <div class="${colClass}">
            ${topBadge}
            <div class="product-click-zone" data-url="${prod.url}" title="Go to Product">
                <div class="matrix-img-wrapper">
                     <div class="matrix-img"><img src="${prod.image_url || 'https://via.placeholder.com/180?text=No+Image'}" /></div>
                </div>
                <div class="grid-header">
                     <div class="matrix-title" title="${prod.title.replace(/"/g, '&quot;')}">${prod.title}</div>
                     <div class="matrix-metrics">
                           <span class="price">${prod.price || 'N/A'}</span>
                           <span class="rating">${ratingStr}</span>
                     </div>
                </div>
            </div>
            <div class="grid-body">
                ${evalRows}
            </div>
        </div>`;
    });
    
    html += '</div></div>';
    container.innerHTML = html;

    // Attach delegated click listener for product links
    container.addEventListener('click', (e) => {
        const zone = e.target.closest('.product-click-zone');
        if (zone) {
            const url = zone.getAttribute('data-url');
            if (url) {
                chrome.tabs.create({ url });
            }
        }
    });
}

function showError(msg) {
    const container = document.getElementById('matrix-container');
    const loading = document.getElementById('loading-block');
    if (loading) loading.style.display = 'none';

    container.innerHTML = `
    <div class="agent-error-container">
        <div class="error-icon">⚠️</div>
        <div class="error-title">Error Loading Results</div>
        <div class="error-user-msg">${msg}</div>
    </div>`;
}
