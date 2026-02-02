from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Player, Subscription, Payment, File, AuditLog
from datetime import datetime
import os

main_bp = Blueprint('main', __name__)

# --- View Routes ---

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main_bp.route('/login', methods=['GET'])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('login.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# --- API Routes ---

@main_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'success': True, 'role': user.role})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@main_bp.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    logout_user()
    return jsonify({'success': True})

# --- Player Management ---

@main_bp.route('/api/players', methods=['GET'])
@login_required
def get_players():
    players = Player.query.all()
    return jsonify([p.to_dict() for p in players])

@main_bp.route('/api/players', methods=['POST'])
@login_required
def add_player():
    data = request.json
    new_player = Player(
        full_name=data['full_name'],
        age=data['age'],
        position=data.get('position'),
        team=data.get('team'),
        phone=data.get('phone'),
        parent_name=data.get('parent_name'),
        medical_notes=data.get('medical_notes')
    )
    db.session.add(new_player)
    
    # Log action
    log = AuditLog(user_id=current_user.id, action=f"Added player {new_player.full_name}")
    db.session.add(log)
    
    db.session.commit()
    return jsonify({'success': True, 'player': new_player.to_dict()})

@main_bp.route('/api/players/<int:id>', methods=['PUT'])
@login_required
def update_player(id):
    player = Player.query.get_or_404(id)
    data = request.json
    
    player.full_name = data.get('full_name', player.full_name)
    player.age = data.get('age', player.age)
    player.position = data.get('position', player.position)
    player.team = data.get('team', player.team)
    player.phone = data.get('phone', player.phone)
    player.parent_name = data.get('parent_name', player.parent_name)
    player.medical_notes = data.get('medical_notes', player.medical_notes)
    
    db.session.commit()
    return jsonify({'success': True, 'player': player.to_dict()})

@main_bp.route('/api/players/<int:id>', methods=['DELETE'])
@login_required
def delete_player(id):
    player = Player.query.get_or_404(id)
    db.session.delete(player)
    db.session.commit()
    return jsonify({'success': True})

# --- Subscriptions & Payments ---

@main_bp.route('/api/subscriptions', methods=['GET'])
@login_required
def get_subscriptions():
    subs = Subscription.query.all()
    # Enrich with player name
    result = []
    for sub in subs:
        data = sub.to_dict()
        data['player_name'] = sub.player.full_name
        result.append(data)
    return jsonify(result)

@main_bp.route('/api/subscriptions', methods=['POST'])
@login_required
def add_subscription():
    data = request.json
    
    # 1. Create Subscription
    new_sub = Subscription(
        player_id=data['player_id'],
        type=data.get('type', 'Custom'), # monthly, yearly, or custom note
        amount=float(data['amount']),
        start_date=datetime.fromisoformat(data['start_date']),
        end_date=datetime.fromisoformat(data['end_date']),
        status=data.get('status', 'active')
    )
    db.session.add(new_sub)
    db.session.flush() # flush to get ID
    
    # 2. Create Payment Record automatically (Assumed paid when added manually)
    import uuid
    new_payment = Payment(
        subscription_id=new_sub.id,
        paid_amount=new_sub.amount,
        payment_date=datetime.utcnow(),
        payment_method='Manual Entry',
        invoice_number=f"INV-{int(datetime.utcnow().timestamp())}-{new_sub.id}", # Simple unique invoice num
        qr_code_data="" # Generated on fly or here
    )
    # ... (previous code)
    db.session.add(new_payment)
    
    db.session.commit()
    
    # Return Subscription with Payment ID for Invoice
    sub_dict = new_sub.to_dict()
    sub_dict['last_payment_id'] = new_payment.id
    
    return jsonify({'success': True, 'subscription': sub_dict})

@main_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    player_count = Player.query.count()
    active_subs = Subscription.query.filter_by(status='active').count()
    total_revenue = db.session.query(db.func.sum(Payment.paid_amount)).scalar() or 0
    
    return jsonify({
        'player_count': player_count,
        'active_subscriptions': active_subs,
        'total_revenue': total_revenue or 0
    })

# --- Subscriptions Management ---

@main_bp.route('/api/subscriptions/<int:id>', methods=['DELETE'])
@login_required
def delete_subscription(id):
    sub = Subscription.query.get_or_404(id)
    # Delete associated payments first or handle via cascade (doing manual here for safety)
    Payment.query.filter_by(subscription_id=id).delete()
    db.session.delete(sub)
    db.session.commit()
    return jsonify({'success': True})

# --- File Management ---

@main_bp.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['file']
    player_id = request.form.get('player_id')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
        
    if file and player_id:
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        
        # Create player specific folder
        player_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], str(player_id))
        os.makedirs(player_folder, exist_ok=True)
        
        file_path = os.path.join(player_folder, filename)
        file.save(file_path)
        
        # Save to DB
        # Store relative path for portability
        rel_path = os.path.join(str(player_id), filename)
        
        new_file = File(
            player_id=player_id,
            file_path=rel_path,
            file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
        )
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({'success': True, 'file': new_file.to_dict()})
    
    return jsonify({'success': False, 'message': 'Invalid data'}), 400

@main_bp.route('/api/players/<int:player_id>/files', methods=['GET'])
@login_required
def get_player_files(player_id):
    files = File.query.filter_by(player_id=player_id).all()
    return jsonify([f.to_dict() for f in files])

@main_bp.route('/api/files/<int:file_id>/download', methods=['GET'])
@login_required
def download_file(file_id):
    from flask import send_from_directory
    file = File.query.get_or_404(file_id)
    
    # Construct absolute path
    # file.file_path is stored as "player_id/filename"
    directory = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.dirname(file.file_path))
    filename = os.path.basename(file.file_path)
    
    return send_from_directory(directory, filename, as_attachment=True)

@main_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    
    # Remove from disk
    full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
        
    db.session.delete(file)
    db.session.commit()
    return jsonify({'success': True})


# --- Invoices ---
@main_bp.route('/api/payments/<int:id>/invoice', methods=['GET'])
@login_required
def download_invoice(id):
    import qrcode
    from fpdf import FPDF
    import tempfile
    from flask import send_file

    payment = Payment.query.get_or_404(id)
    sub = Subscription.query.get(payment.subscription_id)
    player = Player.query.get(sub.player_id)

    # Generate QR Code
    qr_data = f"Invoice:{payment.invoice_number}\nAmount:{payment.paid_amount}\nPlayer:{player.full_name}\nDate:{payment.payment_date}"
    qr = qrcode.make(qr_data)
    qr_path = os.path.join(tempfile.gettempdir(), f"qr_{id}.png")
    qr.save(qr_path)

    # Custom PDF Class
    class InvoicePDF(FPDF):
        def header(self):
            # Logo Text
            self.set_font('Arial', 'B', 24)
            self.set_text_color(0, 255, 136) # Neon Green
            self.cell(0, 15, 'Boshkash Academy', 0, 1, 'L')
            
            # Subheader
            self.set_font('Arial', '', 10)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5, 'Professional Football Training', 0, 1, 'L')
            
            # Line break
            self.ln(10)
            
            # Invoice Title (Right aligned)
            self.set_y(10)
            self.set_font('Arial', 'B', 30)
            self.set_text_color(220, 220, 220)
            self.cell(0, 15, 'INVOICE', 0, 1, 'R')

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    # Create PDF
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Colors
    bg_color = (245, 245, 245)
    header_color = (30, 41, 59) # Dark Blue
    text_color = (30, 30, 30)

    # --- Invoice Info Block ---
    pdf.set_fill_color(*bg_color)
    pdf.rect(10, 35, 190, 40, 'F')
    
    pdf.set_y(40)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    
    # Left Column (Bill To)
    pdf.set_x(15)
    pdf.cell(40, 5, "BILL TO:", 0, 1)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(*text_color)
    pdf.set_x(15)
    pdf.cell(40, 8, player.full_name, 0, 1)
    pdf.set_font("Arial", '', 10)
    pdf.set_x(15)
    pdf.cell(40, 5, f"Team: {player.team or 'N/A'}", 0, 1)

    # Right Column (Invoice Details)
    # Re-position for right column
    pdf.set_y(40)
    pdf.set_x(120)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(30, 5, "Invoice #:", 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(*text_color)
    pdf.cell(40, 5, payment.invoice_number, 0, 1, 'R')
    
    pdf.set_x(120)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(30, 5, "Date:", 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(*text_color)
    pdf.cell(40, 5, payment.payment_date.strftime('%Y-%m-%d'), 0, 1, 'R')
    
    pdf.ln(20)

    # --- Table Header ---
    pdf.set_fill_color(*header_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 10, "  Description", 0, 0, 'L', 1)
    pdf.cell(40, 10, "Type", 0, 0, 'C', 1)
    pdf.cell(40, 10, "Amount  ", 0, 1, 'R', 1)

    # --- Table Rows ---
    pdf.set_text_color(*text_color)
    pdf.set_font("Arial", '', 11)
    
    pdf.cell(110, 12, f"  Subscription Fee ({sub.start_date.strftime('%b %Y')})", "B", 0, 'L')
    pdf.cell(40, 12, sub.type, "B", 0, 'C')
    pdf.cell(40, 12, f"{payment.paid_amount:.2f}  ", "B", 1, 'R')

    # --- Total ---
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(150, 12, "Total Paid", 0, 0, 'R')
    pdf.set_text_color(0, 128, 0) # Green
    pdf.cell(40, 12, f"${payment.paid_amount:.2f}  ", 0, 1, 'R')

    # --- QR Code & Footer Note ---
    pdf.ln(10)
    pdf.image(qr_path, x=15, y=pdf.get_y(), w=30)
    
    pdf.set_y(pdf.get_y() + 10)
    pdf.set_x(50)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, "Thank you for your business. This is a computer generated invoice and requires no signature.")

    # Output
    pdf_path = os.path.join(tempfile.gettempdir(), f"invoice_{id}.pdf")
    pdf.output(pdf_path)

    return send_file(pdf_path, as_attachment=True, download_name=f"Invoice_{payment.invoice_number}.pdf")

