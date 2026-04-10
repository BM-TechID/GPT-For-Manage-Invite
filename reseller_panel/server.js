require('dotenv').config(); // Wajib di paling atas untuk baca .env
const express = require('express');
const fs = require('fs');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = 1004;
const DB_FILE = 'database.json';

// --- MENGAMBIL DARI FILE .env ---
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD; 
const MAIN_APP_URL = process.env.MAIN_APP_URL || 'http://web:8080/api/redeem';

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public'))); // Folder HTML

// Helper Database
function loadDb() {
    try {
        return JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
    } catch (e) {
        return { users: {}, inventory: {}, history: [] };
    }
}

function saveDb(data) {
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 4));
}

// Redirect URL utama ke reseller.html
app.get('/', (req, res) => {
    res.redirect('/reseller.html');
});

// --- API ROUTES ---

app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    const db = loadDb();

    // Cek Login Admin dari .env
    if (username === 'admin') {
        if (!ADMIN_PASSWORD) return res.json({ success: false, msg: 'Password Admin belum diset di .env!' });
        if (password === ADMIN_PASSWORD) return res.json({ success: true, role: 'admin', username: 'admin' });
        return res.json({ success: false, msg: 'Password Admin salah!' });
    }
    
    // Cek Login Reseller dari JSON
    if (db.users[username] && db.users[username].password === password) {
        if (db.users[username].status !== 'approved') return res.json({ success: false, msg: 'Akun belum di-approve Admin!' });
        return res.json({ success: true, role: db.users[username].role, username: username });
    }
    
    res.json({ success: false, msg: 'Username / Password salah!' });
});

app.post('/api/register', (req, res) => {
    const { username, password } = req.body;
    if (!username || !password) return res.json({ success: false, msg: 'Wajib diisi!' });
    
    const db = loadDb();
    if (db.users[username] || username === 'admin') return res.json({ success: false, msg: 'Username sudah dipakai!' });

    db.users[username] = { password, role: 'reseller', status: 'pending' };
    if(!db.inventory) db.inventory = {};
    db.inventory[username] = {};
    saveDb(db);
    res.json({ success: true, msg: 'Pendaftaran berhasil, tunggu approval admin.' });
});

app.post('/api/admin_action', (req, res) => {
    const { action, target, team, codes } = req.body;
    const db = loadDb();

    if (action === 'approve') {
        db.users[target].status = 'approved';
    } else if (action === 'delete') {
        delete db.users[target];
        delete db.inventory[target];
    } else if (action === 'add_stock') {
        const codeArray = codes.split('\n').map(c => c.trim()).filter(c => c);
        if (!db.inventory[target][team]) db.inventory[target][team] = [];
        db.inventory[target][team].push(...codeArray);
    }
    
    saveDb(db);
    res.json({ success: true });
});

app.get('/api/data', (req, res) => {
    res.json(loadDb());
});

app.post('/api/invite', async (req, res) => {
    const { username, email, team } = req.body;
    const db = loadDb();

    if (!db.inventory[username] || !db.inventory[username][team] || db.inventory[username][team].length === 0) {
        return res.json({ success: false, message: `Stok ${team} habis!` });
    }

    const usedCode = db.inventory[username][team].shift(); // Ambil 1 kode

    try {
        // Tembak ke aplikasi utama Python
        const response = await axios.post(MAIN_APP_URL, { email: email, code: usedCode });
        
        if (response.data.success) {
            const receiptId = `REC-${new Date().toISOString().replace(/[-:T.]/g, '').slice(0,14)}`;
            const log = { id: receiptId, reseller: username, email: email, team: team, code: usedCode, date: new Date().toLocaleString('id-ID') };
            if(!db.history) db.history = [];
            db.history.unshift(log);
            saveDb(db);
            return res.json({ success: true, message: response.data.message, receipt: log });
        } else {
            db.inventory[username][team].unshift(usedCode); // Kembalikan kode
            saveDb(db);
            return res.json({ success: false, message: response.data.message });
        }
    } catch (error) {
        db.inventory[username][team].unshift(usedCode); // Kembalikan kode
        saveDb(db);
        let errMsg = "Gagal terhubung ke server utama";
        if (error.response && error.response.data && error.response.data.message) errMsg = error.response.data.message;
        return res.json({ success: false, message: errMsg });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Node.js Reseller Panel aktif di port ${PORT}`);
});