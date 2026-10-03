// Operations Analytics Warehouse - Dashboard JS Application
let rawKpiData = null;
let charts = {};

document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboardData();
});

async function loadDashboardData() {
    try {
        const response = await fetch('./data/kpi_data.json');
        if (!response.ok) throw new Error('Data file not found');
        rawKpiData = await response.json();
        initializeDashboard(rawKpiData);
    } catch (err) {
        console.warn('Falling back to synthetic embedded KPI payload:', err);
        rawKpiData = generateMockKpiPayload();
        initializeDashboard(rawKpiData);
    }
}

function initializeDashboard(data) {
    populateFilterDropdowns(data);
    updateKpiCards(data.overview);
    renderMonthlyTrendChart(data.monthly_trends);
    renderDeptWorkloadChart(data.departments);
    renderCategoryChart(data.categories);
    renderGeoChart(data.geo_distribution);
    renderBacklogAgingChart(data.backlog_aging);
}

function populateFilterDropdowns(data) {
    const deptSelect = document.getElementById('dept-filter');
    const catSelect = document.getElementById('category-filter');
    const distSelect = document.getElementById('district-filter');

    if (data.departments) {
        const depts = [...new Set(data.departments.map(d => d.department_name))];
        depts.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            deptSelect.appendChild(opt);
        });
    }

    if (data.categories) {
        const cats = [...new Set(data.categories.map(c => c.request_category))];
        cats.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            catSelect.appendChild(opt);
        });
    }

    if (data.geo_distribution) {
        const dists = [...new Set(data.geo_distribution.map(g => g.district_code))];
        dists.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = `${d} (${g_neighborhood(data, d)})`;
            distSelect.appendChild(opt);
        });
    }
}

function g_neighborhood(data, dist) {
    const match = data.geo_distribution.find(g => g.district_code === dist);
    return match ? match.neighborhood : dist;
}

function updateKpiCards(overview) {
    if (!overview) return;
    document.getElementById('kpi-total').textContent = (overview.total_requests || 5000).toLocaleString();
    document.getElementById('kpi-closed-sub').textContent = `${(overview.total_closed_requests || 4250).toLocaleString()} Resolved (${overview.sla_compliance_pct || 81.5}%)`;
    document.getElementById('kpi-avg-time').innerHTML = `${overview.avg_resolution_hours || 28.4} <span class="unit">hrs</span>`;
    document.getElementById('kpi-sla-rate').textContent = `${overview.sla_compliance_pct || 81.5}%`;
    document.getElementById('kpi-sla-breach-sub').textContent = `${(overview.total_sla_breaches || 786).toLocaleString()} Breaches`;
    document.getElementById('kpi-backlog').textContent = (overview.current_backlog || 750).toLocaleString();
    document.getElementById('kpi-repeat-rate').textContent = `${overview.repeat_incident_pct || 12.3}%`;
}

function applyFilters() {
    const dept = document.getElementById('dept-filter').value;
    const cat = document.getElementById('category-filter').value;
    const dist = document.getElementById('district-filter').value;
    const prio = document.getElementById('priority-filter').value;

    let filteredDepts = rawKpiData.departments || [];
    let filteredCats = rawKpiData.categories || [];

    if (dept !== 'ALL') filteredDepts = filteredDepts.filter(d => d.department_name === dept);
    if (cat !== 'ALL') filteredCats = filteredCats.filter(c => c.request_category === cat);
    if (prio !== 'ALL') filteredCats = filteredCats.filter(c => c.priority_level === prio);

    // Re-render filtered charts
    renderDeptWorkloadChart(filteredDepts);
    renderCategoryChart(filteredCats);

    const totalCount = filteredDepts.reduce((acc, curr) => acc + (curr.total_tickets || 0), 0);
    document.getElementById('filter-summary').textContent = `Showing ${totalCount > 0 ? totalCount.toLocaleString() : '5,000'} Filtered Incidents`;
}

function renderMonthlyTrendChart(trends) {
    const ctx = document.getElementById('monthlyTrendChart').getContext('2d');
    if (charts.monthly) charts.monthly.destroy();

    const labels = (trends || []).map(t => t.year_month || t.month_name);
    const volumes = (trends || []).map(t => t.ticket_volume || 0);
    const breaches = (trends || []).map(t => t.sla_breaches || 0);

    charts.monthly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [
                {
                    label: 'Total Ticket Volume',
                    data: volumes.length ? volumes : [380, 420, 450, 410, 490, 510, 480, 520, 460, 490, 440, 470],
                    backgroundColor: 'rgba(139, 92, 246, 0.5)',
                    borderColor: '#8b5cf6',
                    borderWidth: 1.5,
                    borderRadius: 6
                },
                {
                    label: 'SLA Breaches',
                    data: breaches.length ? breaches : [65, 82, 90, 70, 95, 105, 88, 98, 75, 85, 78, 82],
                    type: 'line',
                    borderColor: '#f43f5e',
                    backgroundColor: 'rgba(244, 63, 94, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Outfit' } } }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderDeptWorkloadChart(depts) {
    const ctx = document.getElementById('deptWorkloadChart').getContext('2d');
    if (charts.dept) charts.dept.destroy();

    const labels = (depts || []).map(d => d.division_name || d.department_name);
    const tickets = (depts || []).map(d => d.total_tickets || 0);
    const resolution = (depts || []).map(d => d.avg_resolution_hours || 0);

    charts.dept = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['Roads', 'Sanitation', 'Water Main', 'Code Enforcement', 'Parks', 'Traffic'],
            datasets: [
                {
                    label: 'Total Tickets',
                    data: tickets.length ? tickets : [1200, 1100, 850, 700, 600, 550],
                    backgroundColor: 'rgba(6, 182, 212, 0.6)',
                    borderColor: '#06b6d4',
                    borderWidth: 1,
                    borderRadius: 6
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8' } }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderCategoryChart(categories) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    if (charts.cat) charts.cat.destroy();

    const catMap = {};
    (categories || []).forEach(c => {
        catMap[c.request_category] = (catMap[c.request_category] || 0) + (c.request_count || 1);
    });

    const labels = Object.keys(catMap).length ? Object.keys(catMap) : ['Infrastructure', 'Sanitation', 'Water & Utilities', 'Code Enforcement', 'Parks & Grounds', 'Traffic & Transit'];
    const values = Object.values(catMap).length ? Object.values(catMap) : [1450, 1200, 850, 600, 500, 400];

    charts.cat = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#6366f1'],
                borderWidth: 2,
                borderColor: '#121824'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', font: { family: 'Outfit' } } }
            }
        }
    });
}

function renderGeoChart(geo) {
    const ctx = document.getElementById('geoChart').getContext('2d');
    if (charts.geo) charts.geo.destroy();

    const labels = (geo || []).map(g => `${g.district_code} (${g.neighborhood})`);
    const values = (geo || []).map(g => g.total_requests || 0);

    charts.geo = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: labels.length ? labels : ['DIST-01 (Downtown)', 'DIST-02 (Northside)', 'DIST-03 (University)', 'DIST-04 (East Park)', 'DIST-05 (West End)'],
            datasets: [{
                data: values.length ? values : [1250, 1100, 950, 900, 800],
                backgroundColor: [
                    'rgba(139, 92, 246, 0.6)',
                    'rgba(6, 182, 212, 0.6)',
                    'rgba(16, 185, 129, 0.6)',
                    'rgba(245, 158, 11, 0.6)',
                    'rgba(244, 63, 94, 0.6)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8' } }
            },
            scales: {
                r: { grid: { color: 'rgba(255,255,255,0.08)' }, ticks: { display: false } }
            }
        }
    });
}

function renderBacklogAgingChart(backlog) {
    const ctx = document.getElementById('backlogAgingChart').getContext('2d');
    if (charts.backlog) charts.backlog.destroy();

    const depts = (backlog || []).map(b => b.department_name || 'Dept');
    const d0_3 = (backlog || []).map(b => b.aging_0_to_3_days || 0);
    const d4_7 = (backlog || []).map(b => b.aging_4_to_7_days || 0);
    const d8_14 = (backlog || []).map(b => b.aging_8_to_14_days || 0);
    const d14_plus = (backlog || []).map(b => b.aging_over_14_days || 0);

    charts.backlog = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: depts.length ? depts : ['Public Works', 'Water & Utilities', 'Public Safety', 'Parks & Rec', 'Transportation'],
            datasets: [
                { label: '0-3 Days', data: d0_3.length ? d0_3 : [120, 80, 50, 40, 30], backgroundColor: '#10b981' },
                { label: '4-7 Days', data: d4_7.length ? d4_7 : [60, 45, 30, 20, 15], backgroundColor: '#06b6d4' },
                { label: '8-14 Days', data: d8_14.length ? d8_14 : [30, 20, 15, 10, 8], backgroundColor: '#f59e0b' },
                { label: '> 14 Days', data: d14_plus.length ? d14_plus : [15, 10, 8, 5, 4], backgroundColor: '#f43f5e' }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { stacked: true, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: {
                legend: { labels: { color: '#94a3b8' } }
            }
        }
    });
}

function exportKpiData() {
    if (!rawKpiData) return alert('No KPI data loaded to export.');
    const blob = new Blob([JSON.stringify(rawKpiData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'operations_kpi_export.json';
    a.click();
}

function refreshDashboard() {
    loadDashboardData();
}

function generateMockKpiPayload() {
    return {
        overview: {
            total_requests: 5000,
            total_closed_requests: 4250,
            current_backlog: 750,
            avg_resolution_hours: 28.4,
            sla_compliance_pct: 81.5,
            total_sla_breaches: 786,
            repeat_incident_pct: 12.3,
            avg_satisfaction_rating: 4.2
        },
        departments: [
            { department_name: 'Public Works', division_name: 'Roads & Infrastructure', total_tickets: 1450, avg_resolution_hours: 32.1, sla_compliance_pct: 82.5 },
            { department_name: 'Public Works', division_name: 'Sanitation & Waste', total_tickets: 1200, avg_resolution_hours: 21.4, sla_compliance_pct: 88.0 },
            { department_name: 'Water & Utilities', division_name: 'Water Main Maintenance', total_tickets: 850, avg_resolution_hours: 18.2, sla_compliance_pct: 91.2 },
            { department_name: 'Public Safety', division_name: 'Code Enforcement', total_tickets: 600, avg_resolution_hours: 45.0, sla_compliance_pct: 74.1 },
            { department_name: 'Parks & Recreation', division_name: 'Tree Maintenance & Grounds', total_tickets: 500, avg_resolution_hours: 24.8, sla_compliance_pct: 85.0 },
            { department_name: 'Transportation', division_name: 'Traffic Signals & Transit', total_tickets: 400, avg_resolution_hours: 14.5, sla_compliance_pct: 94.0 }
        ],
        monthly_trends: [
            { year_month: '2025-01', month_name: 'January', ticket_volume: 380, sla_breaches: 65 },
            { year_month: '2025-02', month_name: 'February', ticket_volume: 420, sla_breaches: 82 },
            { year_month: '2025-03', month_name: 'March', ticket_volume: 450, sla_breaches: 90 },
            { year_month: '2025-04', month_name: 'April', ticket_volume: 410, sla_breaches: 70 },
            { year_month: '2025-05', month_name: 'May', ticket_volume: 490, sla_breaches: 95 },
            { year_month: '2025-06', month_name: 'June', ticket_volume: 510, sla_breaches: 105 },
            { year_month: '2025-07', month_name: 'July', ticket_volume: 480, sla_breaches: 88 },
            { year_month: '2025-08', month_name: 'August', ticket_volume: 520, sla_breaches: 98 },
            { year_month: '2025-09', month_name: 'September', ticket_volume: 460, sla_breaches: 75 },
            { year_month: '2025-10', month_name: 'October', ticket_volume: 490, sla_breaches: 85 },
            { year_month: '2025-11', month_name: 'November', ticket_volume: 440, sla_breaches: 78 },
            { year_month: '2025-12', month_name: 'December', ticket_volume: 470, sla_breaches: 82 }
        ],
        categories: [
            { request_category: 'Infrastructure', request_count: 1450, priority_level: 'High' },
            { request_category: 'Sanitation', request_count: 1200, priority_level: 'High' },
            { request_category: 'Water & Utilities', request_count: 850, priority_level: 'Critical' },
            { request_category: 'Code Enforcement', request_count: 600, priority_level: 'Medium' },
            { request_category: 'Parks & Grounds', request_count: 500, priority_level: 'Medium' },
            { request_category: 'Traffic & Transit', request_count: 400, priority_level: 'Critical' }
        ],
        geo_distribution: [
            { district_code: 'DIST-01', neighborhood: 'Downtown Metro', total_requests: 1250 },
            { district_code: 'DIST-02', neighborhood: 'Northside Heights', total_requests: 1100 },
            { district_code: 'DIST-03', neighborhood: 'University Hills', total_requests: 950 },
            { district_code: 'DIST-04', neighborhood: 'East Park Industrial', total_requests: 900 },
            { district_code: 'DIST-05', neighborhood: 'West End Suburbs', total_requests: 800 }
        ],
        backlog_aging: [
            { department_name: 'Public Works', aging_0_to_3_days: 120, aging_4_to_7_days: 60, aging_8_to_14_days: 30, aging_over_14_days: 15 },
            { department_name: 'Water & Utilities', aging_0_to_3_days: 80, aging_4_to_7_days: 45, aging_8_to_14_days: 20, aging_over_14_days: 10 },
            { department_name: 'Public Safety', aging_0_to_3_days: 50, aging_4_to_7_days: 30, aging_8_to_14_days: 15, aging_over_14_days: 8 },
            { department_name: 'Parks & Rec', aging_0_to_3_days: 40, aging_4_to_7_days: 20, aging_8_to_14_days: 10, aging_over_14_days: 5 },
            { department_name: 'Transportation', aging_0_to_3_days: 30, aging_4_to_7_days: 15, aging_8_to_14_days: 8, aging_over_14_days: 4 }
        ]
    };
}
