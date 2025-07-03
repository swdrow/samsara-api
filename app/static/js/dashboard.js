// Dashboard JavaScript
class RowCastDashboard {
    constructor() {
        this.baseURL = window.location.origin; // Use current host for local development
        this.currentData = null;
        this.forecastData = null;
        this.charts = {};
        this.currentPage = 0;
        this.itemsPerPage = 6;
        this.currentTimeRange = '24h';
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.initializeTooltips();
        this.showLoading();
        await this.loadInitialData();
        this.hideLoading();
        this.startDataRefresh();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                this.showSection(section);
            });
        });

        // Time range selector
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setTimeRange(btn.dataset.range);
            });
        });

        // Refresh button
        document.querySelector('.refresh-btn').addEventListener('click', () => {
            this.refreshData();
        });
    }

    showSection(sectionId) {
        // Update navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-section="${sectionId}"]`).parentElement.classList.add('active');

        // Show section
        document.querySelectorAll('.content-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionId).classList.add('active');

        // Load section-specific data
        if (sectionId === 'api-docs') {
            this.loadAPIDocumentation();
        }
    }

    async loadInitialData() {
        try {
            // Load current data first (includes forecast)
            await this.loadCurrentData();
            
            // Extract forecast data from current data
            if (this.currentData && this.currentData.forecast) {
                this.forecastData = this.currentData.forecast.rowcastScores || [];
                console.log('Extracted forecast data:', this.forecastData);
            }
            
            // Load extended data separately
            await this.loadExtendedData();
            
            this.updateDashboard();
            this.updateForecastWidget();
            this.updateDetailedForecast();
            this.updateCurrentConditions();
            this.initializeCharts();
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load data. Please try again.');
        }
    }

    async loadCurrentData() {
        try {
            console.log('Loading current data from:', `${this.baseURL}/api/complete`);
            const response = await fetch(`${this.baseURL}/api/complete`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            this.currentData = await response.json();
            console.log('Current data loaded:', this.currentData);
        } catch (error) {
            console.error('Error loading current data:', error);
            throw error;
        }
    }

    async loadForecastData() {
        // Forecast data is already included in the complete API call
        // Set it from the current data if available
        if (this.currentData && this.currentData.forecast && this.currentData.forecast.rowcastScores) {
            this.forecastData = this.currentData.forecast.rowcastScores;
            console.log('Using forecast data from complete API:', this.forecastData);
        } else {
            // Fallback to separate API call
            try {
                const response = await fetch(`${this.baseURL}/api/rowcast/forecast`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                this.forecastData = await response.json();
                console.log('Loaded forecast data from separate API:', this.forecastData);
            } catch (error) {
                console.error('Error loading forecast data:', error);
                throw error;
            }
        }
    }

    async loadExtendedData() {
        try {
            const response = await fetch(`${this.baseURL}/api/rowcast/forecast/extended`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            this.extendedData = await response.json();
        } catch (error) {
            console.error('Error loading extended data:', error);
            // Extended data is optional, don't throw
        }
    }

    updateDashboard() {
        if (!this.currentData) {
            console.log('No current data available');
            return;
        }

        console.log('Updating dashboard with data:', this.currentData);
        const current = this.currentData.current;
        
        // Update current score
        const score = current.rowcastScore || 0;
        console.log('Updating score:', score);
        
        const scoreElement = document.getElementById('current-score');
        if (scoreElement) {
            scoreElement.textContent = score.toFixed(1);
            console.log('Score element updated');
        } else {
            console.error('Score element not found');
        }
        
        // Update score bar
        const scoreFill = document.getElementById('score-fill');
        if (scoreFill) {
            scoreFill.style.width = `${(score / 10) * 100}%`;
            console.log('Score bar updated');
        } else {
            console.error('Score fill element not found');
        }
        
        // Update score color
        if (scoreElement) {
            scoreElement.className = this.getScoreClass(score);
        }

        // Update current stats
        if (current.water) {
            document.getElementById('current-flow').textContent = 
                current.water.discharge ? `${current.water.discharge.toLocaleString()}` : '--';
            document.getElementById('current-water-temp').textContent = 
                current.water.waterTemp ? `${current.water.waterTemp.toFixed(1)}` : '--';
        }

        if (current.weather) {
            const windDisplay = current.weather.windSpeed ? 
                `${current.weather.windSpeed.toFixed(1)} ${current.weather.windDir || ''}` : '--';
            document.getElementById('current-wind').textContent = windDisplay;
            document.getElementById('current-temp').textContent = 
                current.weather.apparentTemp ? `${current.weather.apparentTemp.toFixed(1)}` : '--';
        }

        // Update last updated time (convert to local timezone)
        const lastUpdated = new Date(this.currentData.lastUpdated);
        document.getElementById('last-updated').textContent = 
            lastUpdated.toLocaleTimeString('en-US', { 
                timeZone: 'America/New_York', // EST/EDT timezone
                hour12: true, 
                hour: 'numeric', 
                minute: '2-digit' 
            });
    }

    updateForecastWidget(filteredData = null) {
        const data = filteredData || this.getCurrentForecastData();
        console.log('Forecast data for widget:', data);
        if (!data || !data.length) {
            console.log('No forecast data available');
            return;
        }

        const container = document.getElementById('forecast-grid');
        if (!container) {
            console.error('Forecast grid container not found');
            return;
        }
        
        // When using filtered data (day selection), show all hours, otherwise use pagination
        if (filteredData) {
            container.innerHTML = '';
            data.forEach(item => {
                const card = this.createForecastCard(item);
                container.appendChild(card);
            });
            // Hide pagination when showing filtered data
            document.getElementById('prev-page').disabled = true;
            document.getElementById('next-page').disabled = true;
            document.getElementById('page-indicator').textContent = `Day View`;
        } else {
            // Normal pagination behavior
            const startIndex = this.currentPage * this.itemsPerPage;
            const endIndex = startIndex + this.itemsPerPage;
            const pageData = data.slice(startIndex, endIndex);

            container.innerHTML = '';
            pageData.forEach(item => {
                const card = this.createForecastCard(item);
                container.appendChild(card);
            });

            this.updatePagination(data.length);
        }
    }

    createForecastCard(data) {
        const card = document.createElement('div');
        card.className = 'forecast-card';

        const time = new Date(data.timestamp);
        const timeStr = time.toLocaleString('en-US', {
            timeZone: 'America/New_York', // EST/EDT timezone
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            hour12: true
        });

        const score = data.score || 0;
        const scoreClass = this.getScoreClass(score);

        card.innerHTML = `
            <div class="forecast-time">${timeStr}</div>
            <div class="forecast-score ${scoreClass}">${score.toFixed(1)}</div>
            <div class="forecast-details">
                <div class="forecast-detail">
                    <span class="forecast-detail-label">Flow</span>
                    <span class="forecast-detail-value">${this.formatValue(data.conditions?.discharge, 'cfs')}</span>
                </div>
                <div class="forecast-detail">
                    <span class="forecast-detail-label">Wind</span>
                    <span class="forecast-detail-value">${this.formatValue(data.conditions?.windSpeed, 'mph')}</span>
                </div>
                <div class="forecast-detail">
                    <span class="forecast-detail-label">Gusts</span>
                    <span class="forecast-detail-value">${this.formatValue(data.conditions?.windGust, 'mph')}</span>
                </div>
                <div class="forecast-detail">
                    <span class="forecast-detail-label">Temp</span>
                    <span class="forecast-detail-value">${this.formatValue(data.conditions?.apparentTemp, '°F')}</span>
                </div>
            </div>
        `;

        return card;
    }

    updateDetailedForecast(filteredData = null) {
        const data = filteredData || this.getCurrentForecastData();
        if (!data || !data.length) return;

        const tbody = document.querySelector('#detailed-forecast-table tbody');
        tbody.innerHTML = '';

        data.forEach(item => {
            const row = document.createElement('tr');
            const time = new Date(item.timestamp);
            const conditions = item.conditions || {};
            
            const score = item.score || 0;
            const scoreClass = this.getScoreClass(score);
            const conditionsClass = this.getConditionsClass(score);

            row.innerHTML = `
                <td>${time.toLocaleString('en-US', { 
                    timeZone: 'America/New_York', // EST/EDT timezone
                    month: 'short', 
                    day: 'numeric', 
                    hour: 'numeric', 
                    hour12: true 
                })}</td>
                <td><span class="score-cell ${scoreClass}">${score.toFixed(1)}</span></td>
                <td>${this.formatValue(conditions.discharge, 'cfs')}</td>
                <td>${this.formatValue(conditions.windSpeed, 'mph')}</td>
                <td>${this.formatValue(conditions.windGust, 'mph')}</td>
                <td>${this.formatValue(conditions.apparentTemp, '°F')}</td>
                <td>${this.formatValue(conditions.waterTemp, '°F')}</td>
                <td><span class="conditions-indicator ${conditionsClass}">${this.getConditionsText(score)}</span></td>
            `;

            tbody.appendChild(row);
        });
    }

    updateCurrentConditions() {
        if (!this.currentData) return;

        this.updateWeatherDetails();
        this.updateWaterDetails();
        this.updateSafetyDetails();
    }

    updateWeatherDetails() {
        const weather = this.currentData.current?.weather;
        if (!weather) return;

        const container = document.getElementById('weather-details');
        container.innerHTML = `
            <div class="detail-item">
                <span class="detail-label">Temperature</span>
                <span class="detail-value">${this.formatValue(weather.currentTemp, '°F')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Feels Like</span>
                <span class="detail-value">${this.formatValue(weather.apparentTemp, '°F')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Wind Speed</span>
                <span class="detail-value">${this.formatValue(weather.windSpeed, 'mph')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Wind Gusts</span>
                <span class="detail-value">${this.formatValue(weather.windGust, 'mph')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Wind Direction</span>
                <span class="detail-value">${weather.windDir || 'N/A'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">UV Index</span>
                <span class="detail-value">${weather.uvIndex || 'N/A'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Visibility</span>
                <span class="detail-value">${this.formatValue(weather.visibility, 'mi')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Precipitation</span>
                <span class="detail-value">${this.formatValue(weather.precipitation, 'in')}</span>
            </div>
        `;
    }

    updateWaterDetails() {
        const water = this.currentData.current?.water;
        if (!water) return;

        const container = document.getElementById('water-details');
        container.innerHTML = `
            <div class="detail-item">
                <span class="detail-label">Discharge</span>
                <span class="detail-value">${this.formatValue(water.discharge, 'cfs')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Water Temperature</span>
                <span class="detail-value">${this.formatValue(water.waterTemp, '°F')}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Gauge Height</span>
                <span class="detail-value">${this.formatValue(water.gaugeHeight, 'ft')}</span>
            </div>
        `;
    }

    updateSafetyDetails() {
        const weather = this.currentData.current?.weather;
        const score = this.currentData.current?.rowcastScore || 0;
        
        const container = document.getElementById('safety-details');
        
        let alertsHtml = '';
        if (weather?.weatherAlerts && weather.weatherAlerts.length > 0) {
            alertsHtml = weather.weatherAlerts.map(alert => `
                <div class="alert alert-warning">
                    <strong>${alert.type || 'Weather Alert'}</strong>
                    ${alert.description ? `<br>${alert.description}` : ''}
                </div>
            `).join('');
        }

        const safetyLevel = this.getSafetyLevel(score);
        const safetyClass = this.getConditionsClass(score);

        container.innerHTML = `
            ${alertsHtml}
            <div class="detail-item">
                <span class="detail-label">Safety Level</span>
                <span class="detail-value">
                    <span class="conditions-indicator ${safetyClass}">${safetyLevel}</span>
                </span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Recommendation</span>
                <span class="detail-value">${this.getSafetyRecommendation(score)}</span>
            </div>
        `;
    }

    initializeCharts() {
        this.initializeScoreChart();
        this.initializeConditionsChart();
    }

    initializeScoreChart() {
        const ctx = document.getElementById('score-chart').getContext('2d');
        const data = this.getCurrentForecastData();
        
        if (!data || !data.length) return;

        const labels = data.map(item => {
            const time = new Date(item.timestamp);
            return time.toLocaleTimeString('en-US', { 
                timeZone: 'America/New_York',
                hour: 'numeric', 
                hour12: true 
            });
        });

        const scores = data.map(item => item.score || 0);

        if (this.charts.scoreChart) {
            this.charts.scoreChart.destroy();
        }

        this.charts.scoreChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'RowCast Score',
                    data: scores,
                    borderColor: '#007acc',
                    backgroundColor: 'rgba(0, 122, 204, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#007acc',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: '#333333'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    },
                    y: {
                        min: 0,
                        max: 10,
                        grid: {
                            color: '#333333'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    }
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                }
            }
        });
    }

    initializeConditionsChart() {
        const ctx = document.getElementById('conditions-chart').getContext('2d');
        const data = this.getCurrentForecastData();
        
        if (!data || !data.length) return;

        const labels = data.map(item => {
            const time = new Date(item.timestamp);
            return time.toLocaleTimeString('en-US', { 
                timeZone: 'America/New_York',
                hour: 'numeric', 
                hour12: true 
            });
        });

        const windSpeeds = data.map(item => item.conditions?.windSpeed || 0);
        const temps = data.map(item => item.conditions?.apparentTemp || 0);

        if (this.charts.conditionsChart) {
            this.charts.conditionsChart.destroy();
        }

        this.charts.conditionsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Wind Speed (mph)',
                        data: windSpeeds,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Temperature (°F)',
                        data: temps,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#b0b0b0'
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: '#333333'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: '#333333'
                        },
                        ticks: {
                            color: '#b0b0b0'
                        },
                        title: {
                            display: true,
                            text: 'Wind Speed (mph)',
                            color: '#28a745'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            color: '#b0b0b0'
                        },
                        title: {
                            display: true,
                            text: 'Temperature (°F)',
                            color: '#dc3545'
                        }
                    }
                }
            }
        });
    }

    getCurrentForecastData() {
        switch (this.currentTimeRange) {
            case '24h':
                return this.forecastData || [];
            case '7d':
            case 'extended':
                return this.extendedData || [];
            default:
                return this.forecastData || [];
        }
    }

    setTimeRange(range) {
        this.currentTimeRange = range;
        this.currentPage = 0;
        this.selectedDay = null; // Reset selected day

        // Update button states
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.range === range);
        });

        // Show/hide daily navigation in both locations
        const dailyNav = document.getElementById('daily-navigation');
        const quickNav = document.getElementById('daily-quick-nav');
        
        if (range === 'extended' || range === '7d') {
            if (dailyNav) dailyNav.style.display = 'block';
            if (quickNav) {
                quickNav.style.display = 'block';
                this.updateQuickDailyNavigation();
            }
            this.updateDailyNavigation();
        } else {
            if (dailyNav) dailyNav.style.display = 'none';
            if (quickNav) quickNav.style.display = 'none';
        }

        // Update displays
        this.updateForecastWidget();
        this.updateDetailedForecast();
        this.initializeCharts();
    }

    changeForecastPage(direction) {
        const data = this.getCurrentForecastData();
        const totalPages = Math.ceil(data.length / this.itemsPerPage);
        
        this.currentPage += direction;
        this.currentPage = Math.max(0, Math.min(this.currentPage, totalPages - 1));
        
        this.updateForecastWidget();
    }

    updatePagination(totalItems) {
        const totalPages = Math.ceil(totalItems / this.itemsPerPage);
        const currentPageDisplay = totalPages > 0 ? this.currentPage + 1 : 0;
        
        document.getElementById('page-indicator').textContent = `${currentPageDisplay} / ${totalPages}`;
        document.getElementById('prev-page').disabled = this.currentPage === 0;
        document.getElementById('next-page').disabled = this.currentPage >= totalPages - 1;
    }

    updateDailyNavigation() {
        const data = this.getCurrentForecastData();
        if (!data || !data.length) return;

        // Group data by day
        const dailyData = this.groupDataByDay(data);
        const container = document.getElementById('daily-cards');
        container.innerHTML = '';

        dailyData.forEach((dayData, index) => {
            const card = this.createDailyCard(dayData, index);
            container.appendChild(card);
        });
    }

    updateQuickDailyNavigation() {
        const data = this.getCurrentForecastData();
        if (!data || !data.length) return;

        const dailyData = this.groupDataByDay(data);
        const container = document.getElementById('daily-quick-cards');
        container.innerHTML = '';

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        dailyData.forEach((dayData, index) => {
            const card = this.createQuickDailyCard(dayData, index, today);
            container.appendChild(card);
        });
    }

    groupDataByDay(data) {
        const days = new Map();
        
        data.forEach(item => {
            const date = new Date(item.timestamp);
            date.setHours(0, 0, 0, 0); // Normalize to start of day
            const dayKey = date.getTime();
            
            if (!days.has(dayKey)) {
                days.set(dayKey, {
                    date: new Date(dayKey),
                    hours: []
                });
            }
            
            days.get(dayKey).hours.push(item);
        });

        return Array.from(days.values()).map(day => {
            const scores = day.hours.map(h => h.score || 0).filter(s => s > 0);
            const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b) / scores.length : 0;
            const maxScore = scores.length > 0 ? Math.max(...scores) : 0;
            const minScore = scores.length > 0 ? Math.min(...scores) : 0;
            
            // Calculate average conditions
            const avgTemp = this.calculateAverage(day.hours, h => h.conditions?.apparentTemp);
            const avgWind = this.calculateAverage(day.hours, h => h.conditions?.windSpeed);
            const maxWind = Math.max(...day.hours.map(h => h.conditions?.windGust || 0));
            
            return {
                ...day,
                avgScore: avgScore,
                maxScore: maxScore,
                minScore: minScore,
                avgTemp: avgTemp,
                avgWind: avgWind,
                maxWind: maxWind
            };
        });
    }

    calculateAverage(items, accessor) {
        const values = items.map(accessor).filter(v => v != null);
        return values.length > 0 ? values.reduce((a, b) => a + b) / values.length : null;
    }

    createDailyCard(dayData, index) {
        const card = document.createElement('div');
        card.className = 'daily-card';
        card.dataset.dayIndex = index;
        
        const dateStr = dayData.date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            weekday: 'short',
            month: 'short',
            day: 'numeric'
        });
        
        const avgScore = dayData.avgScore || 0;
        const scoreClass = this.getScoreClass(avgScore);
        
        card.innerHTML = `
            <button class="daily-card-expand" onclick="toggleDailyDetails(${index})" data-tooltip="Expand/collapse daily details">
                <i class="fas fa-chevron-down"></i>
            </button>
            <div class="daily-card-header">
                <div class="daily-date">${dateStr}</div>
                <div class="daily-avg-score ${scoreClass}">${avgScore.toFixed(1)}</div>
            </div>
            <div class="daily-summary">
                <div class="daily-summary-item">
                    <span class="daily-summary-label">Temp</span>
                    <span class="daily-summary-value">${this.formatValue(dayData.avgTemp, '°F')}</span>
                </div>
                <div class="daily-summary-item">
                    <span class="daily-summary-label">Wind</span>
                    <span class="daily-summary-value">${this.formatValue(dayData.avgWind, 'mph')}</span>
                </div>
                <div class="daily-summary-item">
                    <span class="daily-summary-label">Range</span>
                    <span class="daily-summary-value">${dayData.minScore.toFixed(1)}-${dayData.maxScore.toFixed(1)}</span>
                </div>
            </div>
            <div class="daily-details" id="daily-details-${index}">
                <div class="daily-hourly-preview" id="hourly-preview-${index}">
                    ${this.createHourlyPreview(dayData.hours)}
                </div>
            </div>
        `;
        
        // Add click handler to select day
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.daily-card-expand')) {
                this.selectDay(index, dayData);
            }
        });
        
        return card;
    }

    createQuickDailyCard(dayData, index, today) {
        const card = document.createElement('div');
        card.className = 'daily-quick-card';
        card.dataset.dayIndex = index;
        
        // Check if this is today
        const isToday = dayData.date.getTime() === today.getTime();
        if (isToday) {
            card.classList.add('today');
        }
        
        // Check for high flow warning (>= 13000 cfs)
        const hasHighFlow = dayData.hours.some(h => (h.conditions?.discharge || 0) >= 13000);
        if (hasHighFlow) {
            card.classList.add('quick-high-flow-warning');
        }
        
        const dateStr = dayData.date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            month: 'short',
            day: 'numeric'
        });
        
        const weekdayStr = dayData.date.toLocaleDateString('en-US', {
            timeZone: 'America/New_York',
            weekday: 'short'
        });
        
        const avgScore = dayData.avgScore || 0;
        const scoreClass = this.getScoreClass(avgScore);
        
        // Create summary text
        let summaryText = '';
        if (hasHighFlow) {
            summaryText = 'HIGH FLOW!<br>Not Safe';
        } else {
            const tempText = this.formatValue(dayData.avgTemp, '°');
            const windText = this.formatValue(dayData.avgWind, 'mph');
            summaryText = `${tempText}<br>${windText} wind`;
        }
        
        card.innerHTML = `
            <div class="quick-weekday">${weekdayStr}</div>
            <div class="quick-date">${dateStr}</div>
            <div class="quick-score ${scoreClass}">${avgScore.toFixed(1)}</div>
            <div class="quick-summary">${summaryText}</div>
        `;
        
        // Add click handler
        card.addEventListener('click', () => {
            this.selectQuickDay(index, dayData);
        });
        
        return card;
    }

    createHourlyPreview(hours) {
        return hours.slice(0, 12).map(hour => { // Show up to 12 hours
            const time = new Date(hour.timestamp);
            const timeStr = time.toLocaleTimeString('en-US', {
                timeZone: 'America/New_York',
                hour: 'numeric',
                hour12: true
            });
            const score = hour.score || 0;
            const scoreClass = this.getScoreClass(score);
            
            return `
                <div class="hourly-mini-card">
                    <div class="hourly-time">${timeStr}</div>
                    <div class="hourly-score ${scoreClass}">${score.toFixed(1)}</div>
                </div>
            `;
        }).join('');
    }

    selectDay(dayIndex, dayData) {
        // Update selected state
        document.querySelectorAll('.daily-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-day-index="${dayIndex}"]`).classList.add('selected');
        
        this.selectedDay = dayIndex;
        
        // Filter forecast data to show only selected day
        this.updateDetailedForecast(dayData.hours);
    }

    selectQuickDay(dayIndex, dayData) {
        // Update selected state for quick cards
        document.querySelectorAll('.daily-quick-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-day-index="${dayIndex}"]`).classList.add('selected');
        
        // Also update main daily cards if they exist
        const mainCards = document.querySelectorAll('.daily-card');
        mainCards.forEach(card => card.classList.remove('selected'));
        const mainCard = document.querySelector(`.daily-card[data-day-index="${dayIndex}"]`);
        if (mainCard) mainCard.classList.add('selected');
        
        this.selectedDay = dayIndex;
        
        // Show day-specific forecast in the main forecast grid
        this.updateForecastWidget(dayData.hours);
        
        // Also update detailed forecast
        this.updateDetailedForecast(dayData.hours);
        
        // Update charts with day data
        this.initializeCharts(dayData.hours);
    }

    async loadAPIDocumentation() {
        const container = document.querySelector('.api-docs-content');
        
        // Redirect to the dedicated documentation page
        window.open('/documentation', '_blank');
        
        // Also show a simplified version inline
        container.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <h2 style="color: var(--accent-tertiary); margin-bottom: 1rem;">
                    <i class="fas fa-external-link-alt"></i> 
                    API Documentation
                </h2>
                <p style="color: var(--text-secondary); margin-bottom: 2rem;">
                    Complete API documentation has opened in a new tab.
                </p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
                    <div class="api-endpoint">
                        <div class="endpoint-header">
                            <span class="http-method method-get">GET</span>
                            <span class="endpoint-url">
                                <a href="${this.baseURL}/api/complete" target="_blank">
                                    ${this.baseURL}/api/complete
                                </a>
                            </span>
                        </div>
                        <div class="endpoint-description">Get all current data and forecasts</div>
                    </div>
                    <div class="api-endpoint">
                        <div class="endpoint-header">
                            <span class="http-method method-get">GET</span>
                            <span class="endpoint-url">
                                <a href="${this.baseURL}/api/rowcast/forecast" target="_blank">
                                    ${this.baseURL}/api/rowcast/forecast
                                </a>
                            </span>
                        </div>
                        <div class="endpoint-description">24-hour rowing condition forecast</div>
                    </div>
                    <div class="api-endpoint">
                        <div class="endpoint-header">
                            <span class="http-method method-get">GET</span>
                            <span class="endpoint-url">
                                <a href="${this.baseURL}/api/rowcast/forecast/2h" target="_blank">
                                    ${this.baseURL}/api/rowcast/forecast/2h
                                </a>
                            </span>
                        </div>
                        <div class="endpoint-description">Conditions in 2 hours</div>
                    </div>
                    <div class="api-endpoint">
                        <div class="endpoint-header">
                            <span class="http-method method-get">GET</span>
                            <span class="endpoint-url">
                                <a href="${this.baseURL}/api/rowcast/forecast/extended" target="_blank">
                                    ${this.baseURL}/api/rowcast/forecast/extended
                                </a>
                            </span>
                        </div>
                        <div class="endpoint-description">Extended forecast (up to 7 days)</div>
                    </div>
                </div>
                <div style="margin-top: 2rem;">
                    <a href="/documentation" target="_blank" class="refresh-btn">
                        <i class="fas fa-book"></i>
                        View Full Documentation
                    </a>
                </div>
            </div>
        `;
    }

    async refreshData() {
        this.showLoading();
        try {
            await this.loadInitialData();
        } catch (error) {
            this.showError('Failed to refresh data. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    startDataRefresh() {
        // Refresh data every 5 minutes
        setInterval(() => {
            this.refreshData();
        }, 5 * 60 * 1000);
    }

    showLoading() {
        document.getElementById('loading-overlay').classList.add('show');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.remove('show');
    }

    showError(message) {
        // You could implement a toast notification system here
        console.error(message);
    }

    // Utility methods
    formatValue(value, unit = '') {
        if (value === null || value === undefined) return 'N/A';
        if (typeof value === 'number') {
            return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}${unit ? ' ' + unit : ''}`;
        }
        return value.toString();
    }

    getScoreClass(score) {
        if (score >= 8) return 'score-excellent';
        if (score >= 6) return 'score-good';
        if (score >= 4) return 'score-fair';
        return 'score-poor';
    }

    getConditionsClass(score) {
        if (score >= 8) return 'conditions-excellent';
        if (score >= 6) return 'conditions-good';
        if (score >= 4) return 'conditions-fair';
        return 'conditions-poor';
    }

    getConditionsText(score) {
        if (score >= 8) return 'Excellent';
        if (score >= 6) return 'Good';
        if (score >= 4) return 'Fair';
        return 'Poor';
    }

    getSafetyLevel(score) {
        if (score >= 8) return 'Very Safe';
        if (score >= 6) return 'Safe';
        if (score >= 4) return 'Caution';
        return 'Not Recommended';
    }

    getSafetyRecommendation(score) {
        if (score >= 8) return 'Excellent conditions for rowing';
        if (score >= 6) return 'Good conditions with minor considerations';
        if (score >= 4) return 'Fair conditions - exercise caution';
        return 'Poor conditions - consider postponing';
    }

    // Tooltip functionality
    initializeTooltips() {
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.id = 'tooltip';
        tooltip.className = 'tooltip';
        document.body.appendChild(tooltip);

        // Add event listeners to all elements with data-tooltip
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e, element.dataset.tooltip);
            });

            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });

            element.addEventListener('mousemove', (e) => {
                this.positionTooltip(e);
            });
        });
    }

    showTooltip(event, text) {
        const tooltip = document.getElementById('tooltip');
        tooltip.textContent = text;
        tooltip.classList.add('tooltip-visible');
        this.positionTooltip(event);
    }

    hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        tooltip.classList.remove('tooltip-visible');
    }

    positionTooltip(event) {
        const tooltip = document.getElementById('tooltip');
        const tooltipRect = tooltip.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let left = event.pageX + 10;
        let top = event.pageY - 10;

        // Adjust position if tooltip would go off screen
        if (left + tooltipRect.width > viewportWidth) {
            left = event.pageX - tooltipRect.width - 10;
        }

        if (top - tooltipRect.height < 0) {
            top = event.pageY + 20;
        }

        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
    }
}

// Global functions for HTML event handlers
function refreshData() {
    if (window.dashboard) {
        window.dashboard.refreshData();
    }
}

function changeForecastPage(direction) {
    if (window.dashboard) {
        window.dashboard.changeForecastPage(direction);
    }
}

function toggleDailyDetails(dayIndex) {
    const details = document.getElementById(`daily-details-${dayIndex}`);
    const button = document.querySelector(`[onclick="toggleDailyDetails(${dayIndex})"] i`);
    
    if (details && button) {
        const isVisible = details.style.display === 'block';
        details.style.display = isVisible ? 'none' : 'block';
        button.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new RowCastDashboard();
});
