from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gofund.db'
app.config['SECRET_KEY'] = 'gofunduganda2026'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

ADMIN_EMAIL = 'franeputoit@gmail.com'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Campaign model
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    goal = db.Column(db.Float, nullable=False)
    raised = db.Column(db.Float, default=0)
    user_id = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200), nullable=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!')
            return redirect(url_for('register'))
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = (email == ADMIN_EMAIL)
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        flash('Please login first!')
        return redirect(url_for('login'))
    my_campaigns = Campaign.query.filter_by(user_id=session['user_id']).all()
    total_raised = sum(c.raised for c in my_campaigns)
    return render_template('dashboard.html', my_campaigns=my_campaigns, total_raised=total_raised)

@app.route('/campaigns')
def campaigns():
    query = request.args.get('q', '')
    if query:
        all_campaigns = Campaign.query.filter(Campaign.title.ilike(f'%{query}%')).all()
    else:
        all_campaigns = Campaign.query.all()
    return render_template('campaigns.html', campaigns=all_campaigns, query=query)

@app.route('/campaigns/new', methods=['GET', 'POST'])
def new_campaign():
    if not session.get('user_id'):
        flash('Please login first!')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        goal = float(request.form['goal'])
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
        campaign = Campaign(title=title, description=description, goal=goal, raised=0, user_id=session['user_id'], image=image)
        db.session.add(campaign)
        db.session.commit()
        flash('Campaign created successfully!')
        return redirect(url_for('campaigns'))
    return render_template('new_campaign.html')

@app.route('/campaigns/<int:campaign_id>')
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    return render_template('campaign_detail.html', campaign=campaign)

@app.route('/campaigns/<int:campaign_id>/donate', methods=['POST'])
def donate(campaign_id):
    if not session.get('user_id'):
        flash('Please login to donate!')
        return redirect(url_for('login'))
    campaign = Campaign.query.get_or_404(campaign_id)
    amount = float(request.form['amount'])
    campaign.raised += amount
    db.session.commit()
    flash(f'Thank you! You donated UGX {amount} to {campaign.title}')
    return redirect(url_for('campaign_detail', campaign_id=campaign_id))

@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        flash('Access denied!')
        return redirect(url_for('home'))
    users = User.query.all()
    campaigns = Campaign.query.all()
    total_users = len(users)
    total_campaigns = len(campaigns)
    total_donations = sum(c.raised for c in campaigns)
    return render_template('admin.html', users=users, campaigns=campaigns,
                           total_users=total_users, total_campaigns=total_campaigns,
                           total_donations=total_donations)

@app.route('/admin/delete/<int:campaign_id>')
def admin_delete(campaign_id):
    if not session.get('is_admin'):
        flash('Access denied!')
        return redirect(url_for('home'))
    campaign = Campaign.query.get_or_404(campaign_id)
    db.session.delete(campaign)
    db.session.commit()
    flash('Campaign deleted!')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)