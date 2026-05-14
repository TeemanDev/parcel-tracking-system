# app.py - Complete working version with all templates
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import sqlite3
import random
import json
import os
from functools import wraps

import os

# For Railway persistent storage
if not os.path.exists('/data'):
    os.makedirs('/data', exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Database setup
def get_db():
    # Railway uses /data for persistent storage
    db_path = '/data/parcels.db'
    # Fallback for local development
    if not os.path.exists('/data') or os.name == 'nt':  # Windows
        db_path = 'parcels.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parcels'")
    table_exists = c.fetchone()
    
    if table_exists:
        c.execute("PRAGMA table_info(parcels)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'sender_phone' not in columns:
            c.execute("ALTER TABLE parcels ADD COLUMN sender_phone TEXT DEFAULT ''")
        if 'recipient_phone' not in columns:
            c.execute("ALTER TABLE parcels ADD COLUMN recipient_phone TEXT DEFAULT ''")
        if 'weight' not in columns:
            c.execute("ALTER TABLE parcels ADD COLUMN weight REAL DEFAULT 0")
        if 'package_type' not in columns:
            c.execute("ALTER TABLE parcels ADD COLUMN package_type TEXT DEFAULT 'Standard'")
        if 'special_instructions' not in columns:
            c.execute("ALTER TABLE parcels ADD COLUMN special_instructions TEXT DEFAULT ''")
    else:
        c.execute('''CREATE TABLE parcels (
            tracking_code TEXT PRIMARY KEY,
            sender_name TEXT,
            sender_address TEXT,
            sender_phone TEXT,
            recipient_name TEXT,
            recipient_address TEXT,
            recipient_phone TEXT,
            weight REAL,
            package_type TEXT,
            status TEXT,
            current_location TEXT,
            created_at TIMESTAMP,
            last_update TIMESTAMP,
            estimated_delivery DATE,
            special_instructions TEXT
        )''')
        
        c.execute('''CREATE TABLE tracking_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT,
            status TEXT,
            location TEXT,
            description TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY (tracking_code) REFERENCES parcels(tracking_code)
        )''')
        
        c.execute('''CREATE TABLE admins (
            username TEXT PRIMARY KEY,
            password TEXT
        )''')
        
        c.execute("INSERT INTO admins (username, password) VALUES ('admin', 'admin123')")
        
        # Add a sample package for testing
        sample_code = '810123456789'
        c.execute('''INSERT INTO parcels (tracking_code, sender_name, sender_address, sender_phone, 
                     recipient_name, recipient_address, recipient_phone, weight, package_type, 
                     status, current_location, created_at, last_update, estimated_delivery, special_instructions)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (sample_code, 'John Doe', '123 Main St, New York, NY 10001', '(555) 123-4567',
                   'Jane Smith', '456 Oak Ave, Los Angeles, CA 90001', '(555) 987-6543',
                   5.5, 'Medium Box', 'transit', 'Chicago Distribution Center', 
                   datetime.now(), datetime.now(), (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'), 
                   'Handle with care'))
        
        c.execute('''INSERT INTO tracking_updates (tracking_code, status, location, description, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (sample_code, 'pending', 'New York Facility', 'Package received and processed', datetime.now()))
        
        c.execute('''INSERT INTO tracking_updates (tracking_code, status, location, description, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (sample_code, 'picked', 'New York Facility', 'Package picked up by carrier', datetime.now() - timedelta(hours=5)))
        
        c.execute('''INSERT INTO tracking_updates (tracking_code, status, location, description, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (sample_code, 'transit', 'Chicago Distribution Center', 'Package in transit', datetime.now() - timedelta(hours=2)))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized/updated successfully")

def generate_tracking_code():
    while True:
        code = '810' + ''.join(str(random.randint(0, 9)) for _ in range(9))
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT tracking_code FROM parcels WHERE tracking_code = ?", (code,))
        if not c.fetchone():
            conn.close()
            return code
        conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ HTML TEMPLATES ============

ADMIN_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - Parcel Tracking</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 350px;
        }
        h2 { text-align: center; margin-bottom: 30px; color: #333; }
        input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover { transform: translateY(-2px); }
        .error { color: red; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Admin Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
    </div>
</body>
</html>
'''

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - Parcel Tracking</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .container { max-width: 1400px; margin: 30px auto; padding: 0 20px; }
        .card { background: white; border-radius: 15px; padding: 25px; margin-bottom: 30px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); }
        h3 { margin-bottom: 20px; color: #1a1a2e; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
        input, select, textarea { width: 100%; padding: 12px; border: 2px solid #e1e5eb; border-radius: 8px; font-size: 14px; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #e1e5eb; }
        th { background: #f8f9fa; font-weight: 600; }
        .status { padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }
        .status-pending { background: #ffc107; color: #000; }
        .status-picked { background: #17a2b8; color: white; }
        .status-transit { background: #007bff; color: white; }
        .status-out_for_delivery { background: #fd7e14; color: white; }
        .status-delivered { background: #28a745; color: white; }
        .logout { background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 8px; text-decoration: none; color: white; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; }
        .modal-content { background: white; padding: 30px; border-radius: 15px; width: 500px; max-width: 90%; }
        .search-box { margin-bottom: 20px; display: flex; gap: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; text-align: center; }
        .stat-number { font-size: 32px; font-weight: bold; }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .row { grid-template-columns: 1fr; } }
        .alert-success { background: #d4edda; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center; border: 2px solid #28a745; }
        .btn-sm { padding: 5px 10px; font-size: 12px; margin: 0 2px; cursor: pointer; }
        .tracking-code-display { font-size: 32px; font-weight: bold; color: #28a745; margin: 15px 0; letter-spacing: 3px; font-family: monospace; }
        .notification { position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 15px 20px; border-radius: 8px; z-index: 2000; animation: slideIn 0.3s ease; }
        @keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-box"></i> Parcel Tracking Admin</h1>
        <a href="/admin/logout" class="logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
    <div class="container">
        <div class="stats-grid" id="stats">
            <div class="stat-card"><div class="stat-number" id="totalParcels">0</div><div class="stat-label">Total Parcels</div></div>
            <div class="stat-card"><div class="stat-number" id="deliveredParcels">0</div><div class="stat-label">Delivered</div></div>
            <div class="stat-card"><div class="stat-number" id="inTransit">0</div><div class="stat-label">In Transit</div></div>
        </div>
        <div class="row">
            <div class="card">
                <h3><i class="fas fa-plus-circle"></i> Generate New Shipment</h3>
                <form id="parcelForm">
                    <div class="form-group"><label>Sender Name:</label><input type="text" name="sender_name" required></div>
                    <div class="form-group"><label>Sender Phone:</label><input type="tel" name="sender_phone" required></div>
                    <div class="form-group"><label>Sender Address:</label><input type="text" name="sender_address" required></div>
                    <div class="form-group"><label>Recipient Name:</label><input type="text" name="recipient_name" required></div>
                    <div class="form-group"><label>Recipient Phone:</label><input type="tel" name="recipient_phone" required></div>
                    <div class="form-group"><label>Recipient Address:</label><input type="text" name="recipient_address" required></div>
                    <div class="form-group"><label>Weight (lbs):</label><input type="number" name="weight" step="0.1" required></div>
                    <div class="form-group"><label>Package Type:</label><select name="package_type" required>
                        <option value="Document">Document</option><option value="Small Box">Small Box</option>
                        <option value="Medium Box">Medium Box</option><option value="Large Box">Large Box</option>
                    </select></div>
                    <div class="form-group"><label>Estimated Delivery:</label><input type="date" name="estimated_delivery" required></div>
                    <div class="form-group"><label>Special Instructions:</label><textarea name="special_instructions" rows="2"></textarea></div>
                    <button type="submit"><i class="fas fa-qrcode"></i> Generate Tracking Code</button>
                </form>
                <div id="newCode" style="display: none;">
                    <div class="alert-success">
                        <strong>✅ New Tracking Code Generated!</strong><br>
                        <div class="tracking-code-display" id="trackingCode"></div>
                        <button onclick="copyCode()" class="btn-sm"><i class="fas fa-copy"></i> Copy Code</button>
                        <button onclick="testTrack()" class="btn-sm"><i class="fas fa-eye"></i> Track Now</button>
                    </div>
                </div>
            </div>
            <div class="card">
                <h3><i class="fas fa-search"></i> Search & Manage</h3>
                <div class="search-box"><input type="text" id="searchInput" placeholder="Search..."><button onclick="searchParcels()">Search</button></div>
                <div style="overflow-x: auto; max-height: 500px;">
                    <table class="table"><thead><tr><th>Tracking Code</th><th>Sender</th><th>Recipient</th><th>Status</th><th>Actions</th></tr></thead>
                    <tbody id="parcelsList"></tbody></table>
                </div>
            </div>
        </div>
    </div>
    <div id="updateModal" class="modal"><div class="modal-content"><h3>Update Status</h3><form id="updateForm">
        <input type="hidden" id="updateCode">
        <div class="form-group"><label>Status:</label><select id="updateStatus" required>
            <option value="pending">Pending</option><option value="picked">Picked Up</option>
            <option value="transit">In Transit</option><option value="out_for_delivery">Out for Delivery</option>
            <option value="delivered">Delivered</option></select></div>
        <div class="form-group"><label>Location:</label><input type="text" id="updateLocation" required></div>
        <div class="form-group"><label>Description:</label><textarea id="updateDescription" rows="3"></textarea></div>
        <button type="submit">Update</button><button type="button" onclick="closeModal()">Cancel</button>
    </form></div></div>
    <script>
        function loadParcels() {
            fetch('/api/parcels').then(r=>r.json()).then(data=>{
                const tbody=document.getElementById('parcelsList');
                if(data.length===0) tbody.innerHTML='在医院<td colspan="5">No parcels found</td></tr>';
                else tbody.innerHTML=data.map(p=>`<tr><td><strong>${p.tracking_code}</strong></td><td>${p.sender_name}</td><td>${p.recipient_name}</td><td><span class="status status-${p.status}">${p.status.toUpperCase()}</span></td><td><button class="btn-sm" onclick="openUpdateModal('${p.tracking_code}')">Update</button> <button class="btn-sm" onclick="window.open('/track/${p.tracking_code}','_blank')">Track</button></td></tr>`).join('');
                document.getElementById('totalParcels').textContent=data.length;
                document.getElementById('deliveredParcels').textContent=data.filter(p=>p.status==='delivered').length;
                document.getElementById('inTransit').textContent=data.filter(p=>p.status==='transit'||p.status==='out_for_delivery').length;
            });
        }
        document.getElementById('parcelForm').addEventListener('submit',async(e)=>{
            e.preventDefault(); const data={}; new FormData(e.target).forEach((v,k)=>data[k]=v);
            const res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
            const result=await res.json();
            if(result.success){
                document.getElementById('trackingCode').textContent=result.tracking_code;
                document.getElementById('newCode').style.display='block';
                e.target.reset(); loadParcels();
                setTimeout(()=>document.getElementById('newCode').style.display='none',15000);
            }else alert('Error: '+result.error);
        });
        function copyCode(){navigator.clipboard.writeText(document.getElementById('trackingCode').textContent);alert('Copied!');}
        function testTrack(){window.open('/track/'+document.getElementById('trackingCode').textContent,'_blank');}
        function openUpdateModal(code){document.getElementById('updateCode').value=code;document.getElementById('updateModal').style.display='flex';}
        function closeModal(){document.getElementById('updateModal').style.display='none';}
        document.getElementById('updateForm').addEventListener('submit',async(e)=>{
            e.preventDefault(); const data={tracking_code:document.getElementById('updateCode').value,status:document.getElementById('updateStatus').value,location:document.getElementById('updateLocation').value,description:document.getElementById('updateDescription').value};
            await fetch('/api/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
            closeModal(); loadParcels();
        });
        function searchParcels(){fetch(`/api/search?q=${encodeURIComponent(document.getElementById('searchInput').value)}`).then(r=>r.json()).then(data=>{document.getElementById('parcelsList').innerHTML=data.map(p=>`<tr><td>${p.tracking_code}</td><td>${p.sender_name}</td><td>${p.recipient_name}</td><td><span class="status status-${p.status}">${p.status}</span></td><td><button onclick="window.open('/track/${p.tracking_code}','_blank')">Track</button></td></tr>`).join('');});}
        loadParcels(); setInterval(loadParcels,10000);
    </script>
</body>
</html>
'''

# Replace just the TRACKING_TEMPLATE section in your app.py with this:

TRACKING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Track Your Parcel - Real-time Tracking</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',sans-serif;background:linear-gradient(rgba(0,0,0,0.6),rgba(0,0,0,0.6)),url('https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80');background-size:cover;background-attachment:fixed;min-height:100vh}
        .container{max-width:1200px;margin:0 auto;padding:40px 20px}
        .track-card{background:rgba(255,255,255,0.95);border-radius:20px;padding:40px;box-shadow:0 20px 60px rgba(0,0,0,0.3);margin-bottom:30px}
        h1{text-align:center;color:white;margin-bottom:30px;text-shadow:2px 2px 4px rgba(0,0,0,0.3)}
        .search-box{display:flex;gap:15px;margin-bottom:30px}
        .search-box input{flex:1;padding:15px;border:2px solid #ddd;border-radius:12px;font-size:16px}
        .search-box button{padding:15px 35px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;border-radius:12px;cursor:pointer;transition:transform 0.3s}
        .search-box button:hover{transform:translateY(-2px)}
        
        /* Progress Timeline Styles */
        .progress-container{background:white;border-radius:15px;padding:30px;margin-bottom:25px;box-shadow:0 5px 15px rgba(0,0,0,0.1)}
        .progress-title{font-size:18px;font-weight:600;margin-bottom:25px;color:#1a1a2e}
        .progress-title i{margin-right:10px;color:#667eea}
        .timeline-progress{position:relative;display:flex;justify-content:space-between;margin:40px 0 20px}
        .timeline-progress::before{content:'';position:absolute;top:30px;left:0;right:0;height:4px;background:linear-gradient(90deg,#e1e5eb,#e1e5eb);z-index:1}
        .timeline-step{position:relative;z-index:2;text-align:center;flex:1}
        .step-icon{width:60px;height:60px;background:white;border:3px solid #e1e5eb;border-radius:50%;margin:0 auto 12px;display:flex;align-items:center;justify-content:center;transition:all 0.5s ease;position:relative;z-index:2}
        .step-icon i{font-size:24px;color:#adb5bd}
        .step-label{font-size:13px;font-weight:600;color:#6c757d;margin-top:8px}
        .step-date{font-size:11px;color:#adb5bd;margin-top:4px}
        
        /* Completed step */
        .timeline-step.completed .step-icon{background:#28a745;border-color:#28a745;transform:scale(1.05)}
        .timeline-step.completed .step-icon i{color:white}
        .timeline-step.completed .step-label{color:#28a745}
        
        /* Active step */
        .timeline-step.active .step-icon{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-color:#667eea;transform:scale(1.1);box-shadow:0 0 20px rgba(102,126,234,0.5);animation:pulse 2s infinite}
        .timeline-step.active .step-icon i{color:white}
        .timeline-step.active .step-label{color:#667eea;font-weight:700}
        
        @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(102,126,234,0.4)}70%{box-shadow:0 0 0 15px rgba(102,126,234,0)}100%{box-shadow:0 0 0 0 rgba(102,126,234,0)}}
        
        /* Progress bar */
        .progress-wrapper{margin:20px 0 30px}
        .progress-bar-custom{height:10px;background:linear-gradient(90deg,#667eea,#764ba2);border-radius:5px;transition:width 0.8s ease;position:relative}
        .progress-percentage{text-align:right;font-size:14px;font-weight:600;margin-top:8px;color:#667eea}
        
        /* Location card with icon */
        .location-card{background:linear-gradient(135deg,#f8f9fa 0%,#e9ecef 100%);border-radius:15px;padding:20px;margin-bottom:20px;display:flex;align-items:center;gap:15px;border-left:4px solid #667eea}
        .location-icon{width:50px;height:50px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:50%;display:flex;align-items:center;justify-content:center}
        .location-icon i{font-size:24px;color:white}
        .location-details{flex:1}
        .location-status{font-size:18px;font-weight:700;color:#1a1a2e;margin-bottom:5px}
        .location-address{color:#6c757d;font-size:14px}
        .location-time{font-size:12px;color:#adb5bd;margin-top:5px}
        
        /* Parcel info styles */
        .parcel-info{background:#f8f9fa;padding:25px;border-radius:15px;margin-bottom:25px}
        .info-row{display:flex;padding:12px 0;border-bottom:1px solid #dee2e6}
        .info-row:last-child{border-bottom:none}
        .info-label{font-weight:700;width:180px;color:#495057}
        .info-value{flex:1;color:#212529}
        .status-badge{display:inline-block;padding:8px 20px;border-radius:25px;font-weight:700;font-size:14px}
        .status-pending{background:#ffc107;color:#000}
        .status-picked{background:#17a2b8;color:white}
        .status-transit{background:#007bff;color:white}
        .status-out_for_delivery{background:#fd7e14;color:white}
        .status-delivered{background:#28a745;color:white}
        
        /* Timeline history */
        .timeline-history{background:#f8f9fa;border-radius:15px;padding:25px;margin-top:25px}
        .history-title{font-size:16px;font-weight:600;margin-bottom:20px;color:#1a1a2e}
        .history-item{position:relative;padding-left:40px;padding-bottom:25px;border-left:2px solid #dee2e6;margin-left:20px}
        .history-item:last-child{padding-bottom:0;border-left:2px solid transparent}
        .history-dot{position:absolute;left:-9px;top:0;width:16px;height:16px;border-radius:50%;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border:3px solid white;box-shadow:0 0 0 2px #667eea}
        .history-date{font-size:12px;color:#6c757d;margin-bottom:5px}
        .history-status{font-weight:700;color:#1a1a2e;margin-bottom:5px}
        .history-location{font-size:13px;color:#6c757d;margin-bottom:3px}
        .history-desc{font-size:12px;color:#adb5bd}
        
        .loading{text-align:center;padding:40px}
        .spinner{border:4px solid #f3f3f3;border-top:4px solid #667eea;border-radius:50%;width:50px;height:50px;animation:spin 1s linear infinite;margin:0 auto}
        @keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}
        
        @media(max-width:768px){
            .info-row{flex-direction:column}
            .info-label{width:100%;margin-bottom:5px}
            .timeline-progress{flex-direction:column;gap:20px}
            .timeline-progress::before{display:none}
            .step-icon{margin:0 auto}
            .location-card{flex-direction:column;text-align:center}
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><i class="fas fa-truck-moving"></i> Real-Time Parcel Tracking</h1>
        <div class="track-card">
            <div class="search-box">
                <input type="text" id="trackingCode" placeholder="Enter 12-digit tracking code (starts with 810)" maxlength="12">
                <button onclick="trackParcel()"><i class="fas fa-search"></i> Track Package</button>
            </div>
            <div id="result"><div class="text-center"><i class="fas fa-box-open fa-3x mb-3"></i><p>Enter your tracking code above</p><small>Example: 810123456789</small></div></div>
        </div>
    </div>

    <script>
        async function trackParcel(){
            const code = document.getElementById('trackingCode').value;
            if(!code || code.length !== 12){
                alert('Please enter a valid 12-digit tracking code');
                return;
            }
            
            document.getElementById('result').innerHTML = '<div class="loading"><div class="spinner"></div><p class="mt-3">Fetching your package data...</p></div>';
            
            try{
                const res = await fetch(`/api/track/${code}`);
                const data = await res.json();
                
                if(data.error){
                    document.getElementById('result').innerHTML = `<div class="alert alert-danger">❌ ${data.error}</div>`;
                    return;
                }
                
                // Define steps in order
                const steps = [
                    {key: 'pending', label: 'ORDER RECEIVED', icon: 'fa-clipboard-list', description: 'Order confirmed and processing'},
                    {key: 'picked', label: 'PICKED UP', icon: 'fa-hand-peace', description: 'Package picked up from sender'},
                    {key: 'transit', label: 'IN TRANSIT', icon: 'fa-truck', description: 'Package on the way'},
                    {key: 'out_for_delivery', label: 'OUT FOR DELIVERY', icon: 'fa-motorcycle', description: 'Out for final delivery'},
                    {key: 'delivered', label: 'DELIVERED', icon: 'fa-check-circle', description: 'Package delivered successfully'}
                ];
                
                // Find current step index
                let currentStepIndex = steps.findIndex(s => s.key === data.status);
                if(currentStepIndex === -1) currentStepIndex = 0;
                
                // Calculate progress percentage
                const progressPercent = ((currentStepIndex + 1) / steps.length) * 100;
                
                // Generate timeline steps HTML
                let stepsHtml = '';
                steps.forEach((step, index) => {
                    let stepClass = '';
                    if(index < currentStepIndex) stepClass = 'completed';
                    if(index === currentStepIndex) stepClass = 'active';
                    
                    stepsHtml += `
                        <div class="timeline-step ${stepClass}">
                            <div class="step-icon">
                                <i class="fas ${step.icon}"></i>
                            </div>
                            <div class="step-label">${step.label}</div>
                            ${stepClass === 'active' ? '<div class="step-date">Current Status</div>' : ''}
                        </div>
                    `;
                });
                
                // Get status badge class
                let statusClass = '';
                if(data.status === 'pending') statusClass = 'status-pending';
                else if(data.status === 'picked') statusClass = 'status-picked';
                else if(data.status === 'transit') statusClass = 'status-transit';
                else if(data.status === 'out_for_delivery') statusClass = 'status-out_for_delivery';
                else if(data.status === 'delivered') statusClass = 'status-delivered';
                
                // Get status display name
                let statusDisplay = data.status.replace(/_/g, ' ').toUpperCase();
                
                // Generate location card with icon based on status
                let locationIcon = '';
                let locationStatusText = '';
                if(data.status === 'pending') {
                    locationIcon = 'fa-clock';
                    locationStatusText = 'Awaiting Pickup';
                } else if(data.status === 'picked') {
                    locationIcon = 'fa-hand-peace';
                    locationStatusText = 'Picked Up';
                } else if(data.status === 'transit') {
                    locationIcon = 'fa-truck';
                    locationStatusText = 'In Transit';
                } else if(data.status === 'out_for_delivery') {
                    locationIcon = 'fa-motorcycle';
                    locationStatusText = 'Out for Delivery';
                } else if(data.status === 'delivered') {
                    locationIcon = 'fa-check-circle';
                    locationStatusText = 'Delivered';
                }
                
                // Generate tracking history HTML
                let historyHtml = '';
                if(data.updates && data.updates.length > 0){
                    data.updates.forEach((update, idx) => {
                        let updateIcon = '';
                        if(update.status === 'pending') updateIcon = 'fa-clock';
                        else if(update.status === 'picked') updateIcon = 'fa-hand-peace';
                        else if(update.status === 'transit') updateIcon = 'fa-truck';
                        else if(update.status === 'out_for_delivery') updateIcon = 'fa-motorcycle';
                        else if(update.status === 'delivered') updateIcon = 'fa-check-circle';
                        
                        historyHtml += `
                            <div class="history-item">
                                <div class="history-dot"></div>
                                <div class="history-date"><i class="far fa-calendar-alt"></i> ${new Date(update.timestamp).toLocaleString()}</div>
                                <div class="history-status"><i class="fas ${updateIcon}"></i> ${update.status.toUpperCase().replace('_', ' ')}</div>
                                <div class="history-location"><i class="fas fa-map-marker-alt"></i> ${update.location}</div>
                                <div class="history-desc">${update.description || 'No additional information'}</div>
                            </div>
                        `;
                    });
                } else {
                    historyHtml = '<p class="text-center text-muted">No tracking updates available yet.</p>';
                }
                
                // Generate the complete HTML
                document.getElementById('result').innerHTML = `
                    <!-- Status Badge -->
                    <div class="parcel-info">
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-barcode"></i> Tracking Code:</div>
                            <div class="info-value"><strong>${data.tracking_code}</strong></div>
                        </div>
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-tag"></i> Current Status:</div>
                            <div class="info-value"><span class="status-badge ${statusClass}">${statusDisplay}</span></div>
                        </div>
                    </div>
                    
                    <!-- Progress Timeline -->
                    <div class="progress-container">
                        <div class="progress-title">
                            <i class="fas fa-chart-line"></i> Delivery Progress
                        </div>
                        <div class="timeline-progress">
                            ${stepsHtml}
                        </div>
                        <div class="progress-wrapper">
                            <div class="progress">
                                <div class="progress-bar-custom" style="width: ${progressPercent}%"></div>
                            </div>
                            <div class="progress-percentage">${Math.round(progressPercent)}% Complete</div>
                        </div>
                    </div>
                    
                    <!-- Current Location Card -->
                    <div class="location-card">
                        <div class="location-icon">
                            <i class="fas ${locationIcon}"></i>
                        </div>
                        <div class="location-details">
                            <div class="location-status">${locationStatusText}</div>
                            <div class="location-address"><i class="fas fa-location-dot"></i> ${data.current_location || 'Processing at facility'}</div>
                            <div class="location-time"><i class="far fa-clock"></i> Last updated: ${new Date().toLocaleString()}</div>
                        </div>
                    </div>
                    
                    <!-- Package Details -->
                    <div class="parcel-info">
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-weight-hanging"></i> Weight:</div>
                            <div class="info-value">${data.weight || 'N/A'} lbs</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-box"></i> Package Type:</div>
                            <div class="info-value">${data.package_type || 'Standard'}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-user"></i> Sender:</div>
                            <div class="info-value"><strong>${data.sender_name}</strong><br>${data.sender_phone || ''}<br>${data.sender_address}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-user-check"></i> Recipient:</div>
                            <div class="info-value"><strong>${data.recipient_name}</strong><br>${data.recipient_phone || ''}<br>${data.recipient_address}</div>
                        </div>
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-calendar-check"></i> Estimated Delivery:</div>
                            <div class="info-value">${data.estimated_delivery || 'Not set'}</div>
                        </div>
                        ${data.special_instructions ? `
                        <div class="info-row">
                            <div class="info-label"><i class="fas fa-comment"></i> Special Instructions:</div>
                            <div class="info-value">${data.special_instructions}</div>
                        </div>
                        ` : ''}
                    </div>
                    
                    <!-- Tracking History Timeline -->
                    <div class="timeline-history">
                        <div class="history-title">
                            <i class="fas fa-history"></i> Tracking History (${data.updates?.length || 0} updates)
                        </div>
                        ${historyHtml}
                    </div>
                `;
                
                // Scroll to result
                document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
                
            } catch(error){
                document.getElementById('result').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            }
        }
        
        // Auto-track if code in URL
        const urlCode = window.location.pathname.split('/').pop();
        if(urlCode && urlCode.length === 12 && urlCode !== 'track'){
            document.getElementById('trackingCode').value = urlCode;
            trackParcel();
        }
        
        // Enter key to search
        document.getElementById('trackingCode').addEventListener('keypress', function(e){
            if(e.key === 'Enter') trackParcel();
        });
    </script>
</body>
</html>
'''

# ============ ROUTES ============

@app.route('/')
def index():
    return render_template_string(TRACKING_TEMPLATE)

@app.route('/track/<code>')
def track_page(code):
    return render_template_string(TRACKING_TEMPLATE)

@app.route('/admin')
def admin_login():
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard'))
    return render_template_string(ADMIN_LOGIN_TEMPLATE)

@app.route('/admin', methods=['POST'])
def admin_do_login():
    username = request.form.get('username')
    password = request.form.get('password')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, password))
    if c.fetchone():
        session['logged_in'] = True
        conn.close()
        return redirect(url_for('admin_dashboard'))
    conn.close()
    return render_template_string(ADMIN_LOGIN_TEMPLATE, error='Invalid credentials')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ============ API ROUTES ============

@app.route('/api/generate', methods=['POST'])
@login_required
def generate_parcel():
    try:
        data = request.json
        tracking_code = generate_tracking_code()
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT INTO parcels (tracking_code, sender_name, sender_address, sender_phone, 
                     recipient_name, recipient_address, recipient_phone, weight, package_type, 
                     status, current_location, created_at, last_update, estimated_delivery, special_instructions)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (tracking_code, data.get('sender_name', ''), data.get('sender_address', ''), data.get('sender_phone', ''),
                   data.get('recipient_name', ''), data.get('recipient_address', ''), data.get('recipient_phone', ''),
                   float(data.get('weight', 0)), data.get('package_type', 'Standard'), 'pending', 'Sorting Facility',
                   datetime.now(), datetime.now(), data.get('estimated_delivery', ''), data.get('special_instructions', '')))
        c.execute('''INSERT INTO tracking_updates (tracking_code, status, location, description, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (tracking_code, 'pending', 'Sorting Facility', 'Shipment information received', datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'tracking_code': tracking_code})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
@login_required
def update_tracking():
    try:
        data = request.json
        conn = get_db()
        c = conn.cursor()
        c.execute('''UPDATE parcels SET status=?, current_location=?, last_update=? WHERE tracking_code=?''',
                  (data['status'], data['location'], datetime.now(), data['tracking_code']))
        c.execute('''INSERT INTO tracking_updates (tracking_code, status, location, description, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (data['tracking_code'], data['status'], data['location'], data.get('description', ''), datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/track/<code>')
def track_parcel(code):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM parcels WHERE tracking_code=?", (code,))
        parcel = c.fetchone()
        if not parcel:
            conn.close()
            return jsonify({'error': 'Tracking code not found'}), 404
        parcel_dict = dict(parcel)
        c.execute("SELECT * FROM tracking_updates WHERE tracking_code=? ORDER BY timestamp DESC", (code,))
        updates = c.fetchall()
        updates_list = [dict(update) for update in updates]
        conn.close()
        return jsonify({**parcel_dict, 'updates': updates_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/parcels')
@login_required
def get_parcels():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT tracking_code, sender_name, recipient_name, status FROM parcels ORDER BY created_at DESC")
        parcels = c.fetchall()
        conn.close()
        return jsonify([dict(p) for p in parcels])
    except Exception as e:
        return jsonify([])

@app.route('/api/search')
@login_required
def search_parcels():
    query = request.args.get('q', '')
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT tracking_code, sender_name, recipient_name, status 
                 FROM parcels WHERE tracking_code LIKE ? OR sender_name LIKE ? OR recipient_name LIKE ?
                 ORDER BY created_at DESC''', (f'%{query}%', f'%{query}%', f'%{query}%'))
    parcels = c.fetchall()
    conn.close()
    return jsonify([dict(p) for p in parcels])

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*60)
    print("📦 Parcel Tracking System - Running on Railway")
    print("="*60)
    print(f"📍 Tracking Page: http://localhost:{port}/")
    print(f"👨‍💼 Admin Dashboard: http://localhost:{port}/admin")
    print(f"🔑 Login: admin / admin123")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)