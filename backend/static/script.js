// AI Travel Planner - Complete Frontend JavaScript
class TravelPlanner {
    constructor() {
        this.map = null;
        this.markers = [];
        this.currentPlan = null;
        this.selectedPOIs = [];
        this.selectedPOIDetails = [];
        this.regenTimer = null;
        this.locations = {};
        this.savedPlans = []; // Initialize saved plans array
        
        this.init();
    }

    init() {
        console.log('Initializing TravelPlanner...');
        this.setupEventListeners();
        this.loadSavedPlans();
        this.setupTabs();
        this.loadLocations();
        this.checkAuthStatus();
        
        // Apply initial mood styling
        const moodSelect = document.getElementById('mood');
        if (moodSelect) {
            this.applyMoodStyling(moodSelect.value);
        }
        
        console.log('TravelPlanner initialized');
    }



    setupEventListeners() {
        // Google Login functionality
        this.setupGoogleLogin();
        
        // Form submissions
        document.getElementById('manual-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleManualPlan();
        });

        document.getElementById('ai-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleAIPlan();
        });

        // Plan actions
        document.getElementById('save-plan-btn').addEventListener('click', () => {
            this.saveCurrentPlan();
        });

        document.getElementById('new-plan-btn').addEventListener('click', () => {
            this.resetToInput();
        });

        // Global event delegation for dynamic elements
        document.addEventListener('click', (e) => {
            if (e.target.closest('.poi-toggle')) {
                this.togglePOISelection(e.target.closest('.poi-toggle'));
            }

            if (e.target.closest('.delete-btn')) {
                this.deletePlan(e.target.closest('.plan-card').dataset.planId);
            }
            if (e.target.closest('.view-btn')) {
                const btn = e.target.closest('.view-btn');
                let pid = btn && btn.dataset ? btn.dataset.planId : undefined;
                if (!pid) {
                    const card = e.target.closest('.plan-card');
                    pid = card && card.dataset ? card.dataset.planId : undefined;
                }
                if (!pid) return this.showToast('Plan id missing', 'error');
                this.viewPlan(pid);
            }
            if (e.target.closest('.modify-btn')) {
                const btn = e.target.closest('.modify-btn');
                let pid = btn && btn.dataset ? btn.dataset.planId : undefined;
                if (!pid) {
                    const card = e.target.closest('.plan-card');
                    pid = card && card.dataset ? card.dataset.planId : undefined;
                }
                if (!pid) return this.showToast('Plan id missing', 'error');
                this.modifyPlan(pid);
            }

            if (e.target.matches('.toggle-other-packing')) {
                const wrap = document.getElementById('other-packing-groups');
                if (wrap) {
                    wrap.classList.toggle('hidden');
                    e.target.textContent = wrap.classList.contains('hidden') ? 'Show other groups' : 'Hide other groups';
                }
            }

            if (e.target.closest('.add-plan-btn')) {
                const btn = e.target.closest('.add-plan-btn');
                const dayNumber = parseInt(btn.dataset.day);
                this.addNewPlanForDay(dayNumber);
            }
        });

        const budget = document.getElementById('budget');
        const budgetLabel = document.getElementById('budget-label');
        if (budget && budgetLabel) {
            budget.addEventListener('input', () => {
                budgetLabel.textContent = `₹${parseInt(budget.value).toLocaleString('en-IN')}`;
            });
        }

        // Interest cards selection
        const interestCards = document.getElementById('interests-cards');
        if (interestCards) {
            interestCards.addEventListener('click', (e) => {
                const card = e.target.closest('.interest-card');
                if (!card) return;
                card.classList.toggle('active');
                const selected = Array.from(interestCards.querySelectorAll('.interest-card.active')).map(c => c.dataset.value);
                const hidden = document.getElementById('interests');
                if (hidden) hidden.value = selected.join(',');
            });
        }

        // Auto-populate interests when mood changes
        const moodSelect = document.getElementById('mood');
        if (moodSelect) {
            moodSelect.addEventListener('change', () => {
                this.applyMoodInterests(moodSelect.value);
                this.applyMoodStyling(moodSelect.value);
            });
        }

        // Cascading location selectors for manual form
        const countrySelect = document.getElementById('countrySelect');
        const stateSelect = document.getElementById('stateSelect');
        const citySelect = document.getElementById('citySelect');
        if (countrySelect && stateSelect && citySelect) {
            countrySelect.addEventListener('change', () => {
                this.populateStates(countrySelect.value);
                stateSelect.disabled = !countrySelect.value;
                citySelect.disabled = true;
                stateSelect.classList.add('fade-in');
                citySelect.classList.remove('fade-in');
            });
            stateSelect.addEventListener('change', () => {
                this.populateCities(countrySelect.value, stateSelect.value);
                citySelect.disabled = !stateSelect.value;
                citySelect.classList.add('fade-in');
            });
            citySelect.addEventListener('change', () => {
                const city = citySelect.value || '';
                const state = stateSelect.value || '';
                const country = countrySelect.value || '';
                const destinationInput = document.getElementById('destination');
                if (city && destinationInput) {
                    const parts = [city, state, country].filter(Boolean);
                    destinationInput.value = parts.join(', ');
                }
            });
        }

        // Cascading location selectors for AI form
        const aiCountrySelect = document.getElementById('ai_countrySelect');
        const aiStateSelect = document.getElementById('ai_stateSelect');
        const aiCitySelect = document.getElementById('ai_citySelect');
        if (aiCountrySelect && aiStateSelect && aiCitySelect) {
            aiCountrySelect.addEventListener('change', () => {
                this.populateAIStates(aiCountrySelect.value);
                aiStateSelect.disabled = !aiCountrySelect.value;
                aiCitySelect.disabled = true;
                aiStateSelect.classList.add('fade-in');
                aiCitySelect.classList.remove('fade-in');
            });
            aiStateSelect.addEventListener('change', () => {
                this.populateAICities(aiCountrySelect.value, aiStateSelect.value);
                aiCitySelect.disabled = !aiStateSelect.value;
                aiCitySelect.classList.add('fade-in');
            });
        }
    }

    setupTabs() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.dataset.tab;
                
                // Update active tab button
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update active tab content
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === `${targetTab}-tab`) {
                        content.classList.add('active');
                    }
                });
            });
        });
    }

    setupGoogleLogin() {
        // Google Login button
        const googleLoginBtn = document.getElementById('google-login-btn');
        if (googleLoginBtn) {
            googleLoginBtn.addEventListener('click', () => {
                this.initiateGoogleLogin();
            });
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/user/is-authenticated');
            const data = await response.json();
            
            if (data.authenticated) {
                this.showUserSection(data.user);
            } else {
                this.showLoginSection();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            this.showLoginSection();
        }
    }

    initiateGoogleLogin() {
        window.location.href = '/auth/google/login';
    }

    async logout() {
        try {
            const response = await fetch('/auth/google/logout', {
                method: 'GET'
            });
            
            if (response.ok) {
                this.showLoginSection();
                this.showToast('Successfully logged out', 'success');
            } else {
                this.showToast('Error logging out', 'error');
            }
        } catch (error) {
            console.error('Error during logout:', error);
            this.showToast('Error logging out', 'error');
        }
    }

    showUserSection(user) {
        const loginSection = document.getElementById('login-section');
        const userSection = document.getElementById('user-section');
        const userAvatar = document.getElementById('user-avatar');
        const userName = document.getElementById('user-name');

        if (loginSection) loginSection.style.display = 'none';
        if (userSection) userSection.style.display = 'flex';
        
        if (userAvatar && user.picture) {
            userAvatar.src = user.picture;
        }
        
        if (userName && user.name) {
            userName.textContent = user.name;
        }
    }

    showLoginSection() {
        const loginSection = document.getElementById('login-section');
        const userSection = document.getElementById('user-section');

        if (loginSection) loginSection.style.display = 'block';
        if (userSection) userSection.style.display = 'none';
    }

    async handleManualPlan() {
        const formData = new FormData(document.getElementById('manual-form'));
        const userName = formData.get('name') || '';
        const userAge = formData.get('age') || '';
        const userGender = formData.get('gender') || '';
        const selectedCity = (document.getElementById('citySelect') || {}).value || '';
        const selectedState = (document.getElementById('stateSelect') || {}).value || '';
        const selectedCountry = (document.getElementById('countrySelect') || {}).value || '';
        const destination = selectedCity ? [selectedCity, selectedState, selectedCountry].filter(Boolean).join(', ') : formData.get('destination');
        const startDate = formData.get('start_date');
        const days = parseInt(formData.get('days'));
        const mood = formData.get('mood');
        const interests = Array.from(document.querySelectorAll('input[name="interests"]:checked')).map(i => i.value);
        // Merge with card selections
        const cardHidden = document.getElementById('interests')?.value || '';
        const cardInterests = cardHidden ? cardHidden.split(',').filter(Boolean) : [];
        const allInterests = Array.from(new Set([...(interests || []), ...cardInterests]));
        const budget = parseInt(formData.get('budget')) || undefined;

        if (!destination || !days || !mood) {
            this.showToast('Please fill in all fields', 'error');
            return;
        }

        this.showLoading();
        
        try {
            // Step 1: Get places
            const places = await this.fetchPlaces(destination, days, allInterests);
            

            
            // Merge interests with selected POI categories
            const poiInterestHints = (this.selectedPOIDetails || []).map(p => (p.category || '').toLowerCase()).filter(Boolean);
            const mergedInterests = Array.from(new Set([...(allInterests || []), ...poiInterestHints]));

            // Prefer selected POIs if any
            const poisForAI = (this.selectedPOIDetails && this.selectedPOIDetails.length)
                ? this.selectedPOIDetails.map(p => ({ name: p.name, category: p.category, entry_fee: p.entry_fee }))
                : places;
            
            // Step 3: Generate itinerary
            const itinerary = await this.generateItinerary({
                city: destination,
                start_date: startDate || new Date().toISOString().split('T')[0],
                days: days,
                mood: mood,
                interests: mergedInterests,
                pois: poisForAI,
                name: userName,
                age: userAge,
                gender: userGender
            });

            // Step 4: Display results
            this.displayPlan({
                destination: destination,
                start_date: startDate,
                days: days,
                mood: mood,
                places: poisForAI,
                itinerary: itinerary.itinerary,
                famous_places: itinerary.famous_places,
                total_budget: itinerary.total_budget_inr,
                packing_list: itinerary.packing_list,
                weather: itinerary.itinerary?.map(d => ({ day: `Day ${d.day}`, temperature: `${d.weather?.high || ''}/${d.weather?.low || ''}`, forecast: d.weather?.summary || '' })) || [],
                country: selectedCountry,
                state: selectedState,
                city: selectedCity,
                name: itinerary.name || userName,
                age: itinerary.age || userAge,
                gender: itinerary.gender || userGender,
                interests: mergedInterests
            });

        } catch (error) {
            console.error('Error generating plan:', error);
            this.showToast('Error generating plan. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleAIPlan() {
        const formData = new FormData(document.getElementById('ai-form'));
        const prompt = formData.get('prompt');
        const mood = formData.get('mood');
        const days = formData.get('days') || '3';
        const userName = formData.get('name') || '';
        const userAge = formData.get('age') || '';
        const userGender = formData.get('gender') || '';
        const selectedCity = (document.getElementById('ai_citySelect') || {}).value || '';
        const selectedState = (document.getElementById('ai_stateSelect') || {}).value || '';
        const selectedCountry = (document.getElementById('ai_countrySelect') || {}).value || '';
        const destination = selectedCity ? [selectedCity, selectedState, selectedCountry].filter(Boolean).join(', ') : '';

        if (!prompt || !mood || !destination) {
            this.showToast('Please fill in all fields including location selection', 'error');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch('/ask-agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    mood: mood,
                    days: parseInt(days),
                    name: userName,
                    age: userAge,
                    gender: userGender,
                    destination: destination,
                    country: selectedCountry,
                    state: selectedState,
                    city: selectedCity
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate AI plan');
            }

            const data = await response.json();
            this.displayPlan({
                ...data,
                days: parseInt(days),
                name: data.name || userName,
                age: data.age || userAge,
                gender: data.gender || userGender,
                destination: destination,
                country: selectedCountry,
                state: selectedState,
                city: selectedCity
            });

        } catch (error) {
            console.error('Error generating AI plan:', error);
            this.showToast('Error generating AI plan. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async fetchPlaces(city, days, interests) {
        try {
            const interestsCsv = interests && interests.length ? `&interests=${encodeURIComponent(interests.join(','))}` : '';
            const mood = document.getElementById('mood')?.value || '';
            const response = await fetch(`/api/places?city=${encodeURIComponent(city)}&days=${days}${interestsCsv}&mood=${encodeURIComponent(mood)}`);
            if (!response.ok) {
                throw new Error('Failed to fetch places');
            }
            const data = await response.json();
            return data.places || [];
        } catch (error) {
            console.error('Error fetching places:', error);
            return [];
        }
    }



    async generateItinerary(planData) {
        try {
            const response = await fetch('/api/itinerary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(planData)
            });
            
            if (!response.ok) {
                throw new Error('Failed to generate itinerary');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Error generating itinerary:', error);
            throw error;
        }
    }

    displayPlan(planData) {
        this.currentPlan = planData;
        
        // Create plan card from template
        const template = document.getElementById('plan-template');
        const planCard = template.content.cloneNode(true);
        
        // Personalized greeting
        const greetEl = document.getElementById('greet-text');
        const greetSummary = document.getElementById('greet-summary');
        if (greetEl) {
            if (planData.name) {
                greetEl.textContent = `Hi ${planData.name}, here's your Smart Travel Plan!`;
            } else {
                greetEl.textContent = `Here's your Smart Travel Plan!`;
            }
        }
        if (greetSummary) {
            const moodEmoji = this.getMoodEmoji(planData.mood);
            const dateStr = planData.start_date ? new Date(planData.start_date).toLocaleDateString() : new Date().toLocaleDateString();
            greetSummary.textContent = `${planData.destination}\n${planData.days} Days | ${moodEmoji} ${planData.mood?.charAt(0).toUpperCase() + planData.mood?.slice(1)} | ${dateStr}`;
        }

        // Set basic plan info
        const planTitle = planCard.querySelector('.plan-title');
        const planDays = planCard.querySelector('.plan-days');
        const planMood = planCard.querySelector('.plan-mood');
        const planDate = planCard.querySelector('.plan-date');
        
        planTitle.textContent = planData.destination;
        planDays.textContent = `${planData.days} days`;
        planMood.textContent = this.getMoodEmoji(planData.mood);
        planDate.textContent = new Date().toLocaleDateString();

        // Render weather forecast
        this.renderWeatherForecast(planCard.querySelector('.weather-forecast'), planData.weather);
        
        // Render attractions
        this.renderAttractions(
            planCard.querySelector('.attractions-grid'),
            Array.isArray(planData.famous_places) ? planData.famous_places : (Array.isArray(planData.places) ? planData.places : [])
        );
        
        // If attractions missing/empty, fetch as fallback and render once received
        const attractionsContainer = planCard.querySelector('.attractions-grid');
        const initialAttractions = Array.isArray(planData.famous_places) ? planData.famous_places : (Array.isArray(planData.places) ? planData.places : []);
        if (!initialAttractions || initialAttractions.length === 0) {
            attractionsContainer.innerHTML = '<div class="loading-msg">Loading must-visit attractions…</div>';
            const cityName = this.currentPlan?.city || this.currentPlan?.destination || '';
            if (cityName) {
                this.fetchPlaces(cityName, this.currentPlan?.days || 3, this.currentPlan?.interests || [])
                    .then(list => {
                        // Save for later re-renders
                        this.currentPlan = this.currentPlan || {};
                        this.currentPlan.famous_places = list;
                        this.renderAttractions(attractionsContainer, list || []);
                        // Re-run after map centers
                        this.rerenderAttractionsForMapCenter();
                    })
                    .catch(() => {
                        attractionsContainer.innerHTML = '<p>No attractions found</p>';
                    });
            }
        }

        
        // Render itinerary
        this.renderItinerary(planCard.querySelector('.daily-itinerary'), planData.itinerary);



        // Render budget
        this.renderBudget(planCard, planData.total_budget, planData.days);

        // Render packing list (if element present)
        const packingEl = planCard.querySelector('.packing-list');
        if (packingEl) {
            this.renderPackingList(packingEl, planData.packing_list);
        }


        
        // Initialize map
        this.initializeMap(
            planCard.querySelector('.map-container'),
            Array.isArray(planData.famous_places) ? planData.famous_places : (Array.isArray(planData.places) ? planData.places : [])
        );

        // Replace current plan content
        const currentPlanDiv = document.getElementById('current-plan');
        currentPlanDiv.innerHTML = '';
        currentPlanDiv.appendChild(planCard);
        
        // Initialize map AFTER the card is mounted in the DOM so Leaflet can measure size correctly
        try {
            const mountedCard = currentPlanDiv.querySelector('.plan-card');
            const mountedContainer = mountedCard ? mountedCard.querySelector('.map-container') : null;
            this.initializeMap(
                mountedContainer,
                Array.isArray(planData.famous_places) ? planData.famous_places : (Array.isArray(planData.places) ? planData.places : [])
            );
            // Force a size recalculation shortly after mount
            setTimeout(() => { try { this.map && this.map.invalidateSize(true); } catch(_){} }, 50);
        } catch(_) {}
        
        // Show plan section
        document.getElementById('current-plan-section').classList.remove('hidden');
        
        // Scroll to plan
        document.getElementById('current-plan-section').scrollIntoView({ behavior: 'smooth' });
    }

    renderBudget(planCard, totalBudgetStr, days) {
        const totalEl = planCard.querySelector('#budget-total');
        const breakdownEl = planCard.querySelector('#budget-breakdown');
        if (!totalEl || !breakdownEl) return;
        
        let total = 0;
        let budgetBreakdown = null;
        
        // Check if we have detailed budget breakdown from AI
        if (this.currentPlan && this.currentPlan.budget_breakdown) {
            budgetBreakdown = this.currentPlan.budget_breakdown;
            total = budgetBreakdown.total || 0;
        } else {
            // Fallback to string parsing
            if (typeof totalBudgetStr === 'string') {
                total = parseInt(totalBudgetStr.replace(/[^0-9]/g, '')) || 0;
            } else if (typeof totalBudgetStr === 'number') {
                total = totalBudgetStr;
            }
        }
        
        totalEl.textContent = `₹${(total || 0).toLocaleString('en-IN')}`;
        
        if (budgetBreakdown) {
            // Use AI-generated budget breakdown
            breakdownEl.innerHTML = `
                <div class="budget-item"><i class="fas fa-hotel"></i> Accommodation: ₹${(budgetBreakdown.accommodation || 0).toLocaleString('en-IN')}</div>
                <div class="budget-item"><i class="fas fa-utensils"></i> Food: ₹${(budgetBreakdown.food || 0).toLocaleString('en-IN')}</div>
                <div class="budget-item"><i class="fas fa-bus"></i> Transportation: ₹${(budgetBreakdown.transportation || 0).toLocaleString('en-IN')}</div>
                <div class="budget-item"><i class="fas fa-ticket-alt"></i> Activities: ₹${(budgetBreakdown.activities || 0).toLocaleString('en-IN')}</div>
                <div class="budget-item"><i class="fas fa-shopping-bag"></i> Shopping: ₹${(budgetBreakdown.shopping || 0).toLocaleString('en-IN')}</div>
            `;
        } else {
            // Fallback to calculated breakdown
            const perDay = days ? Math.round(total / days) : total;
            const lodging = Math.round(perDay * 0.5);
            const food = Math.round(perDay * 0.25);
            const activities = Math.round(perDay * 0.15);
            const transit = Math.round(perDay * 0.10);
            breakdownEl.innerHTML = `
                <div class="budget-item"><i class="fas fa-hotel"></i> Lodging: ₹${lodging.toLocaleString('en-IN')}/day</div>
                <div class="budget-item"><i class="fas fa-utensils"></i> Food: ₹${food.toLocaleString('en-IN')}/day</div>
                <div class="budget-item"><i class="fas fa-ticket-alt"></i> Activities: ₹${activities.toLocaleString('en-IN')}/day</div>
                <div class="budget-item"><i class="fas fa-bus"></i> Transit: ₹${transit.toLocaleString('en-IN')}/day</div>
            `;
        }
    }











    renderWeatherForecast(container, weatherData) {
        if (!weatherData || !Array.isArray(weatherData)) {
            container.innerHTML = '<p>Weather data not available</p>';
            return;
        }

        const weatherHTML = weatherData.map(day => `
            <div class="weather-day">
                <h5>${day.day}</h5>
                <div class="temp">${day.temperature}</div>
                <div class="forecast">${day.forecast}</div>
            </div>
        `).join('');
        
        container.innerHTML = weatherHTML;
    }

    renderAttractions(container, attractions) {
        if (!container) return;
        // Ensure minimal styles so cards render visibly even if external CSS is delayed
        this.ensureAttractionStyles();
        if (!attractions || !Array.isArray(attractions)) {
            container.innerHTML = '<p>No attractions found</p>';
            return;
        }

        // Compute a score based on rating and proximity to current map center (if available)
        const center = (() => {
            try { return this.map && this.map.getCenter ? this.map.getCenter() : null; } catch(_) { return null; }
        })();
        const toNum = (v, d=0) => {
            const n = parseFloat(v);
            return isNaN(n) ? d : n;
        };
        const distKm = (a, b) => {
            if (!a || !b) return Infinity;
            const R = 6371;
            const dLat = (b.lat - a.lat) * Math.PI/180;
            const dLon = (b.lng - a.lng) * Math.PI/180;
            const sa = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(a.lat*Math.PI/180) * Math.cos(b.lat*Math.PI/180) * Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(sa), Math.sqrt(1-sa));
            return R * c;
        };

        const scored = attractions.map(a => {
            const rating = toNum(a.rating, 4.3);
            const lat = toNum(a.lat, NaN);
            const lon = toNum(a.lon, NaN);
            const distance = (!isNaN(lat) && !isNaN(lon) && center) ? distKm({ lat: center.lat, lng: center.lng }, { lat, lng: lon }) : 10_000;
            // Higher rating and closer distance => better. Weight: rating*10 minus distance factor
            const score = (rating * 10) - (distance * 0.5);
            return { a, score, distance };
        });
        scored.sort((x, y) => y.score - x.score);

        const attractionsHTML = scored.map((wrap, idx) => {
            const attraction = wrap.a;
            const entryFee = attraction.entry_fee || attraction.fee || 'Free';
            const bestTime = attraction.best_time || attraction.visiting_time || 'Anytime';
            const rating = attraction.rating || '4.5';
            const googleMapsLink = attraction.google_maps_link || attraction.source || '';
            const candidates = this.getImageCandidates(attraction);
            const firstSrc = candidates[0] || '/static/placeholder.jpg';
            const dataSrcs = candidates.slice(1).join('|');
            const badge = idx === 0 ? '<div class="badge-most-famous" title="Top pick near your selected location">Most Famous</div>' : '';
            
            return `
                <div class="attraction-card" data-poi-id="${attraction.id || attraction.xid}">
                    <div class="attraction-image-container">
                        <img src="${firstSrc}" data-fallbacks="${dataSrcs}" alt="${attraction.name}" class="attraction-image">
                        ${googleMapsLink ? `<a href="${googleMapsLink}" target="_blank" class="maps-link" title="View on Google Maps">
                            <i class="fas fa-map-marker-alt"></i>
                        </a>` : ''}
                        ${badge}
                    </div>
                    <div class="attraction-info">
                        <h5 class="attraction-name">${attraction.name}</h5>
                        <p class="attraction-description">${attraction.description || attraction.summary || 'No description available'}</p>
                        <div class="attraction-details">
                            <span class="attraction-fee"><i class="fas fa-ticket-alt"></i> Entry: ${entryFee}</span>
                            <span class="attraction-time"><i class="fas fa-clock"></i> Best Time: ${bestTime}</span>
                            <span class="attraction-rating"><i class="fas fa-star"></i> ${rating}</span>
                        </div>
                        <div class="attraction-actions">
                            <button class="poi-toggle" data-poi-id="${attraction.id || attraction.xid}"
                                data-name="${(attraction.name || '').replace(/"/g,'&quot;')}"
                                data-category="${(attraction.category || '').replace(/"/g,'&quot;')}"
                                data-entry_fee="${(attraction.entry_fee || '').replace(/"/g,'&quot;')}">
                                <i class="fas fa-plus"></i> Add to Plan
                            </button>
                            ${googleMapsLink ? `<a href="${googleMapsLink}" target="_blank" class="maps-btn" title="View on Google Maps">
                                <i class="fas fa-map-marker-alt"></i> View on Map
                            </a>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = attractionsHTML;
        this.loadAttractionImages(container);
        // Asynchronously improve image accuracy using Wikimedia for well-known places
        this.enhanceAttractionImages(container);
    }

    getImageCandidates(attraction) {
        const list = [];
        const city = (this.currentPlan?.city || this.currentPlan?.destination || '').split(',')[0] || '';
        const name = (attraction?.name || '').trim();
        const category = (attraction?.category || '').trim();
        const baseQuery = encodeURIComponent([category, name, city].filter(Boolean).join(','));
        if (attraction?.image) list.push(attraction.image);
        // Unsplash source (can 302)
        list.push(`https://source.unsplash.com/featured/800x600/?${baseQuery}`);
        // Picsum by seed to ensure an image even if Unsplash blocked
        const seed = encodeURIComponent(`${name}-${city}-${category}` || 'travel');
        list.push(`https://picsum.photos/seed/${seed}/800/600`);
        // Final placeholder
        list.push('/static/placeholder.jpg');
        return list;
    }

    loadAttractionImages(container) {
        try {
            const imgs = Array.from(container.querySelectorAll('img.attraction-image'));
            imgs.forEach(img => {
                img.addEventListener('error', () => {
                    const fallbacks = (img.getAttribute('data-fallbacks') || '').split('|').filter(Boolean);
                    if (fallbacks.length) {
                        const next = fallbacks.shift();
                        img.setAttribute('data-fallbacks', fallbacks.join('|'));
                        img.src = next;
                    } else {
                        img.src = '/static/placeholder.jpg';
                    }
                }, { once: false });
            });
        } catch(_) {}
    }

    async enhanceAttractionImages(container) {
        try {
            const cards = Array.from(container.querySelectorAll('.attraction-card'));
            // Map DOM card to minimal attraction data if available via dataset or by index from current plan arrays
            const list = Array.isArray(this.currentPlan?.famous_places) ? this.currentPlan.famous_places : (Array.isArray(this.currentPlan?.places) ? this.currentPlan.places : []);
            const city = (this.currentPlan?.city || this.currentPlan?.destination || '').split(',')[0] || '';
            // Only enrich the first 8 cards to limit network calls
            for (let i = 0; i < Math.min(cards.length, 8); i++) {
                const card = cards[i];
                const title = (card.querySelector('.attraction-name')?.textContent || '').trim();
                const img = card.querySelector('img.attraction-image');
                if (!img || !title) continue;
                const currentSrc = img.getAttribute('src') || '';
                if (currentSrc && !currentSrc.includes('/static/') && !currentSrc.includes('picsum.photos') && !currentSrc.includes('source.unsplash.com')) continue;

                // Try geosearch first when coordinates are known
                let found = null;
                const item = list[i] || {};
                const lat = parseFloat(item.lat);
                const lon = parseFloat(item.lon);
                if (!isNaN(lat) && !isNaN(lon)) {
                    found = await this.getWikimediaImageByGeo(lat, lon, title);
                }
                // Fallback to title + city
                if (!found) {
                    found = await this.getWikimediaImage(`${title} ${city}`.trim());
                }
                if (found && typeof found === 'string') {
                    img.src = found;
                    img.removeAttribute('data-fallbacks');
                }
            }
        } catch(_) {}
    }

    async getWikimediaImageByGeo(lat, lon, titleHint) {
        try {
            const radius = 8000; // 8km radius
            const url = `https://en.wikipedia.org/w/api.php?origin=*&action=query&list=geosearch&gscoord=${lat}%7C${lon}&gsradius=${radius}&gslimit=10&format=json`;
            const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) return null;
            const data = await res.json();
            const pages = (data?.query?.geosearch) || [];
            if (!pages.length) return null;
            // Prefer result whose title semantically matches the hint
            const normalizedHint = (titleHint || '').toLowerCase();
            pages.sort((a,b)=>{
                const aScore = (a?.title || '').toLowerCase().includes(normalizedHint) ? 1 : 0;
                const bScore = (b?.title || '').toLowerCase().includes(normalizedHint) ? 1 : 0;
                return bScore - aScore;
            });
            const chosen = pages[0];
            if (!chosen) return null;
            const pageTitle = chosen.title;
            const img = await this.getWikimediaImage(pageTitle);
            return img;
        } catch(_) { return null; }
    }

    async getWikimediaImage(query) {
        try {
            const url = `https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages|pageterms&piprop=original|thumbnail&pithumbsize=800&format=json&titles=${encodeURIComponent(query)}`;
            const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
            if (!res.ok) return null;
            const data = await res.json();
            const pages = (data && data.query && data.query.pages) ? data.query.pages : {};
            const first = Object.values(pages)[0];
            if (!first) return null;
            const src = (first.original && first.original.source) || (first.thumbnail && first.thumbnail.source);
            return src || null;
        } catch(_) { return null; }
    }

    getFallbackAttractionImage(attraction) {
        try {
            const tokens = [];
            const city = (this.currentPlan?.city || this.currentPlan?.destination || '').split(',')[0];
            const name = (attraction?.name || '').toLowerCase();
            const category = (attraction?.category || '').toLowerCase();
            const desc = (attraction?.description || attraction?.summary || '').toLowerCase();
            const add = (t) => { if (t) tokens.push(t); };
            // Basic category to keyword mapping
            if (category.includes('beach')) add('beach');
            else if (category.includes('temple') || name.includes('temple')) add('temple');
            else if (category.includes('park') || name.includes('park')) add('park');
            else if (category.includes('museum') || name.includes('museum')) add('museum');
            else if (category.includes('garden') || name.includes('garden')) add('garden');
            else if (category.includes('market') || name.includes('market')) add('market');
            else if (category.includes('fort') || name.includes('fort')) add('fort');
            else if (category.includes('palace') || name.includes('palace')) add('palace');
            else if (category.includes('waterfall') || name.includes('waterfall')) add('waterfall');
            else if (category.includes('lake') || name.includes('lake')) add('lake');
            else if (category.includes('wildlife') || desc.includes('wildlife') || name.includes('zoo')) add('wildlife');
            else add('landmark');
            if (city) add(city);
            // Unsplash free source endpoint (no API key)
            const query = encodeURIComponent(tokens.join(','));
            return `https://source.unsplash.com/featured/800x600/?${query}`;
        } catch(_) {
            return '/static/placeholder.jpg';
        }
    }

    ensureAttractionStyles() {
        try {
            if (document.getElementById('injected-attraction-styles')) return;
            const style = document.createElement('style');
            style.id = 'injected-attraction-styles';
            style.textContent = `
                .attractions-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
                .attraction-card { background: rgba(255,255,255,0.06); border-radius: 12px; overflow: hidden; backdrop-filter: blur(2px); border: 1px solid rgba(255,255,255,0.08); }
                .attraction-image-container { position: relative; height: 180px; overflow: hidden; }
                .attraction-image { width: 100%; height: 100%; object-fit: cover; display: block; }
                .maps-link { position: absolute; right: 10px; bottom: 10px; background: rgba(0,0,0,0.55); color: #fff; padding: 6px 8px; border-radius: 8px; text-decoration: none; font-size: 12px; }
                .badge-most-famous { position: absolute; left: 10px; top: 10px; background: #ffd60a; color: #111; font-weight:700; padding: 4px 8px; border-radius: 999px; font-size: 12px; }
                .attraction-info { padding: 12px 14px 14px; }
                .attraction-name { margin: 0 0 6px 0; font-size: 16px; line-height: 1.3; color: #fff; }
                .attraction-description { margin: 0 0 10px 0; color: #f7f7f7; opacity: 0.9; font-size: 13px; }
                .attraction-details { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: #f1f1f1; opacity: 0.9; margin-bottom: 10px; }
                .attraction-actions { display: flex; gap: 10px; }
                .attraction-actions .poi-toggle { background: #2b6ef3; border: none; color: #fff; padding: 8px 10px; border-radius: 8px; cursor: pointer; font-size: 12px; }
                .attraction-actions .maps-btn { background: #334155; color: #fff; padding: 8px 10px; border-radius: 8px; text-decoration: none; font-size: 12px; }
            `;
            document.head.appendChild(style);
        } catch(_) {}
    }



    renderItinerary(container, itineraryData) {
        if (!itineraryData) {
            container.innerHTML = '<p>No itinerary available</p>';
            return;
        }
        const days = Array.isArray(itineraryData) ? itineraryData : this.parseItineraryText(itineraryData);
        
        const itineraryHTML = days.map((day, index) => `
            <div class="day-card">
                <div class="day-header">
                    <div class="day-number">${index + 1}</div>
                    <span>Day ${index + 1}</span>
                    <button class="add-plan-btn" data-day="${index + 1}" style="margin-left: auto; background: #007bff; color: white; border: none; padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                        <i class="fas fa-plus"></i> Add Plan
                    </button>
                </div>
                <div class="day-activities">
                    ${Array.isArray(day.activities) ? day.activities.map(activity => `
                        <div class="activity-item">
                            <div class="activity-time">${activity.time || ''}</div>
                            <div class="activity-content">${this.formatItineraryContent(activity.content)}</div>
                        </div>
                    `).join('') : ['morning','afternoon','evening','dinner','accommodation'].map(slot => `
                        <div class="activity-item">
                            <div class="activity-time">${slot}</div>
                            <div class="activity-content">${this.formatItinerarySlot(day, slot)}</div>
                        </div>`).join('')}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = itineraryHTML;
    }



    addNewPlanForDay(dayNumber) {
        // Create a new plan based on the current plan but for the specific day
        if (!this.currentPlan) {
            this.showToast('No current plan to base new plan on', 'error');
            return;
        }

        // Get the existing day's activities
        const existingDay = this.currentPlan.itinerary ? this.currentPlan.itinerary[dayNumber - 1] : null;
        
        // Helper function to extract text from activity objects
        const extractActivityText = (activity) => {
            if (typeof activity === 'string') return activity;
            if (!activity || typeof activity !== 'object') return `Day ${dayNumber} activity`;
            
            // Try to find text in various possible locations
            const possibleTextFields = [
                'suggestion', 'activity', 'name', 'title', 'description', 
                'content', 'restaurant', 'restaurant_name', 'text', 'value'
            ];
            
            for (const field of possibleTextFields) {
                if (activity[field] && typeof activity[field] === 'string') {
                    return activity[field];
                }
            }
            
            // If it's an array, try the first item
            if (Array.isArray(activity) && activity.length > 0) {
                return extractActivityText(activity[0]);
            }
            
            // If it's an object with nested properties, try to find any string
            for (const key in activity) {
                if (typeof activity[key] === 'string' && activity[key].trim()) {
                    return activity[key];
                }
                if (typeof activity[key] === 'object' && activity[key] !== null) {
                    const nestedText = extractActivityText(activity[key]);
                    if (nestedText && nestedText !== `Day ${dayNumber} activity`) {
                        return nestedText;
                    }
                }
            }
            
            return `Day ${dayNumber} activity`;
        };
        
        const newPlan = {
            destination: this.currentPlan.destination,
            start_date: this.currentPlan.start_date,
            days: 1, // Single day plan
            mood: this.currentPlan.mood,
            country: this.currentPlan.country,
            state: this.currentPlan.state,
            city: this.currentPlan.city,
            itinerary: [{
                day: dayNumber,
                morning: extractActivityText(existingDay?.morning) || `Day ${dayNumber} morning activity`,
                afternoon: extractActivityText(existingDay?.afternoon) || `Day ${dayNumber} afternoon activity`,
                evening: extractActivityText(existingDay?.evening) || `Day ${dayNumber} evening activity`,
                dinner: extractActivityText(existingDay?.dinner) || `Day ${dayNumber} dinner`,
                accommodation: extractActivityText(existingDay?.accommodation) || `Day ${dayNumber} accommodation`
            }],
            famous_places: [],
            total_budget: '₹0',
            packing_list: [],
            weather: []
        };

        // Show a modal to edit the new plan
        this.showNewPlanModal(newPlan, dayNumber);
    }

    showNewPlanModal(plan, dayNumber) {
        const modalHTML = `
            <div class="modal-overlay" id="new-plan-modal" style="background: linear-gradient(135deg, rgba(255,165,0,0.8), rgba(255,140,0,0.8)); display: flex; align-items: center; justify-content: center; position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 1000; backdrop-filter: blur(8px);">
                <div class="modal-content" style="background: linear-gradient(145deg, #ffffff, #f8f9fa); border-radius: 20px; box-shadow: 0 20px 60px rgba(255,165,0,0.3), 0 8px 25px rgba(0,0,0,0.1); max-width: 500px; width: 90%; max-height: 85vh; overflow-y: auto; border: 1px solid rgba(255,165,0,0.1);">
                    <div class="modal-header" style="padding: 25px 25px 0; border-bottom: 2px solid rgba(255,165,0,0.1); background: linear-gradient(135deg, #ff8c00, #ffa500); border-radius: 20px 20px 0 0; margin: -1px -1px 0 -1px;">
                        <h3 style="margin: 0; color: white; font-size: 20px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">Add Plan for Day ${dayNumber}</h3>
                        <button class="close-btn" onclick="this.closest('.modal-overlay').remove()" style="position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.2); border: none; font-size: 20px; cursor: pointer; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease;">&times;</button>
                    </div>
                    <div class="modal-body" style="padding: 20px;">
                        <div style="background: linear-gradient(135deg, #fff3e0, #ffe0b2); border: 2px solid #ffb74d; border-radius: 15px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(255,183,77,0.2);">
                            <h4 style="margin: 0 0 15px 0; color: #e65100; font-size: 16px; font-weight: 700; text-align: center; text-transform: uppercase; letter-spacing: 1px;">🤖 AI Generated Plan Details</h4>
                            <div style="font-size: 13px; line-height: 1.4;">
                                <div style="margin-bottom: 8px;"><strong>Destination:</strong> ${this.currentPlan?.destination || 'N/A'}</div>
                                <div style="margin-bottom: 8px;"><strong>Duration:</strong> ${this.currentPlan?.days || 'N/A'} days</div>
                                <div style="margin-bottom: 8px;"><strong>Mood:</strong> ${this.currentPlan?.mood || 'N/A'}</div>
                                <div style="margin-bottom: 8px;"><strong>Budget:</strong> ${this.currentPlan?.total_budget || 'N/A'}</div>
                                <div style="margin-bottom: 8px;"><strong>Location:</strong> ${[this.currentPlan?.city, this.currentPlan?.state, this.currentPlan?.country].filter(Boolean).join(', ') || 'N/A'}</div>
                                ${this.currentPlan?.famous_places && this.currentPlan.famous_places.length > 0 ? `<div style="margin-bottom: 8px;"><strong>Famous Places:</strong> ${this.currentPlan.famous_places.slice(0, 3).map(place => typeof place === 'string' ? place : place.name || place.title || place.description || 'Unknown place').join(', ')}${this.currentPlan.famous_places.length > 3 ? '...' : ''}</div>` : ''}
                                ${this.currentPlan?.packing_list && this.currentPlan.packing_list.length > 0 ? `<div style="margin-bottom: 8px;"><strong>Packing Items:</strong> ${this.currentPlan.packing_list.slice(0, 3).map(item => typeof item === 'string' ? item : item.name || item.title || item.description || 'Unknown item').join(', ')}${this.currentPlan.packing_list.length > 3 ? '...' : ''}</div>` : ''}
                                ${this.currentPlan?.weather && this.currentPlan.weather.length > 0 ? `<div style="margin-bottom: 8px;"><strong>Weather Info:</strong> ${this.currentPlan.weather.slice(0, 2).map(weather => typeof weather === 'string' ? weather : weather.description || weather.condition || weather.temperature || 'Unknown weather').join(', ')}${this.currentPlan.weather.length > 2 ? '...' : ''}</div>` : ''}
                            </div>
                        </div>
                        <form id="new-plan-form">
                            <div style="margin-bottom: 20px;">
                                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">🏖️ Destination</label>
                                <input type="text" id="new-destination" value="${plan.destination || ''}" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);" />
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">📅 Start Date</label>
                                    <input type="date" id="new-start-date" value="${plan.start_date || ''}" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);" />
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">😊 Mood</label>
                                    <select id="new-mood" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);">
                                        <option value="relaxing" ${plan.mood === 'relaxing' ? 'selected' : ''}>Relaxing</option>
                                        <option value="adventurous" ${plan.mood === 'adventurous' ? 'selected' : ''}>Adventurous</option>
                                        <option value="foodie" ${plan.mood === 'foodie' ? 'selected' : ''}>Foodie</option>
                                        <option value="romantic" ${plan.mood === 'romantic' ? 'selected' : ''}>Romantic</option>
                                        <option value="family" ${plan.mood === 'family' ? 'selected' : ''}>Family</option>
                                    </select>
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                                <div>
                                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">🌍 Country</label>
                                    <input type="text" id="new-country" value="${plan.country || ''}" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);" />
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">🗺️ State</label>
                                    <input type="text" id="new-state" value="${plan.state || ''}" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);" />
                                </div>
                            </div>
                            <div style="margin-bottom: 25px;">
                                <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #e65100; font-size: 14px;">🏙️ City</label>
                                <input type="text" id="new-city" value="${plan.city || ''}" style="width: 100%; padding: 12px 16px; border: 2px solid #ffb74d; border-radius: 12px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(255,183,77,0.1);" />
                            </div>
                            <div style="border-top: 3px solid #ffb74d; padding-top: 20px; background: linear-gradient(135deg, #fff8e1, #fff3e0); border-radius: 15px; padding: 20px; margin-top: 20px;">
                                <h4 style="margin: 0 0 20px 0; color: #e65100; font-size: 18px; font-weight: 700; text-align: center; text-transform: uppercase; letter-spacing: 1px;">🎯 Day Activities</h4>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; font-size: 14px; color: #e65100; font-weight: 600;">🌅 Morning</label>
                                        <input type="text" id="new-morning" value="${plan.itinerary[0].morning || ''}" style="width: 100%; padding: 10px 12px; border: 2px solid #ffb74d; border-radius: 10px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 6px rgba(255,183,77,0.1);" />
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; font-size: 14px; color: #e65100; font-weight: 600;">☀️ Afternoon</label>
                                        <input type="text" id="new-afternoon" value="${plan.itinerary[0].afternoon || ''}" style="width: 100%; padding: 10px 12px; border: 2px solid #ffb74d; border-radius: 10px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 6px rgba(255,183,77,0.1);" />
                                    </div>
                                </div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; font-size: 14px; color: #e65100; font-weight: 600;">🌆 Evening</label>
                                        <input type="text" id="new-evening" value="${plan.itinerary[0].evening || ''}" style="width: 100%; padding: 10px 12px; border: 2px solid #ffb74d; border-radius: 10px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 6px rgba(255,183,77,0.1);" />
                                    </div>
                                    <div>
                                        <label style="display: block; margin-bottom: 6px; font-size: 14px; color: #e65100; font-weight: 600;">🍽️ Dinner</label>
                                        <input type="text" id="new-dinner" value="${plan.itinerary[0].dinner || ''}" style="width: 100%; padding: 10px 12px; border: 2px solid #ffb74d; border-radius: 10px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 6px rgba(255,183,77,0.1);" />
                                    </div>
                                </div>
                                <div>
                                    <label style="display: block; margin-bottom: 6px; font-size: 14px; color: #e65100; font-weight: 600;">🏨 Accommodation</label>
                                    <input type="text" id="new-accommodation" value="${plan.itinerary[0].accommodation || ''}" style="width: 100%; padding: 10px 12px; border: 2px solid #ffb74d; border-radius: 10px; font-size: 14px; background: #fff; transition: all 0.3s ease; box-shadow: 0 2px 6px rgba(255,183,77,0.1);" />
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer" style="padding: 20px 25px 25px; border-top: 2px solid rgba(255,165,0,0.1); display: flex; gap: 15px; justify-content: flex-end; background: linear-gradient(135deg, #fff8e1, #fff3e0); border-radius: 0 0 20px 20px; margin: 0 -1px -1px -1px;">
                        <button onclick="this.closest('.modal-overlay').remove()" style="padding: 12px 24px; border: 2px solid #ffb74d; background: #fff; color: #e65100; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(255,183,77,0.2);">❌ Cancel</button>
                        <button id="save-new-plan-btn" style="padding: 12px 24px; border: none; background: linear-gradient(135deg, #ff8c00, #ffa500); color: white; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s ease; box-shadow: 0 4px 12px rgba(255,140,0,0.3);">💾 Save Plan</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Add event listener for save button
        const saveBtn = document.getElementById('save-new-plan-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveNewPlan());
        }
    }

    async saveNewPlan() {
        const destination = document.getElementById('new-destination').value;
        const startDate = document.getElementById('new-start-date').value;
        const mood = document.getElementById('new-mood').value;
        const country = document.getElementById('new-country').value;
        const state = document.getElementById('new-state').value;
        const city = document.getElementById('new-city').value;
        const morning = document.getElementById('new-morning').value;
        const afternoon = document.getElementById('new-afternoon').value;
        const evening = document.getElementById('new-evening').value;
        const dinner = document.getElementById('new-dinner').value;
        const accommodation = document.getElementById('new-accommodation').value;

        if (!destination || !startDate) {
            this.showToast('Please fill in destination and start date', 'error');
            return;
        }

        // Update the specific day in the current plan's itinerary
        if (this.currentPlan && this.currentPlan.itinerary) {
            // Get the day number from the modal title
            const modalTitle = document.querySelector('#new-plan-modal h3');
            const dayMatch = modalTitle?.textContent?.match(/Day (\d+)/);
            const dayNumber = dayMatch ? parseInt(dayMatch[1]) : 1;
            
            // Update the existing day's activities
            if (this.currentPlan.itinerary[dayNumber - 1]) {
                this.currentPlan.itinerary[dayNumber - 1] = {
                    day: dayNumber,
                    morning,
                    afternoon,
                    evening,
                    dinner,
                    accommodation
                };
                
                // Update the display to show the updated day
                this.displayPlan(this.currentPlan);
                
                this.showToast(`Day ${dayNumber} activities updated!`, 'success');
                document.getElementById('new-plan-modal').remove();
            } else {
                this.showToast(`Day ${dayNumber} not found in current plan`, 'error');
            }
        } else {
            this.showToast('No current plan to update', 'error');
        }
    }

    formatItineraryContent(val) {
        if (!val) return '';
        if (typeof val === 'string') return val;
        // When slot is the object itself (e.g., {suggestion: '...'} or {activity: '...'})
        if (val.suggestion && typeof val.suggestion === 'string') return val.suggestion;
        if (val.activity && typeof val.activity === 'string') return val.activity;
        if (val.activity && typeof val.activity === 'object') return this.formatItineraryContent(val.activity);
        if (val.name && typeof val.name === 'string') return val.name;
        if (val.title && typeof val.title === 'string') return val.title;
        if (val.description && typeof val.description === 'string') return val.description;
        if (val.poi && typeof val.poi === 'object' && typeof val.poi.name === 'string') return val.poi.name;
        if (typeof val.content === 'string') return val.content;
        return '';
    }

    formatItinerarySlot(day, slot) {
        try {
            const v = day?.[slot];
            // Prefer explicit string fields first
            if (slot === 'dinner') {
                if (typeof v === 'string') return v;
                if (v?.suggestion) return this.formatItineraryContent(v.suggestion);
                if (v?.restaurant || v?.restaurant_name) return v.restaurant || v.restaurant_name;
                if (v?.name) return v.name;
            } else {
                if (typeof v === 'string') return v;
                if (v?.activity) return this.formatItineraryContent(v.activity);
                if (v?.name) return v.name;
            }
            return this.formatItineraryContent(v);
        } catch (e) {
            return '';
        }
    }

    renderPackingList(container, items) {
        // Personalized greeting
        const packingGreeting = document.getElementById('packing-greeting');
        if (packingGreeting && this.currentPlan && this.currentPlan.name) {
            packingGreeting.innerHTML = `<div class="greeting-text">Hi ${this.currentPlan.name}, here is your personalized packing list ✨</div>`;
            packingGreeting.style.display = 'block';
        } else if (packingGreeting) {
            packingGreeting.style.display = 'none';
        }
        
        // Build smart list by age + gender; fall back to items
        let smart = this.generateSmartPackingList(this.currentPlan?.age, this.currentPlan?.gender);
        const ageVal = parseInt(this.currentPlan?.age, 10);
        const genderVal = (this.currentPlan?.gender || '').toString().trim().toLowerCase();
        // If user provided gender or age, force a single matching group
        if ((!!genderVal || !isNaN(ageVal)) && Array.isArray(smart) && smart.length) {
            const assumedStage = (!isNaN(ageVal) && ageVal >= 5 && ageVal <= 12) ? 'Kids'
                : (!isNaN(ageVal) && ageVal >= 55) ? 'Seniors' : 'Adults';
            const assumedGender = genderVal.startsWith('m') ? 'Men' : (genderVal ? 'Women' : null);
            const matchPrefix = assumedGender ? `${assumedStage} (` : assumedStage;
            const preferred = smart.find(s => {
                const title = (s.title || '').replace(' (Recommended)', '');
                return assumedGender
                    ? title.startsWith(`${assumedStage}`) && title.endsWith(`– ${assumedGender}`)
                    : title.startsWith(matchPrefix);
            });
            if (preferred) smart = [preferred];
        }
        if (smart && smart.length) {
            container.classList.remove('packing-pills');
            const primary = smart[0];
            const others = smart.slice(1);

            const key = this.getPackingStorageKey(primary.title);
            let checked = [];
            try { checked = JSON.parse(localStorage.getItem(key) || '[]'); } catch(_) { checked = []; }

            const primaryHTML = `
                <li style="list-style:none; margin:12px 0;">
                    <div style="font-weight:700; margin-bottom:8px; display:flex; align-items:center; gap:12px;">
                        <span>${primary.title}</span>
                        ${others.length ? '<button type="button" class="toggle-other-packing" style="border:none; background:#f1f5ff; padding:6px 10px; border-radius:8px; cursor:pointer;">Show other groups</button>' : ''}
                    </div>
                    <ul style="margin-left:12px;">
                        ${primary.items.map(it => `<li>${it}</li>`).join('')}
                    </ul>
                </li>`;

            const othersHTML = others.map(section => {
                const k = this.getPackingStorageKey(section.title);
                let chk = [];
                try { chk = JSON.parse(localStorage.getItem(k) || '[]'); } catch(_) { chk = []; }
                return `
                    <li style="list-style:none; margin:16px 0;">
                        <div style="font-weight:700; margin-bottom:6px;">${section.title}</div>
                        <ul style="margin-left:12px;">
                            ${section.items.map(it => `<li>${it}</li>`).join('')}
                        </ul>
                    </li>`;
            }).join('');

            container.innerHTML = `${primaryHTML}${others.length ? '<li id="other-packing-groups" style="list-style:none;">' + othersHTML + '</li>' : ''}`;
            return;
        }

        // Fallback: simple pills from provided items
        const list = Array.isArray(items) ? items : [];
        if (list.length === 0) {
            container.innerHTML = '<p>No packing suggestions.</p>';
            return;
        }
        container.classList.add('packing-pills');
        container.innerHTML = list.map(i => `<li class="pill">${i}</li>`).join('');
    }

    getPackingStorageKey(groupTitle) {
        const safe = (groupTitle || 'packing').replace(/[^a-z0-9]+/gi,'-').toLowerCase();
        return `packing-selected-${safe}`;
    }

    renderSavedPackingHTML(itemsOverride) {
        try {
            const items = Array.isArray(itemsOverride) ? itemsOverride : (() => {
                let smart = this.generateSmartPackingList(this.currentPlan?.age, this.currentPlan?.gender) || [];
                if (!Array.isArray(smart) || smart.length === 0) return [];
                const primary = smart[0];
                const key = this.getPackingStorageKey(primary.title);
                let checked = [];
                try { checked = JSON.parse(localStorage.getItem(key) || '[]'); } catch(_) { checked = []; }
                return checked.length ? checked : primary.items;
            })();
            if (!items || !items.length) return '<li>No packing items.</li>';
            return items.map(it => `<li>• ${it}</li>`).join('');
        } catch (e) {
            return '<li>No packing items.</li>';
        }
    }

    getSelectedPackingItems() {
        try {
            let smart = this.generateSmartPackingList(this.currentPlan?.age, this.currentPlan?.gender) || [];
            if (!Array.isArray(smart) || smart.length === 0) return [];
            const primary = smart[0];
            const key = this.getPackingStorageKey(primary.title);
            let checked = [];
            try { checked = JSON.parse(localStorage.getItem(key) || '[]'); } catch(_) { checked = []; }
            return checked.length ? checked : primary.items;
        } catch (e) {
            return [];
        }
    }

    generateSmartPackingList(age, gender) {
        try {
            const a = parseInt(age, 10);
            const g = (gender || '').toString().trim().toLowerCase();
            const isKid = !isNaN(a) && a >= 5 && a <= 12;
            const isSenior = !isNaN(a) && a >= 55;
            const isAdult = !isKid && !isSenior;

            // Build ALL sections first
            const kidsBoys = {
                title: 'Kids (5–12) – Boys',
                items: [
                    'T‑shirts (5–6)', 'Shorts (3–4)', 'Jeans/Pants (2)', 'Jacket / Hoodie',
                    'Undergarments', 'Socks (5–6 pairs)', 'Sleepwear', 'Sneakers',
                    'Slippers / Sandals', 'Cap / Hat', 'Water bottle', 'Small backpack',
                    'Favorite toy / action figure', 'Coloring book + crayons', 'Snacks',
                    'Toothbrush + kids toothpaste', 'Soap + shampoo', 'Wet wipes / Tissues',
                    'Sunscreen (kids safe)', 'Small first aid kit (band‑aids, antiseptic)'
                ]
            };
            const kidsGirls = {
                title: 'Kids (5–12) – Girls',
                items: [
                    'T‑shirts / Tops (5–6)', 'Dresses (2–3)', 'Shorts / Skirts (2–3)', 'Leggings / Jeans',
                    'Jacket / Sweater', 'Undergarments', 'Socks (5–6 pairs)', 'Sleepwear',
                    'Sneakers', 'Sandals / Flip‑flops', 'Hair accessories (clips, bands)', 'Sunglasses',
                    'Small backpack / sling bag', 'Favorite doll / toy', 'Snacks',
                    'Toothbrush + kids toothpaste', 'Soap + shampoo', 'Wet wipes / Tissues',
                    'Sunscreen (kids safe)', 'Storybook / Activity book'
                ]
            };
            const adultsMen = {
                title: 'Adults (18–40) – Men',
                items: [
                    'T‑shirts / Shirts (5–6)', 'Jeans / Trousers (2–3)', 'Shorts (2)', 'Jacket / Blazer (weather‑specific)',
                    'Undergarments', 'Socks', 'Sneakers / Casual shoes', 'Sandals / Flip‑flops', 'Sleepwear',
                    'Shaving kit / Trimmer', 'Sunglasses', 'Wallet (cash/cards/ID)', 'Power bank', 'Phone charger',
                    'Backpack / Duffel bag', 'Travel pillow', 'Headphones / Earbuds', 'Deodorant + perfume',
                    'Toothbrush + Toothpaste', 'First aid / Medicines'
                ]
            };
            const adultsWomen = {
                title: 'Adults (18–40) – Women',
                items: [
                    'Tops / T‑shirts (5–6)', 'Jeans / Skirts / Leggings (3–4)', 'Dresses (2–3, casual or party wear)', 'Jacket / Sweater',
                    'Undergarments + bras', 'Sleepwear', 'Sneakers / Flats', 'Sandals / Heels (optional)',
                    'Makeup kit (basic essentials)', 'Hairbrush + Hair ties', 'Sunglasses', 'Jewelry (minimal, safe)',
                    'Purse / Sling bag', 'Wallet (cash/cards/ID)', 'Power bank', 'Phone charger',
                    'Deodorant + perfume', 'Skincare kit (moisturizer, sunscreen)', 'Sanitary products',
                    'First aid / Medicines'
                ]
            };
            const seniorsMen = {
                title: 'Seniors (55+) – Men',
                items: [
                    'Comfortable shirts (cotton)', 'Trousers / Track pants', 'Light sweater / Jacket', 'Undergarments',
                    'Comfortable walking shoes', 'Sandals', 'Socks', 'Sleepwear', 'Cap / Hat', 'Sunglasses',
                    'Medications (with prescription)', 'First aid kit', 'Toothbrush + Toothpaste', 'Soap + shampoo',
                    'Reading glasses', 'Walking stick (if needed)', 'Travel documents (ID, insurance)', 'Water bottle',
                    'Snacks / Light dry food', 'Travel bag with wheels'
                ]
            };
            const seniorsWomen = {
                title: 'Seniors (55+) – Women',
                items: [
                    'Comfortable tops / Kurtis', 'Saree / Salwar / Dress (as preferred)', 'Sweater / Shawl',
                    'Comfortable pants / leggings', 'Undergarments', 'Sleepwear', 'Comfortable walking shoes',
                    'Sandals', 'Socks', 'Sunglasses', 'Cap / Scarf', 'Medications (with prescription)', 'First aid kit',
                    'Toothbrush + Toothpaste', 'Soap + shampoo', 'Reading glasses', 'Travel documents (ID, insurance)',
                    'Small handbag', 'Water bottle', 'Snacks / Dry fruits'
                ]
            };

            const all = [kidsBoys, kidsGirls, adultsMen, adultsWomen, seniorsMen, seniorsWomen];

            // If no valid age/gender, return ALL lists
            if (isNaN(a) || !g) {
                return all;
            }

            // Return ALL lists but mark the recommended one first
            let recommendedIndex = 0;
            if (isKid) recommendedIndex = g.startsWith('m') ? 0 : 1;
            else if (isAdult) recommendedIndex = g.startsWith('m') ? 2 : 3;
            else if (isSenior) recommendedIndex = g.startsWith('m') ? 4 : 5;

            const rec = { ...all[recommendedIndex], title: all[recommendedIndex].title + ' (Recommended)' };
            const others = all.filter((_, idx) => idx !== recommendedIndex);
            return [rec, ...others];
        } catch (e) {
            return [];
        }
    }



    parseItineraryText(text) {
        // Simple parsing of itinerary text - this can be enhanced
        const lines = text.split('\n').filter(line => line.trim());
        const days = [];
        let currentDay = { activities: [] };
        
        lines.forEach(line => {
            if (line.toLowerCase().includes('day') && (line.includes('1') || line.includes('2') || line.includes('3'))) {
                if (currentDay.activities.length > 0) {
                    days.push(currentDay);
                }
                currentDay = { activities: [] };
            } else if (line.trim()) {
                // Try to extract time and content
                const timeMatch = line.match(/(morning|afternoon|evening|dinner|breakfast|lunch)/i);
                const time = timeMatch ? timeMatch[1].toLowerCase() : 'activity';
                const content = line.replace(/(morning|afternoon|evening|dinner|breakfast|lunch):/i, '').trim();
                
                if (content) {
                    currentDay.activities.push({ time, content });
                }
            }
        });
        
        if (currentDay.activities.length > 0) {
            days.push(currentDay);
        }
        
        return days.length > 0 ? days : [{ activities: [{ time: 'full day', content: text }] }];
    }

    initializeMap(container, places) {
        // Clear existing map
        if (this.map) {
            this.map.remove();
        }
        
        this.markers = [];
        
        // Create map with lighter options for faster startup
        this.map = L.map(container, { preferCanvas: true, zoomControl: true, inertia: false }).setView([0, 0], 10);
        
        // Add OpenStreetMap tiles (keep default, quick to render)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            crossOrigin: true
        }).addTo(this.map);
        
        const bounds = L.latLngBounds();
        
        // Add place markers
        if (places && Array.isArray(places)) {
            places.forEach(place => {
                if (place.lat && place.lon) {
                    const marker = L.marker([place.lat, place.lon], {
                        icon: L.divIcon({
                            className: 'custom-marker poi-marker',
                            html: '<i class="fas fa-landmark"></i>',
                            iconSize: [30, 30]
                        })
                    }).addTo(this.map);
                    
                    marker.bindPopup(`
                        <div class="map-popup">
                            <h5>${place.name}</h5>
                            <p>${place.description || place.summary || ''}</p>
                        </div>
                    `);
                    
                    this.markers.push(marker);
                    bounds.extend([place.lat, place.lon]);
                }
            });
        }
        
        // Fit map to bounds if we have markers
        if (bounds.isValid()) {
            this.map.fitBounds(bounds, { padding: [20, 20] });
            // Re-render attractions to respect new center
            this.rerenderAttractionsForMapCenter();
        } else {
            // Immediate quick guess center to avoid perceived wait
            this.centerQuickGuess(this.currentPlan || {});
            this.rerenderAttractionsForMapCenter();

            // Fallbacks in parallel: 1) try our own places API (usually fast) 2) geocode the text
            const runFallbacks = async () => {
                const loc = this.currentPlan || {};
                const parts = [loc.city, loc.state, loc.country].filter(Boolean).join(', ');

                const tasks = [];
                // Try server places for coordinates based on city
                if (loc.city || loc.destination) {
                    tasks.push((async () => {
                        try {
                            const city = loc.city || (loc.destination || '').split(',')[0];
                            if (!city) return null;
                            const list = await this.fetchPlaces(city, 1, []);
                            const withCoords = (list || []).filter(p => p.lat && p.lon);
                            if (withCoords.length) {
                                const p = withCoords[0];
                                return { lat: p.lat, lon: p.lon, label: p.name };
                            }
                            return null;
                        } catch(_) { return null; }
                    })());
                }
                // Try cache immediately
                if (parts) {
                    const cached = this.getCachedGeocode(parts);
                    if (cached) {
                        this.centerWithMarker(cached, loc, parts);
                        // also refresh silently
                        this.getLatLonForLocation(parts, true).catch(()=>{});
                        return; // already centered
                    }
                    // else enqueue geocode with short timeout
                    tasks.push((async () => {
                        const g = await this.getLatLonForLocation(parts);
                        if (!g) return null;
                        return { lat: g.lat, lon: g.lon, label: g.display_name };
                    })());
                }

                // Whichever finishes first and returns a result wins
                try {
                    const results = await Promise.allSettled(tasks);
                    const firstOk = results.map(r => r.status === 'fulfilled' ? r.value : null).find(v => v && typeof v.lat === 'number');
                    if (firstOk) {
                        this.centerWithMarker({ lat: firstOk.lat, lon: firstOk.lon, display_name: firstOk.label }, loc, parts);
                        // Re-render attractions when center finally known
                        this.rerenderAttractionsForMapCenter();
                    }
                } catch(_) {}
            };
            runFallbacks();
        }
    }

    centerQuickGuess(loc) {
        try {
            const country = (loc.country || loc.destination || '').toString().toLowerCase();
            const guesses = {
                'india': [22.9734, 78.6569],
                'united states': [39.8283, -98.5795],
                'usa': [39.8283, -98.5795],
                'canada': [56.1304, -106.3468],
                'united kingdom': [54.0, -2.0],
                'uk': [54.0, -2.0],
                'australia': [-25.2744, 133.7751],
                'germany': [51.1657, 10.4515],
                'france': [46.2276, 2.2137],
                'italy': [41.8719, 12.5674],
                'spain': [40.4637, -3.7492],
                'brazil': [-14.2350, -51.9253],
                'japan': [36.2048, 138.2529]
            };
            const match = Object.keys(guesses).find(k => country.includes(k));
            if (match) {
                this.map.setView(guesses[match], 4);
            } else {
                // world view fallback
                this.map.setView([20, 0], 2);
            }
        } catch(_) {
            this.map.setView([20, 0], 2);
        }
    }

    centerWithMarker(result, loc, fallbackLabel) {
        try {
            const { lat, lon, display_name } = result;
            const center = [lat, lon];
            const marker = L.marker(center, {
                icon: L.divIcon({
                    className: 'custom-marker location-marker',
                    html: '<i class="fas fa-map-marker-alt"></i>',
                    iconSize: [30, 30]
                })
            }).addTo(this.map);
            marker.bindPopup(`
                <div class="map-popup">
                    <h5>${loc?.destination || loc?.city || 'Selected Location'}</h5>
                    <p>${display_name || fallbackLabel || ''}</p>
                </div>
            `);
            this.map.setView(center, 12);
        } catch (_) {}
    }

    getCachedGeocode(query) {
        try {
            const key = `geo-cache:${query.toLowerCase()}`;
            const raw = localStorage.getItem(key);
            if (!raw) return null;
            const { lat, lon, display_name, ts } = JSON.parse(raw);
            // 7-day TTL
            if (!ts || (Date.now() - ts) > 7*24*60*60*1000) return null;
            if (typeof lat !== 'number' || typeof lon !== 'number') return null;
            return { lat, lon, display_name };
        } catch (_) { return null; }
    }

    async getLatLonForLocation(query, silentRefresh = false) {
        try {
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 1500); // hard timeout to avoid long waits
            const res = await fetch(url, {
                headers: { 'Accept': 'application/json', 'User-Agent': 'ai-travel-planner/1.0' },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (!res.ok) return null;
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) return null;
            const first = data[0];
            const lat = parseFloat(first.lat);
            const lon = parseFloat(first.lon);
            if (isNaN(lat) || isNaN(lon)) return null;
            const result = { lat, lon, display_name: first.display_name };
            // cache
            try {
                const key = `geo-cache:${query.toLowerCase()}`;
                localStorage.setItem(key, JSON.stringify({ ...result, ts: Date.now() }));
            } catch(_){}
            return result;
        } catch (e) {
            if (!silentRefresh && (e.name !== 'AbortError')) {
                console.warn('Geocoding failed:', e);
            }
            return null;
        }
    }

    togglePOISelection(button) {
        const poiId = button.dataset.poiId;
        const poiName = button.dataset.name || '';
        const poiCategory = button.dataset.category || '';
        const poiEntry = button.dataset.entry_fee || '';
        const icon = button.querySelector('i');
        
        if (this.selectedPOIs.includes(poiId)) {
            this.selectedPOIs = this.selectedPOIs.filter(id => id !== poiId);
            this.selectedPOIDetails = this.selectedPOIDetails.filter(p => p.id !== poiId);
            icon.className = 'fas fa-plus';
            button.textContent = ' Add to Plan';
        } else {
            this.selectedPOIs.push(poiId);
            this.selectedPOIDetails.push({ id: poiId, name: poiName, category: poiCategory, entry_fee: poiEntry });
            icon.className = 'fas fa-check';
            button.textContent = ' Added to Plan';
            // Nudge plan by interest and budget when user adds a must-visit
            const interestHints = [];
            if (poiCategory) interestHints.push(poiCategory);
            if (poiName && poiName.toLowerCase().includes('temple')) interestHints.push('history');
            if (poiName && poiName.toLowerCase().includes('beach')) interestHints.push('nature');
            if (poiName && poiName.toLowerCase().includes('market')) interestHints.push('shopping');
            const merged = Array.from(new Set([...(this.currentPlan?.interests || []), ...interestHints]));
            this.currentPlan = this.currentPlan || {};
            this.currentPlan.interests = merged;
            const feeVal = poiEntry ? parseInt((poiEntry || '').replace(/[^0-9]/g,'')) : 0;
            if (feeVal && this.currentPlan.budget_breakdown) {
                this.currentPlan.budget_breakdown.activities += feeVal;
                this.currentPlan.budget_breakdown.total += feeVal;
                this.currentPlan.total_budget = `₹${this.currentPlan.budget_breakdown.total.toLocaleString('en-IN')}`;
            }
            // Debounced auto-regeneration for uniqueness
            clearTimeout(this.regenTimer);
            this.regenTimer = setTimeout(() => this.regenerateWithSelections(), 600);
        }
    }

    async regenerateWithSelections() {
        try {
            if (!this.currentPlan) return;
            const city = this.currentPlan.city || this.currentPlan.destination;
            if (!city) return;
            const days = this.currentPlan.days || 3;
            const mood = this.currentPlan.mood || 'relaxing';
            const mergedInterests = Array.from(new Set([...(this.currentPlan.interests || [])]));
            const poisForAI = (this.selectedPOIDetails && this.selectedPOIDetails.length)
                ? this.selectedPOIDetails.map(p => ({ name: p.name, category: p.category, entry_fee: p.entry_fee }))
                : (this.currentPlan.famous_places || this.currentPlan.places || []);

            const response = await fetch('/api/itinerary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    city,
                    start_date: this.currentPlan.start_date,
                    days,
                    mood,
                    interests: mergedInterests,
                    pois: poisForAI,
                    name: this.currentPlan.name || 'Anonymous',
                    age: this.currentPlan.age || '',
                    gender: this.currentPlan.gender || ''
                })
            });
            if (!response.ok) return;
            const itinerary = await response.json();
            this.displayPlan({
                destination: city,
                start_date: this.currentPlan.start_date,
                days,
                mood,
                places: poisForAI,
                itinerary: itinerary.itinerary,
                famous_places: itinerary.famous_places,
                total_budget: itinerary.total_budget_inr,
                budget_breakdown: itinerary.budget_breakdown,
                packing_list: itinerary.packing_list,
                weather: itinerary.itinerary?.map(d => ({ day: `Day ${d.day}`, temperature: `${d.weather?.high || ''}/${d.weather?.low || ''}`, forecast: d.weather?.summary || '' })) || [],
                country: this.currentPlan.country,
                state: this.currentPlan.state,
                city: this.currentPlan.city,
                name: this.currentPlan.name,
                age: this.currentPlan.age,
                gender: this.currentPlan.gender,
                interests: mergedInterests
            });
        } catch (e) {
            console.error('Auto-regeneration failed:', e);
        }
    }



    async saveCurrentPlan() {
        if (!this.currentPlan) {
            this.showToast('No plan to save', 'error');
            return;
        }

        try {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    destination: this.currentPlan.destination,
                    country: this.currentPlan.country,
                    state: this.currentPlan.state,
                    start_date: this.currentPlan.start_date,
                    days: this.currentPlan.days,
                    mood: this.currentPlan.mood,
                    budget_range_inr: undefined,
                    interests: this.currentPlan.interests || [],
                    pois: this.currentPlan.famous_places || this.currentPlan.places,
                    itinerary: this.currentPlan.itinerary,
                    packing_list: this.getSelectedPackingItems(),
                    weather: this.currentPlan.weather,
                    map_data: { center: null, zoom: null },
                    total_budget_inr: this.currentPlan.total_budget,
                    name: this.currentPlan.name || (document.getElementById('user_name')?.value || ''),
                    age: this.currentPlan.age || (document.getElementById('user_age')?.value || ''),
                    gender: this.currentPlan.gender || (document.getElementById('user_gender')?.value || '')
                })
            });

            if (response.status === 401) {
                // User not authenticated
                this.showToast('Please login to save plans', 'error');
                this.showLoginSection();
                return;
            }
            
            if (response.status === 403) {
                // Access denied
                this.showToast('Access denied', 'error');
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to save plan`);
            }

            const data = await response.json();
            
            // Update current plan with the saved plan ID
            this.currentPlan.unique_id = data.unique_id;
            
            this.showToast('Plan saved successfully! You can now share it with others.', 'success');
            
            // Show saved plan details
            this.showSavedPlanDetails(data);
            
            // Reload saved plans list
            this.loadSavedPlans();

        } catch (error) {
            console.error('Error saving plan:', error);
            this.showToast('Error saving plan', 'error');
        }
    }

    calculateEndDate(startDate, days) {
        if (!startDate || !days) return 'N/A';
        const start = new Date(startDate);
        const end = new Date(start);
        end.setDate(start.getDate() + parseInt(days) - 1);
        return end.toLocaleDateString();
    }

    showSavedPlanDetails(savedPlan) {
        // Create a comprehensive saved plan details container
        const planSection = document.getElementById('current-plan-section');
        
        // Create a new saved plan details container
        const savedPlanContainer = document.createElement('div');
        savedPlanContainer.className = 'saved-plan-details-container';
        savedPlanContainer.innerHTML = `
            <div class="saved-plan-header">
                <div class="saved-plan-badge">
                    <i class="fas fa-check-circle"></i> Plan Saved Successfully!
                </div>
                <h3><i class="fas fa-user"></i> Created by: ${savedPlan.name || 'Anonymous'}</h3>
            </div>
            
            <div class="saved-plan-summary">
                <div class="summary-grid">
                    <div class="summary-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span><strong>Destination:</strong> ${this.currentPlan.destination}</span>
                    </div>
                    <div class="summary-item">
                        <i class="fas fa-calendar"></i>
                        <span><strong>Duration:</strong> ${this.currentPlan.days} days</span>
                    </div>
                    <div class="summary-item">
                        <i class="fas fa-heart"></i>
                        <span><strong>Mood:</strong> ${this.currentPlan.mood}</span>
                    </div>
                    <div class="summary-item">
                        <i class="fas fa-wallet"></i>
                        <span><strong>Budget:</strong> ${this.currentPlan.total_budget || 'N/A'}</span>
                    </div>
                    <div class="summary-item">
                        <i class="fas fa-calendar-day"></i>
                        <span><strong>Start Date:</strong> ${this.currentPlan.start_date}</span>
                    </div>
                    <div class="summary-item">
                        <i class="fas fa-clock"></i>
                        <span><strong>Created:</strong> ${new Date().toLocaleString()}</span>
                    </div>
                </div>
            </div>
            
            <div class="saved-plan-actions">
                    <h4><i class="fas fa-copy"></i> Copy Your Plan</h4>
                    <div class="share-options">
                    <button class="share-btn copy-share" onclick="travelPlanner.copyPlan('${savedPlan.id}')">
                            <i class="fas fa-copy"></i> Copy Details
                        </button>
                    </div>
                    <div class="plan-link">
                    <small>Direct link: <a href="${window.location.origin}/plan/${savedPlan.id}" target="_blank">${window.location.origin}/plan/${savedPlan.id}</a></small>
                </div>
            </div>
            
            <div class="saved-plan-full-details">
                <h4><i class="fas fa-info-circle"></i> Complete Plan Details</h4>
                <div class="details-grid">
                    <div class="detail-section">
                        <h5><i class="fas fa-user-circle"></i> Creator Information</h5>
                        <p><strong>Name:</strong> ${savedPlan.name || 'Anonymous'}</p>
                        <p><strong>Age:</strong> ${this.currentPlan.age || 'N/A'}</p>
                        <p><strong>Gender:</strong> ${this.currentPlan.gender || 'N/A'}</p>
                    </div>
                    <div class="detail-section">
                        <h5><i class="fas fa-map"></i> Location Details</h5>
                        <p><strong>Country:</strong> ${this.currentPlan.country || 'N/A'}</p>
                        <p><strong>State:</strong> ${this.currentPlan.state || 'N/A'}</p>
                        <p><strong>City:</strong> ${this.currentPlan.destination}</p>
                    </div>
                    <div class="detail-section">
                        <h5><i class="fas fa-tags"></i> Trip Preferences</h5>
                        <p><strong>Interests:</strong> ${(this.currentPlan.interests || []).join(', ') || 'N/A'}</p>
                        <p><strong>Mood:</strong> ${this.currentPlan.mood}</p>
                        <p><strong>Duration:</strong> ${this.currentPlan.days} days</p>
                    </div>
                    <div class="detail-section">
                        <h5><i class="fas fa-calendar-alt"></i> Schedule</h5>
                        <p><strong>Start Date:</strong> ${this.currentPlan.start_date}</p>
                        <p><strong>End Date:</strong> ${this.calculateEndDate(this.currentPlan.start_date, this.currentPlan.days)}</p>
                        <p><strong>Total Days:</strong> ${this.currentPlan.days}</p>
                    </div>
                    <div class="detail-section">
                        <h5><i class="fas fa-suitcase-rolling"></i> Your Smart Packing List</h5>
                        <ul class="saved-packing-list">
                            ${this.renderSavedPackingHTML(this.getSelectedPackingItems())}
                        </ul>
                    </div>
                    </div>
                </div>
            `;
            
        // Insert the saved plan details after the current plan section
        planSection.parentNode.insertBefore(savedPlanContainer, planSection.nextSibling);
        
        // Scroll to the saved plan details
        savedPlanContainer.scrollIntoView({ behavior: 'smooth' });
    }

    async loadSavedPlans() {
        try {
            const response = await fetch('/api/plans');
            
            if (response.status === 401) {
                // User not authenticated
                this.showToast('Please login to view your saved plans', 'error');
                this.showLoginSection();
                this.savedPlans = [];
                return;
            }
            
            if (response.status === 403) {
                // Access denied
                this.showToast('Access denied', 'error');
                this.savedPlans = [];
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Failed to load plans`);
            }

            const plans = await response.json();
            this.savedPlans = plans; // Store plans in memory
            this.renderSavedPlans(plans);

        } catch (error) {
            console.error('Error loading saved plans:', error);
            this.savedPlans = []; // Initialize as empty array if failed
            this.showToast('Error loading saved plans', 'error');
        }
    }

    getSavedPlans() {
        // Return saved plans from memory, or empty array if not loaded
        return this.savedPlans || [];
    }

    renderSavedPlans(plans) {
        const container = document.getElementById('saved-plans-list');
        
        if (!plans || plans.length === 0) {
            container.innerHTML = '<p class="no-plans">No saved plans yet. Create your first plan!</p>';
            return;
        }

        const plansHTML = plans.map(plan => {
            const titleFromLocation = [plan.city, plan.state, plan.country].filter(v => v && String(v).trim()).join(', ');
            const displayDestination = titleFromLocation || plan.destination || 'Unknown Destination';
            return `
            <div class="plan-card" data-plan-id="${plan.unique_id}">
                <div class="plan-header">
                    <div class="plan-title-section">
                    <h3 class="plan-title">${displayDestination}</h3>
                        <div class="creator-info">
                            <i class="fas fa-user-circle"></i>
                            <span class="creator-name">${plan.name || 'Anonymous'}</span>
                        </div>
                    </div>
                    <div class="plan-meta">
                        <span class="plan-days">${plan.days} days</span>
                        <span class="plan-mood">${this.getMoodEmoji(plan.mood)}</span>
                        <span class="plan-date">${new Date(plan.created_at).toLocaleDateString()}</span>
                    </div>
                </div>
                <div class="plan-preview">
                    <div class="preview-grid">
                        <div class="preview-item">
                            <i class="fas fa-wallet"></i>
                            <span><strong>Budget:</strong> ${plan.total_budget_inr || 'N/A'}</span>
                        </div>
                        <div class="preview-item">
                            <i class="fas fa-map-marker-alt"></i>
                            <span><strong>Location:</strong> ${plan.city ? `${plan.city}, ` : ''}${plan.state ? `${plan.state}, ` : ''}${plan.country || 'N/A'}</span>
                        </div>
                        <div class="preview-item">
                            <i class="fas fa-heart"></i>
                            <span><strong>Mood:</strong> ${plan.mood}</span>
                        </div>
                        <div class="preview-item">
                            <i class="fas fa-calendar"></i>
                            <span><strong>Created:</strong> ${new Date(plan.created_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                </div>
                <div class="plan-actions">
                    <button class="action-btn view-btn primary-btn" data-plan-id="${plan.unique_id}" title="View Full Plan">
                        <i class="fas fa-eye"></i> View Plan
                    </button>
                    <button class="action-btn modify-btn primary-btn" data-plan-id="${plan.unique_id}" title="Modify Plan">
                        <i class="fas fa-edit"></i> Modify
                    </button>
                    <button class="action-btn copy-btn" onclick="travelPlanner.copyPlan('${plan.unique_id}')" title="Copy Plan Details">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    <button class="action-btn share-btn" onclick="travelPlanner.sharePlan('${plan.unique_id}')" title="Share Plan">
                        <i class="fas fa-share-alt"></i> Share
                    </button>
                    <button class="action-btn delete-btn" data-plan-id="${plan.unique_id}" title="Delete Plan">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `}).join('');

        container.innerHTML = plansHTML;
    }

    sanitizePlanId(planId) {
        try {
            let id = String(planId || '').trim();
            // Remove any leading ':' or '#' characters accidentally coming from links
            id = id.replace(/^[:#]+/, '');
            // Remove trailing slashes
            id = id.replace(/\/+$/, '');
            // Remove any remaining ':' characters that might be in the middle
            id = id.replace(/:/g, '');
            // Ensure it's not empty after sanitization
            if (!id) {
                throw new Error('Invalid plan ID');
            }
            return id;
        } catch (_) {
            return String(planId || '');
        }
    }

    async deletePlan(planId) {
        if (!confirm('Are you sure you want to delete this plan?')) {
            return;
        }

        planId = this.sanitizePlanId(planId);

        try {
            const response = await fetch(`/api/plans/${planId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to delete plan');
            }

            this.showToast('Plan deleted successfully', 'success');
            this.loadSavedPlans();

        } catch (error) {
            console.error('Error deleting plan:', error);
            this.showToast('Error deleting plan', 'error');
        }
    }

    async viewPlan(planId) {
        try {
            // Remove any existing saved plan details container
            const existingContainer = document.querySelector('.saved-plan-details-container');
            if (existingContainer) {
                existingContainer.remove();
            }
            // Remove previous plan overview container
            const existingOverview = document.querySelector('.plan-overview-container');
            if (existingOverview) {
                existingOverview.remove();
            }

            planId = this.sanitizePlanId(planId);

            const response = await fetch(`/api/plans/${planId}`);
            if (!response.ok) {
                throw new Error('Failed to load plan');
            }

            const plan = await response.json();
            
            // Handle missing or invalid plan data
            if (!plan || !plan.destination) {
                throw new Error('Invalid plan data');
            }
            
            const normalized = {
                destination: [plan.city, plan.state, plan.country].filter(v => v && String(v).trim()).join(', ') || plan.destination || 'Unknown Destination',
                start_date: plan.start_date || new Date().toISOString().split('T')[0],
                days: plan.days || 1,
                mood: plan.mood || 'relaxing',
                places: plan.pois || [],
                itinerary: plan.itinerary || {},
                famous_places: plan.pois || [],
                total_budget: plan.total_budget_inr || '0',
                packing_list: plan.packing_list || [],
                weather: plan.weather || [],
                interests: plan.interests || [],
                name: plan.name || 'Anonymous',
                age: plan.age || '',
                gender: plan.gender || '',
                unique_id: plan.unique_id || planId,
                country: plan.country || '',
                state: plan.state || '',
                city: plan.city || ''
            };
            
            this.currentPlan = normalized;
            this.displayPlan(normalized);

        } catch (error) {
            console.error('Error loading plan for viewing:', error);
            this.showToast('Error loading plan: ' + error.message, 'error');
        }
    }

    async modifyPlan(planId) {
        try {
            planId = this.sanitizePlanId(planId);
            const response = await fetch(`/api/plans/${planId}`);
            if (!response.ok) {
                throw new Error('Failed to load plan');
            }

            const plan = await response.json();
            
            if (!plan || !plan.destination) {
                throw new Error('Invalid plan data');
            }

            // Show modification modal
            this.showModifyModal(plan);

        } catch (error) {
            console.error('Error loading plan for modification:', error);
            this.showToast('Error loading plan: ' + error.message, 'error');
        }
    }

    showModifyModal(plan) {
        // Remove existing modal if any
        const existingModal = document.getElementById('modify-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHTML = `
            <div id="modify-modal" class="modal-overlay">
                <div class="modal-content modify-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-edit"></i> Modify Travel Plan</h3>
                        <button class="modal-close" onclick="travelPlanner.closeModifyModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form id="modify-form">
                            <div class="form-group">
                                <label for="modify-destination">Destination</label>
                                <input type="text" id="modify-destination" value="${plan.destination || ''}" required>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="modify-start-date">Start Date</label>
                                    <input type="date" id="modify-start-date" value="${plan.start_date || ''}" required>
                                </div>
                                <div class="form-group">
                                    <label for="modify-days">Duration (Days)</label>
                                    <input type="number" id="modify-days" value="${plan.days || 1}" min="1" max="30" required>
                                </div>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="modify-mood">Travel Mood</label>
                                    <select id="modify-mood" required>
                                        <option value="relaxing" ${plan.mood === 'relaxing' ? 'selected' : ''}>Relaxing</option>
                                        <option value="adventurous" ${plan.mood === 'adventurous' ? 'selected' : ''}>Adventurous</option>
                                        <option value="foodie" ${plan.mood === 'foodie' ? 'selected' : ''}>Foodie</option>
                                        <option value="romantic" ${plan.mood === 'romantic' ? 'selected' : ''}>Romantic</option>
                                        <option value="family" ${plan.mood === 'family' ? 'selected' : ''}>Family</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="modify-budget">Budget (₹)</label>
                                    <input type="number" id="modify-budget" value="${parseInt(plan.total_budget_inr || '0')}" min="1000" step="1000" required>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="modify-interests">Interests (comma-separated)</label>
                                <input type="text" id="modify-interests" value="${plan.interests || ''}" placeholder="e.g., beaches, temples, shopping, food">
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="modify-country">Country</label>
                                    <input type="text" id="modify-country" value="${plan.country || ''}">
                                </div>
                                <div class="form-group">
                                    <label for="modify-state">State</label>
                                    <input type="text" id="modify-state" value="${plan.state || ''}">
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="modify-city">City</label>
                                <input type="text" id="modify-city" value="${plan.city || ''}">
                            </div>
                            
                            <div class="modal-actions">
                                <button type="button" class="btn btn-secondary" onclick="travelPlanner.closeModifyModal()">
                                    <i class="fas fa-times"></i> Cancel
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Update Plan
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Add form submit handler
        document.getElementById('modify-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleModifySubmit(plan.unique_id);
        });

        // Show modal
        document.getElementById('modify-modal').style.display = 'flex';

        // Auto-sync destination from city/state/country while the user types
        const destInput = document.getElementById('modify-destination');
        const cityInput = document.getElementById('modify-city');
        const stateInput = document.getElementById('modify-state');
        const countryInput = document.getElementById('modify-country');
        const updateDestination = () => {
            const parts = [cityInput.value.trim(), stateInput.value.trim(), countryInput.value.trim()].filter(Boolean);
            const computed = parts.join(', ');
            if (computed) {
                destInput.value = computed;
            }
        };
        cityInput.addEventListener('input', updateDestination);
        stateInput.addEventListener('input', updateDestination);
        countryInput.addEventListener('input', updateDestination);
        // Initialize once in case destination is blank
        if (!destInput.value.trim()) updateDestination();
    }

    closeModifyModal() {
        const modal = document.getElementById('modify-modal');
        if (modal) {
            modal.remove();
        }
    }

    async handleModifySubmit(planId) {
        try {
            // Get form data
            const formData = {
                destination: document.getElementById('modify-destination').value,
                start_date: document.getElementById('modify-start-date').value,
                days: parseInt(document.getElementById('modify-days').value),
                mood: document.getElementById('modify-mood').value,
                total_budget_inr: document.getElementById('modify-budget').value,
                interests: document.getElementById('modify-interests').value,
                country: document.getElementById('modify-country').value,
                state: document.getElementById('modify-state').value,
                city: document.getElementById('modify-city').value
            };

            // If destination field is left blank, derive it from city/state/country
            const computedDestination = formData.destination && formData.destination.trim()
                ? formData.destination.trim()
                : [formData.city, formData.state, formData.country].filter(Boolean).join(', ');

            // Validate required fields
            if (!formData.destination || !formData.start_date || !formData.days) {
                this.showToast('Please fill in all required fields', 'error');
                return;
            }

            // Show loading state
            const submitBtn = document.querySelector('#modify-form button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
            submitBtn.disabled = true;

            // Update plan via API
            const response = await fetch(`/api/plans/${planId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ...formData, destination: computedDestination })
            });

            if (!response.ok) {
                throw new Error('Failed to update plan');
            }

            const result = await response.json();
            
            if (result.success) {
                this.showToast('Plan updated successfully!', 'success');
                this.closeModifyModal();
                
                // Regenerate plan based on new parameters
                await this.regeneratePlanAfterModification(planId, { ...formData, destination: computedDestination });
                
                // Reload saved plans to show updated data
                this.loadSavedPlans();
            } else {
                throw new Error(result.error || 'Update failed');
            }

        } catch (error) {
            console.error('Error updating plan:', error);
            this.showToast('Error updating plan: ' + error.message, 'error');
        } finally {
            // Reset button state
            const submitBtn = document.querySelector('#modify-form button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-save"></i> Update Plan';
                submitBtn.disabled = false;
            }
        }
    }

    async regeneratePlanAfterModification(planId, formData) {
        try {
            // Show loading message
            this.showToast('Regenerating plan with new parameters...', 'info');
            
            // Build request for existing itinerary API (uses city + days + mood)
            const planRequest = {
                city: formData.city || formData.destination,
                start_date: formData.start_date,
                days: formData.days,
                mood: formData.mood,
                name: (this.currentPlan && this.currentPlan.name) || 'Anonymous',
                age: (this.currentPlan && this.currentPlan.age) || '',
                gender: (this.currentPlan && this.currentPlan.gender) || ''
            };

            const response = await fetch('/api/itinerary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(planRequest)
            });

            if (!response.ok) throw new Error('Failed to regenerate plan');

            const ai = await response.json();
            
            // Update the plan with new generated data
            const updateResponse = await fetch(`/api/plans/${planId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    destination: formData.destination,
                    start_date: formData.start_date,
                    days: formData.days,
                    mood: formData.mood,
                    total_budget_inr: formData.total_budget_inr,
                    interests: formData.interests,
                    country: formData.country,
                    state: formData.state,
                    city: formData.city,
                    itinerary: ai.itinerary || [],
                    pois: ai.famous_places || ai.places || [],
                    packing_list: ai.packing_list || [],
                    weather: ai.weather || []
                })
            });

            if (updateResponse.ok) {
                this.showToast('Plan regenerated successfully with new parameters!', 'success');
            } else {
                throw new Error('Failed to save regenerated plan');
            }

        } catch (error) {
            console.error('Error regenerating plan:', error);
            this.showToast('Plan updated but regeneration failed: ' + error.message, 'warning');
        }
    }

    renderPlanOverviewContainer(plan) {
        try {
            const host = document.getElementById('current-plan-section');
            if (!host) return;
            const existing = document.querySelector('.plan-overview-container');
            if (existing) existing.remove();

            const container = document.createElement('div');
            container.className = 'plan-overview-container';
            const moodEmoji = this.getMoodEmoji(plan.mood);
            const dateStr = plan.start_date ? new Date(plan.start_date).toLocaleDateString() : new Date().toLocaleDateString();

            const weatherItems = Array.isArray(plan.weather) && plan.weather.length
                ? plan.weather.slice(0, Math.min(3, plan.weather.length)).map((w, i) => `
                    <div class="weather-mini">
                        <div class="weather-day">Day ${i + 1}</div>
                        <div class="weather-temp">${w.temperature || `${w.high || ''}/${w.low || ''}`}</div>
                        <div class="weather-forecast">${w.forecast || w.summary || ''}</div>
                    </div>
                  `).join('')
                : '';

            const titleFromLocation = [plan.city, plan.state, plan.country].filter(v => v && String(v).trim()).join(', ');
            const displayDestination = titleFromLocation || plan.destination || 'Unknown Destination';
            container.innerHTML = `
                <div class="overview-header">
                    <div class="greeting">👋 Hi ${plan.name || 'traveler'}, here's your Smart Travel Plan!</div>
                    <div class="summary">${displayDestination} ${plan.days} Days | ${moodEmoji} ${plan.mood} | ${dateStr}</div>
                    <div style="margin-top:8px;">
                        <button id="modify-from-view" class="btn btn-primary" style="padding:8px 12px; font-size:14px;">
                            <i class="fas fa-edit"></i> Modify Plan
                        </button>
                    </div>
                </div>
                <div class="overview-grid">
                    <div class="overview-pill"><span class="label">Destination</span><span class="value">${displayDestination}</span></div>
                    <div class="overview-pill"><span class="label">Days</span><span class="value">${plan.days}</span></div>
                    <div class="overview-pill"><span class="label">Mood</span><span class="value">${moodEmoji}</span></div>
                    <div class="overview-pill"><span class="label">Start</span><span class="value">${dateStr}</span></div>
                </div>
                ${weatherItems ? `<div class="overview-weather"><h4>Weather Forecast</h4><div class="weather-mini-wrap">${weatherItems}</div></div>` : ''}
            `;

            host.parentNode.insertBefore(container, host);

            // Hook modify button
            const btn = container.querySelector('#modify-from-view');
            if (btn && (this.currentPlan?.unique_id)) {
                btn.addEventListener('click', () => this.modifyPlan(this.currentPlan.unique_id));
            } else if (btn) {
                btn.addEventListener('click', () => this.showToast('Save the plan first to modify later', 'info'));
            }
        } catch (_) {}
    }









    async copyPlan(planId) {
        try {
            console.log('Copying plan with ID:', planId);
            planId = this.sanitizePlanId(planId);
            console.log('Sanitized plan ID:', planId);
            
            // First try to get the plan from the server
            const response = await fetch(`/api/plans/${planId}`);
            console.log('Server response status:', response.status);
            
            let plan;
            if (response.ok) {
                plan = await response.json();
                console.log('Plan loaded from server:', plan.destination);
            } else {
                console.log('Server failed, trying memory...');
                // If server fails, try to get from saved plans in memory
                const savedPlans = this.getSavedPlans();
                console.log('Saved plans in memory:', savedPlans.length);
                plan = savedPlans.find(p => p.unique_id === planId);
                
                if (!plan) {
                    console.log('Plan not in memory, trying current plan...');
                    // Last resort: try to get from current plan if it matches
                    if (this.currentPlan && this.currentPlan.unique_id === planId) {
                        plan = this.currentPlan;
                        console.log('Plan found in current plan');
                    } else {
                        throw new Error('Plan not found. Please refresh the page and try again.');
                    }
                } else {
                    console.log('Plan found in memory:', plan.destination);
                }
            }
            
            // Handle missing or invalid plan data
            if (!plan || !plan.destination) {
                throw new Error('Invalid plan data');
            }
            
            const planText = this.formatPlanForCopy(plan);
            console.log('Plan text formatted, length:', planText.length);
            
            // Try to copy to clipboard
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(planText);
                this.showToast('Plan copied to clipboard!', 'success');
                console.log('Plan copied to clipboard successfully');
            } else {
                // Fallback for older browsers or non-secure contexts
                this.fallbackCopyTextToClipboard(planText);
                console.log('Used fallback copy method');
            }

        } catch (error) {
            console.error('Error copying plan:', error);
            this.showToast('Error copying plan: ' + error.message, 'error');
        }
    }

    fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showToast('Plan copied to clipboard!', 'success');
        } catch (err) {
            console.error('Fallback copy failed:', err);
            this.showToast('Copy failed. Please select and copy manually.', 'error');
        }
        
        document.body.removeChild(textArea);
    }

    async sharePlan(planId) {
        try {
            console.log('Sharing plan with ID:', planId);
            
            // Get plan data
            let plan = null;
            try {
                const response = await fetch(`/api/plans/${planId}`);
                if (response.ok) {
                    plan = await response.json();
                }
            } catch (error) {
                console.log('Failed to fetch plan from server, trying memory...');
            }
            
            // If server fails, try to get from saved plans in memory
            if (!plan) {
                const savedPlans = this.getSavedPlans();
                console.log('Saved plans in memory:', savedPlans.length);
                plan = savedPlans.find(p => p.unique_id === planId);
            }
            
            if (!plan) {
                throw new Error('Plan not found');
            }
            
            const planUrl = `${window.location.origin}/plan/${plan.unique_id}`;
            const planText = this.formatPlanForCopy(plan);
            
            // Try to use native Web Share API if available
            if (navigator.share) {
                await navigator.share({
                    title: `AI Travel Planner - ${plan.destination || 'Travel Plan'}`,
                    text: planText,
                    url: planUrl
                });
                this.showToast('Plan shared successfully!', 'success');
            } else {
                // Fallback: copy to clipboard and show URL
                await this.copyPlan(planId);
                this.showToast(`Plan copied! Share this link: ${planUrl}`, 'info');
            }
            
        } catch (error) {
            console.error('Error sharing plan:', error);
            this.showToast('Error sharing plan: ' + error.message, 'error');
        }
    }







    formatPlanForCopy(plan) {
        let itineraryText = '';
        if (plan.itinerary && Array.isArray(plan.itinerary)) {
            itineraryText = plan.itinerary.map((day, index) => {
                let dayText = `Day ${index + 1}:\n`;
                if (day.morning) dayText += `  Morning: ${this.formatItineraryContent(day.morning)}\n`;
                if (day.afternoon) dayText += `  Afternoon: ${this.formatItineraryContent(day.afternoon)}\n`;
                if (day.evening) dayText += `  Evening: ${this.formatItineraryContent(day.evening)}\n`;
                if (day.dinner) dayText += `  Dinner: ${this.formatItineraryContent(day.dinner)}\n`;
                if (day.accommodation) dayText += `  Accommodation: ${this.formatItineraryContent(day.accommodation)}\n`;
                return dayText;
            }).join('\n');
        } else if (plan.itinerary && typeof plan.itinerary === 'object') {
            // Handle object format itinerary
            itineraryText = Object.entries(plan.itinerary).map(([key, value]) => {
                return `  ${key}: ${this.formatItineraryContent(value)}`;
            }).join('\n');
        }

        let packingText = '';
        if (plan.packing_list && Array.isArray(plan.packing_list)) {
            packingText = plan.packing_list.join(', ');
        }

        return `
🌍 AI Travel Planner - ${plan.destination || 'Travel Plan'}

📅 Duration: ${plan.days || 1} days
😊 Mood: ${plan.mood || 'Unknown'}
💰 Budget: ${plan.total_budget_inr || 'Not specified'}
👤 Created by: ${plan.name || 'Anonymous'}

🗺️ ITINERARY:
${itineraryText || 'No detailed itinerary available'}

🎒 PACKING LIST:
${packingText || 'No packing list available'}

🔗 View full plan with maps and details: ${window.location.origin}/plan/${plan.unique_id || 'unknown'}

---
Created with AI Travel Planner - Smart trip planning with AI, weather, maps, and more!
        `.trim();
    }

    formatCurrency(amount) {
        if (!amount) return 'Price not available';
        return `₹${parseInt(amount).toLocaleString('en-IN')}`;
    }

    getMoodEmoji(mood) {
        const emojis = {
            'relaxing': '😌',
            'adventurous': '🏔️',
            'foodie': '🍽️',
            'romantic': '💕',
            'family': '👨‍👩‍👧‍👦'
        };
        return emojis[mood] || '🎒';
    }

    showLoading() {
        document.getElementById('loading-section').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-section').classList.add('hidden');
    }

    resetToInput() {
        document.getElementById('current-plan-section').classList.add('hidden');
        document.getElementById('manual-form').reset();
        document.getElementById('ai-form').reset();
        this.currentPlan = null;
        this.selectedPOIs = [];
        
        // Remove any existing saved plan details container
        const existingContainer = document.querySelector('.saved-plan-details-container');
        if (existingContainer) {
            existingContainer.remove();
        }
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        const container = document.getElementById('toast-container');
        container.appendChild(toast);
        
        // Show toast
        setTimeout(() => toast.classList.add('show'), 100);
        
        // Remove toast after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => container.removeChild(toast), 300);
        }, 3000);
    }

    async loadLocations() {
        try {
            console.log('Loading locations...');
            this.updateDebugInfo('Loading locations...');
            const res = await fetch('/api/locations');
            if (!res.ok) throw new Error('Failed to load locations');
            const payload = await res.json();
            this.locations = payload.locations || payload;
            this.moodToInterests = payload.mood_to_interests || {};
            console.log('Locations loaded:', Object.keys(this.locations));
            this.updateDebugInfo(`Locations loaded: ${Object.keys(this.locations).length} countries`);
            this.populateCountries();
            // Keep placeholders; do not auto-select country/state/city
            const moodSelect = document.getElementById('mood');
            if (moodSelect && moodSelect.value) {
                this.applyMoodInterests(moodSelect.value);
            }
        } catch (e) {
            console.error('Locations load error:', e);
            this.updateDebugInfo(`Error: ${e.message}`);
        }
    }

    updateDebugInfo(message) {
        const debugEl = document.getElementById('debug-info');
        if (debugEl) {
            debugEl.innerHTML = message;
        }
    }

    populateCountries() {
        const countrySelect = document.getElementById('countrySelect');
        const aiCountrySelect = document.getElementById('ai_countrySelect');
        const countries = Object.keys(this.locations || {});
        
        console.log('Populating countries:', countries.length, 'countries found');
        console.log('Manual country select found:', !!countrySelect);
        console.log('AI country select found:', !!aiCountrySelect);
        
        this.updateDebugInfo(`Found ${countries.length} countries. Manual: ${!!countrySelect}, AI: ${!!aiCountrySelect}`);
        
        if (countrySelect) {
            countrySelect.innerHTML = ['<option value="" disabled selected>🌍 Select country</option>', ...countries.map(c => `<option value="${c}">${c}</option>`)].join('');
            console.log('Manual countries populated');
        }
        
        if (aiCountrySelect) {
            aiCountrySelect.innerHTML = ['<option value="" disabled selected>🌍 Select country</option>', ...countries.map(c => `<option value="${c}">${c}</option>`)].join('');
            console.log('AI countries populated');
            this.updateDebugInfo(`✅ AI countries populated: ${countries.length} countries`);
        } else {
            this.updateDebugInfo(`❌ AI country select not found`);
        }
    }

    populateStates(country) {
        const stateSelect = document.getElementById('stateSelect');
        const citySelect = document.getElementById('citySelect');
        if (!stateSelect || !citySelect) return;
        stateSelect.innerHTML = '<option value="" disabled selected>🏞️ Select state</option>';
        citySelect.innerHTML = '<option value="" disabled selected>🏙️ Select city</option>';
        if (!country || !(this.locations || {})[country]) return;
        const states = Object.keys(this.locations[country] || {});
        stateSelect.innerHTML = ['<option value="" disabled selected>🏞️ Select state</option>', ...states.map(s => `<option value="${s}">${s}</option>`)].join('');
    }

    populateCities(country, state) {
        const citySelect = document.getElementById('citySelect');
        if (!citySelect) return;
        citySelect.innerHTML = '<option value="" disabled selected>🏙️ Select city</option>';
        if (!country || !state) return;
        const cities = (((this.locations || {})[country] || {})[state]) || [];
        citySelect.innerHTML = ['<option value="" disabled selected>🏙️ Select city</option>', ...cities.map(c => `<option value="${c}">${c}</option>`)].join('');
    }

    populateAIStates(country) {
        const stateSelect = document.getElementById('ai_stateSelect');
        const citySelect = document.getElementById('ai_citySelect');
        if (!stateSelect || !citySelect) return;
        stateSelect.innerHTML = '<option value="" disabled selected>🏞️ Select state</option>';
        citySelect.innerHTML = '<option value="" disabled selected>🏙️ Select city</option>';
        if (!country || !(this.locations || {})[country]) return;
        const states = Object.keys(this.locations[country] || {});
        stateSelect.innerHTML = ['<option value="" disabled selected>🏞️ Select state</option>', ...states.map(s => `<option value="${s}">${s}</option>`)].join('');
    }

    populateAICities(country, state) {
        const citySelect = document.getElementById('ai_citySelect');
        if (!citySelect) return;
        citySelect.innerHTML = '<option value="" disabled selected>🏙️ Select city</option>';
        if (!country || !state) return;
        const cities = (((this.locations || {})[country] || {})[state]) || [];
        citySelect.innerHTML = ['<option value="" disabled selected>🏙️ Select city</option>', ...cities.map(c => `<option value="${c}">${c}</option>`)].join('');
    }

    applyMoodInterests(moodValue) {
        if (!this.moodToInterests) return;
        const container = document.getElementById('interests-cards');
        if (!container) return;
        // Resolve mood aliases (form values -> mapping keys)
        const alias = {
            'relaxing': 'Relaxing',
            'relax': 'Relaxing',
            'adventurous': 'Adventure',
            'adventure': 'Adventure',
            'foodie': 'Foodie',
            'romantic': 'Romantic',
            'family': 'Family',
            'office trip': 'Office Trip'
        };
        const mv = String(moodValue || '').toLowerCase();
        const aliasKey = alias[mv] || moodValue;
        // Find mapping key case-insensitively
        const moodKey = Object.keys(this.moodToInterests || {}).find(k => k.toLowerCase() === String(aliasKey || '').toLowerCase());
        const list = (moodKey && this.moodToInterests[moodKey]) ? this.moodToInterests[moodKey] : [];

        // Helpers
        const normalizeToken = (label) => {
            const s = String(label).toLowerCase();
            if (s.includes('history') || s.includes('museum') || s.includes('heritage')) return 'history';
            if (s.includes('nature') || s.includes('park') || s.includes('scenic') || s.includes('wildlife')) return 'nature';
            if (s.includes('art') || s.includes('culture')) return 'art';
            if (s.includes('food') || s.includes('dining') || s.includes('cooking') || s.includes('beverage')) return 'food';
            if (s.includes('shop')) return 'shopping';
            if (s.includes('adventure') || s.includes('trek') || s.includes('water') || s.includes('camp') || s.includes('extreme') || s.includes('caving')) return 'adventure';
            if (s.includes('family') || s.includes('amusement') || s.includes('zoo') || s.includes('aquarium')) return 'family';
            return 'nature';
        };
        const emojiFor = (label) => {
            const s = String(label).toLowerCase();
            // Specifics first
            if (s.includes('trek')) return '🥾';
            if (s.includes('water sport')) return '🌊';
            if (s.includes('camp')) return '⛺';
            if (s.includes('wildlife')) return '🐾';
            if (s.includes('extreme')) return '🧗';
            if (s.includes('caving') || s.includes('explor')) return '🧭';
            if (s.includes('street food')) return '🍢';
            if (s.includes('fine dining')) return '🍽️';
            if (s.includes('market')) return '🛍️';
            if (s.includes('cooking')) return '👨‍🍳';
            if (s.includes('beverage')) return '🍷';
            if (s.includes('beach') || s.includes('sunset')) return '🏖️';
            if (s.includes('spa') || s.includes('wellness')) return '💆';
            if (s.includes('drive')) return '🚗';
            if (s.includes('art') || s.includes('culture')) return '🎭';
            if (s.includes('amusement')) return '🎢';
            if (s.includes('family restaurant')) return '👨‍👩‍👧‍👦';
            if (s.includes('team') || s.includes('workshop') || s.includes('seminar')) return '🤝';
            if (s.includes('business')) return '🏢';
            // Fallback by broad token
            const t = normalizeToken(label);
            return t === 'food' ? '🍲' :
                   t === 'nature' ? '🌳' :
                   t === 'shopping' ? '🛍️' :
                   t === 'adventure' ? '🏔️' :
                   t === 'art' ? '🎭' :
                   t === 'family' ? '👨‍👩‍👧‍👦' :
                   '📍';
        };

        // Rebuild badges for this mood and pre-select all
        const cardsHtml = list.map(label => {
            const token = normalizeToken(label);
            return `<div class="interest-card active" data-value="${token}"><span>${emojiFor(label)}</span><span>${label}</span></div>`;
        }).join('');
        container.innerHTML = cardsHtml;

        const selected = Array.from(container.querySelectorAll('.interest-card.active')).map(c => c.dataset.value);
        const hidden = document.getElementById('interests');
        if (hidden) hidden.value = selected.join(',');
    }

    applyMoodStyling(moodValue) {
        const interestsContainer = document.getElementById('interests-cards');
        if (!interestsContainer) return;
        
        // Remove all mood-specific classes
        interestsContainer.classList.remove('romantic-mood');
        
        // Add romantic-mood class if romantic is selected
        if (moodValue === 'romantic') {
            interestsContainer.classList.add('romantic-mood');
        }
    }

    rerenderAttractionsForMapCenter() {
        try {
            const section = document.getElementById('current-plan');
            const grid = section ? section.querySelector('.attractions-grid') : null;
            if (!grid) return;
            const list = Array.isArray(this.currentPlan?.famous_places) ? this.currentPlan.famous_places : (Array.isArray(this.currentPlan?.places) ? this.currentPlan.places : []);
            if (!Array.isArray(list) || list.length === 0) return;
            this.renderAttractions(grid, list);
        } catch(_) {}
    }
}

// Initialize the app when DOM is loaded
let travelPlanner;
document.addEventListener('DOMContentLoaded', () => {
    travelPlanner = new TravelPlanner();
});

// Add custom CSS for map markers
const style = document.createElement('style');
style.textContent = `
    .custom-marker {
        background: white;
        border: 2px solid #007bff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #007bff;
        font-size: 14px;
    }
    
    .hotel-marker {
        border-color: #28a745;
        color: #28a745;
    }
    
    .map-popup {
        text-align: center;
    }
    
    .map-popup h5 {
        margin: 0 0 5px 0;
        color: #333;
    }
    
    .map-popup p {
        margin: 0;
        color: #666;
        font-size: 12px;
    }
`;
document.head.appendChild(style);
