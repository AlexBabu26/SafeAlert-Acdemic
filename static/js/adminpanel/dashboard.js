document.addEventListener('DOMContentLoaded', function() {
    if (!requireAuth()) return;

    const userInfo = getUserInfo();
    if (!userInfo || !userInfo.is_staff) {
        window.location.href = '/reports';
        return;
    }

    let currentPage = 1;
    const filters = {
        status: '',
        category: '',
        search: '',
        created_after: '',
        created_before: '',
    };

    // Load categories for filter
    loadCategories();

    // Load incidents
    loadIncidents();

    // Filter button
    document.getElementById('btn-filter').addEventListener('click', function() {
        currentPage = 1;
        filters.status = document.getElementById('filter-status').value;
        filters.category = document.getElementById('filter-category').value;
        filters.search = document.getElementById('filter-search').value;
        filters.created_after = document.getElementById('filter-date-from').value;
        filters.created_before = document.getElementById('filter-date-to').value;
        loadIncidents();
    });

    async function loadCategories() {
        try {
            const categories = await apiGet(API_ENDPOINTS.categories);
            const select = document.getElementById('filter-category');
            categories.results.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load categories:', error);
        }
    }

    async function loadIncidents() {
        const container = document.getElementById('incidents-list');
        container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>';

        try {
            const params = { page: currentPage };
            if (filters.status) params.status = filters.status;
            if (filters.category) params.category = filters.category;
            if (filters.search) params.search = filters.search;
            if (filters.created_after) params.created_after = filters.created_after;
            if (filters.created_before) params.created_before = filters.created_before;

            const data = await apiGet(API_ENDPOINTS.admin.incidents, params);

            if (data.results.length === 0) {
                container.innerHTML = '<div class="text-center py-5"><p class="text-muted">No incidents found.</p></div>';
                document.getElementById('pagination-nav').style.display = 'none';
                return;
            }

            let html = '<table class="table table-hover"><thead><tr><th>ID</th><th>Category</th><th>User</th><th>Title</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>';
            
            data.results.forEach(incident => {
                html += `
                    <tr>
                        <td>#${incident.id}</td>
                        <td>${escapeHtml(incident.category_name)}</td>
                        <td>${escapeHtml(incident.user_username)}</td>
                        <td>${escapeHtml(incident.title || incident.description.substring(0, 30))}</td>
                        <td>${formatStatus(incident.status)}</td>
                        <td>${formatDate(incident.created_at)}</td>
                        <td><a href="/admin/reports/${incident.id}" class="btn btn-sm btn-outline-primary">View</a></td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;

            // Pagination
            renderPagination(data);
        } catch (error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
            console.error('Failed to load incidents:', error);
        }
    }

    function renderPagination(data) {
        const nav = document.getElementById('pagination-nav');
        const pagination = document.getElementById('pagination');
        
        if (!data.next && !data.previous) {
            nav.style.display = 'none';
            return;
        }

        nav.style.display = 'block';
        pagination.innerHTML = '';

        if (data.previous) {
            const li = document.createElement('li');
            li.className = 'page-item';
            li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a>`;
            pagination.appendChild(li);
        }

        if (data.next) {
            const li = document.createElement('li');
            li.className = 'page-item';
            li.innerHTML = `<a class="page-link" href="#" data-page="${currentPage + 1}">Next</a>`;
            pagination.appendChild(li);
        }

        pagination.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                currentPage = parseInt(this.dataset.page);
                loadIncidents();
            });
        });
    }
});

