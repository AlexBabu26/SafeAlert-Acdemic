document.addEventListener('DOMContentLoaded', function() {
    if (!requireAuth()) return;

    const userInfo = getUserInfo();
    if (!userInfo || !userInfo.is_staff) {
        window.location.href = '/reports';
        return;
    }

    loadSummary();
    loadTimeseries();

    document.getElementById('timeseries-days').addEventListener('change', function() {
        loadTimeseries();
    });

    async function loadSummary() {
        try {
            const data = await apiGet(API_ENDPOINTS.admin.analytics.summary);

            // Update summary cards
            document.getElementById('total-incidents').textContent = data.total_incidents;
            document.getElementById('pending-count').textContent = data.summary.pending;
            document.getElementById('verified-count').textContent = data.summary.verified;
            document.getElementById('resolved-count').textContent = data.summary.resolved;

            // Status chart
            const statusCtx = document.getElementById('status-chart').getContext('2d');
            new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: data.status_counts.map(s => s.status),
                    datasets: [{
                        data: data.status_counts.map(s => s.count),
                        backgroundColor: ['#ffc107', '#0dcaf0', '#198754'],
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        }
                    }
                }
            });

            // Category chart
            const categoryCtx = document.getElementById('category-chart').getContext('2d');
            new Chart(categoryCtx, {
                type: 'bar',
                data: {
                    labels: data.category_counts.map(c => c.name),
                    datasets: [{
                        label: 'Incidents',
                        data: data.category_counts.map(c => c.count),
                        backgroundColor: '#0d6efd',
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false,
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        } catch (error) {
            showToast(error.message || 'Failed to load analytics.', 'error');
            console.error('Failed to load summary:', error);
        }
    }

    async function loadTimeseries() {
        const days = parseInt(document.getElementById('timeseries-days').value);
        
        try {
            const data = await apiGet(API_ENDPOINTS.admin.analytics.timeseries, { days });

            const timeseriesCtx = document.getElementById('timeseries-chart').getContext('2d');
            new Chart(timeseriesCtx, {
                type: 'line',
                data: {
                    labels: data.data.map(d => d.date),
                    datasets: [{
                        label: 'Incidents',
                        data: data.data.map(d => d.count),
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        tension: 0.4,
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display: false,
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        } catch (error) {
            showToast(error.message || 'Failed to load time series data.', 'error');
            console.error('Failed to load timeseries:', error);
        }
    }
});

