// Use relative URL so it works with the Flask server
const API_BASE = '/api';

const api = {
    // Auth
    async signup(name, email, password, type) {
        const res = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ name, email, password, type })
        });
        return res.json();
    },

    async login(email, password, type) {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, password, type })
        });
        return res.json();
    },

    async logout() {
        const res = await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        return res.json();
    },

    async getCurrentUser() {
        const res = await fetch(`${API_BASE}/auth/me`, {
            credentials: 'include'
        });
        return res.json();
    },

    // Listings
    async getListings(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`${API_BASE}/listings?${query}`, {
            credentials: 'include'
        });
        return res.json();
    },

    async createListing(data) {
        const res = await fetch(`${API_BASE}/listings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        return res.json();
    },

    async updateListing(id, data) {
        const res = await fetch(`${API_BASE}/listings/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        return res.json();
    },

    // Supplies
    async getSupplies(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`${API_BASE}/supplies?${query}`, {
            credentials: 'include'
        });
        return res.json();
    },

    async createSupply(data) {
        const res = await fetch(`${API_BASE}/supplies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        return res.json();
    },

    // Transactions
    async getTransactions(params = {}) {
        const query = new URLSearchParams(params).toString();
        const res = await fetch(`${API_BASE}/transactions?${query}`, {
            credentials: 'include'
        });
        return res.json();
    },

    async createTransaction(data) {
        const res = await fetch(`${API_BASE}/transactions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        return res.json();
    },

    // Admin
    async getUsers() {
        const res = await fetch(`${API_BASE}/admin/users`, {
            credentials: 'include'
        });
        return res.json();
    },

    async updateUser(id, data) {
        const res = await fetch(`${API_BASE}/admin/users/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        return res.json();
    },

    async getAdminStats() {
        const res = await fetch(`${API_BASE}/admin/stats`, {
            credentials: 'include'
        });
        return res.json();
    }
};