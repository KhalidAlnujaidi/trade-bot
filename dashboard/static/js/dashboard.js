// Global variables for charts
let sentimentChart;
let trendChart;

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    setInterval(loadDashboardData, 60000); // Refresh every minute
});

// Load all dashboard data from the API
async function loadDashboardData() {
    try {
        // Load articles and stats
        const response = await fetch('/api/articles');
        if (!response.ok) throw new Error('Failed to fetch articles');
        const data = await response.json();
        
        // Update last updated time
        document.getElementById('last-updated').textContent = new Date().toLocaleString();
        
        // Update stats cards
        document.getElementById('total-articles').textContent = data.stats.total_articles;
        document.getElementById('positive-articles').textContent = data.stats.positive_articles;
        document.getElementById('negative-articles').textContent = data.stats.negative_articles;
        document.getElementById('avg-confidence').textContent = `${data.stats.avg_confidence}%`;
        
        // Update articles table
        updateArticlesTable(data.articles);
        
        // Update sentiment chart
        updateSentimentChart({
            positive: data.stats.positive_articles,
            negative: data.stats.negative_articles,
            neutral: data.stats.neutral_articles
        });
        
        // Load trend data
        const trendResponse = await fetch('/api/articles/trend');
        if (!trendResponse.ok) throw new Error('Failed to fetch trend data');
        const trendData = await trendResponse.json();
        
        // Update trend chart
        updateTrendChart(trendData.trend_data);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Update the articles table with the latest data
function updateArticlesTable(articles) {
    const tbody = document.getElementById('articles-table-body');
    tbody.innerHTML = ''; // Clear existing rows
    
    // Only show the 10 most recent articles in the table
    const recentArticles = articles.slice(0, 10);
    
    recentArticles.forEach(article => {
        const row = document.createElement('tr');
        
        // Format the date
        const pubDate = article.publication_date ? new Date(article.publication_date).toLocaleDateString() : 'N/A';
        
        // Determine sentiment color
        let sentimentClass = 'bg-gray-100 text-gray-800';
        if (article.llm_evaluation === 'positive') sentimentClass = 'bg-green-100 text-green-800';
        if (article.llm_evaluation === 'negative') sentimentClass = 'bg-red-100 text-red-800';
        
        // Create row HTML
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">
                    <a href="${article.url}" target="_blank" class="text-blue-600 hover:underline">
                        ${article.title || 'Untitled'}
                    </a>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${pubDate}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${sentimentClass}">
                    ${article.llm_evaluation || 'Neutral'}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${article.llm_confidence ? `${Math.round(article.llm_confidence * 100)}%` : 'N/A'}
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

// Create or update the sentiment distribution chart
function updateSentimentChart(data) {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (sentimentChart) {
        sentimentChart.destroy();
    }
    
    sentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Negative', 'Neutral'],
            datasets: [{
                data: [data.positive, data.negative, data.neutral],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)', // green
                    'rgba(239, 68, 68, 0.8)',  // red
                    'rgba(156, 163, 175, 0.8)'  // gray
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(239, 68, 68, 1)',
                    'rgba(156, 163, 175, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Create or update the trend chart
function updateTrendChart(trendData) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    // Process trend data
    const labels = trendData.map(item => item.date);
    const positiveData = trendData.map(item => item.positive || 0);
    const negativeData = trendData.map(item => item.negative || 0);
    const totalData = trendData.map(item => item.total || 0);
    
    // Destroy existing chart if it exists
    if (trendChart) {
        trendChart.destroy();
    }
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Articles',
                    data: totalData,
                    borderColor: 'rgba(59, 130, 246, 1)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Positive',
                    data: positiveData,
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false
                },
                {
                    label: 'Negative',
                    data: negativeData,
                    borderColor: 'rgba(239, 68, 68, 1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}
