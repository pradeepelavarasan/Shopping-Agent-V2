const API_URL = "http://127.0.0.1:8000";

async function submitTask() {
    const query = document.getElementById("query-input").value;
    if (!query) return;
    
    document.getElementById("query-input").value = "";
    
    const priorities = ["Customer Sentiment", "Reliability", "Value for Money", "Feature Completeness", "Build Quality"];
    
    try {
        const res = await fetch(`${API_URL}/tasks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, priorities })
        });
        const task = await res.json();
        
        const tasks = await getTasks();
        tasks.push(task.id);
        await chrome.storage.local.set({ tasks });
        renderQueue();
    } catch (e) {
        console.error("Error submitting task", e);
    }
}

document.getElementById("search-btn").addEventListener("click", submitTask);

document.getElementById("query-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        submitTask();
    }
});

async function getTasks() {
    return new Promise(r => chrome.storage.local.get(['tasks'], res => r(res.tasks || [])));
}

async function getCachedTask(taskId) {
    return new Promise(r => chrome.storage.local.get([`task_${taskId}`], res => r(res[`task_${taskId}`])));
}

async function setCachedTask(taskId, data) {
    return new Promise(r => chrome.storage.local.set({ [`task_${taskId}`]: data }, r));
}

async function renderQueue() {
    const list = document.getElementById("queue-list");
    const tasks = await getTasks();
    
    let newInnerHtml = "";
    // Use [...tasks] to avoid modifying the original array if it matters
    for (const taskId of [...tasks].reverse()) {
        let data = await getCachedTask(taskId);
        
        // Only fetch from the API if it's not complete or errored
        if (!data || (data.status !== 'complete' && data.status !== 'error')) {
            try {
                const res = await fetch(`${API_URL}/tasks/${taskId}`);
                data = await res.json();
                
                // Cache it locally forever so we stop spamming the API!
                if (data.status === 'complete' || data.status === 'error') {
                    await setCachedTask(taskId, data);
                }
            } catch (e) {
                data = { task: { query: "Loading..." }, status: "network_error" };
            }
        }
        
        let itemHtml = `<div class="queue-item ${data.status === 'complete' ? 'clickable-card' : ''}" data-task-id="${taskId}">`;
        
        // Header row with query and status
        itemHtml += `<div class="item-header">`;
        if (data.task && data.task.query) {
            itemHtml += `<div class="query">${data.task.query}</div>`;
        }
        
        if (data.status === 'complete') {
            itemHtml += `<div class="status success">✅</div>`;
        } else if (data.status === 'error') {
            itemHtml += `<div class="status error">❌</div>`;
        } else {
            // No emoji for loading/searching/analyzing as shimmer is enough
            itemHtml += `<div class="status loading"></div>`;
        }
        itemHtml += `</div>`;

        if (data.status === 'complete') {
            const analysisProducts = data.analysis && data.analysis.products ? data.analysis.products : [];
            const topProdAnalysis = analysisProducts.find(p => p.is_top_recommendation);
            
            if (topProdAnalysis) {
                // Find matching product metadata
                const productMeta = data.products.find(p => p.id === topProdAnalysis.product_id);
                if (productMeta) {
                    const reviewsStr = productMeta.reviews_count ? ` (${productMeta.reviews_count.toLocaleString()})` : '';
                    itemHtml += `
                        <div class="recommendation-card">
                            <img src="${productMeta.image_url}" class="rec-thumb">
                            <div class="rec-info">
                                <div class="rec-label">🏆 Top Recommendation</div>
                                <div class="rec-name">${productMeta.title.substring(0, 45)}...</div>
                                <div class="rec-metrics">
                                    <span class="rec-price">${productMeta.price || 'N/A'}</span>
                                    <span class="rec-rating">⭐ ${productMeta.rating || '0'}${reviewsStr}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }
            }
        } else if (data.status === 'error' || data.status === 'network_error') {
             itemHtml += `<div class="error-msg">${data.error_message || "Backend offline"}</div>`;
        } else {
             itemHtml += `<div class="loading-bar"><div class="loading-progress"></div></div>`;
        }
        
        itemHtml += `</div>`;
        newInnerHtml += itemHtml;
    }
    
    list.innerHTML = newInnerHtml;
    
    // Attach click listeners to the entire clickable card
    const clickableCards = list.querySelectorAll('.clickable-card');
    clickableCards.forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.button === 2) return;
            const id = card.getAttribute('data-task-id');
            chrome.tabs.create({ url: `results.html?taskId=${id}` });
        });
    });

    // Handle right-click to delete
    const allItems = list.querySelectorAll('.queue-item');
    allItems.forEach(item => {
        item.addEventListener('contextmenu', async (e) => {
            e.preventDefault(); // This blocks the "Inspect" menu from showing up
            const id = item.getAttribute('data-task-id');
            const queryText = item.querySelector('.query') ? item.querySelector('.query').innerText : "this item";
            
            if (confirm(`Delete research for "${queryText}"?`)) {
                let tasks = await getTasks();
                tasks = tasks.filter(tid => tid !== id);
                await chrome.storage.local.set({ tasks });
                await chrome.storage.local.remove([`task_${id}`]);
                renderQueue(); // Refresh the list immediately
            }
        });
    });
}

// Poll every 3 seconds
setInterval(renderQueue, 3000);
// Initial render
renderQueue();

// Safe image fallback handling
document.addEventListener('error', (e) => {
    if (e.target.tagName === 'IMG' && e.target.classList.contains('rec-thumb')) {
        e.target.src = 'icon128.png';
    }
}, true);
