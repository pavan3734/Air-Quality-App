from flask import Flask, render_template, request, redirect, url_for, session, flash,jsonify 
import requests
from urllib.parse import quote
from flask_sqlalchemy import SQLAlchemy 
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from urllib.parse import quote
from flask_migrate import Migrate
import datetime
import pandas as pd
from matplotlib.figure import Figure
import io
import base64

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret_key' 

db = SQLAlchemy(app) 
migrate = Migrate(app, db)
admin = Admin(app, name='Community Admin', template_mode='bootstrap3')
 
 
openweatherMapApiKey ="7d9d91e8a10b95b8d8f7a2c5656e5bf9" 

@app.route('/api/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'City name is required'}), 400

    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={openweatherMapApiKey}&units=metric'

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            return jsonify(data)
        else:
            return jsonify({'error': data.get('message', 'Failed to retrieve data')}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500  
     
AQI_API_KEY = '904164073b279b07ff95c1ead5e07cd58eedf0c0'

@app.route('/api/aqi', methods=['GET'])
def get_aqi():
    city = request.args.get('city') 
    if not city:
        return jsonify({'error': 'City name is required'}), 400

    url = f'http://api.waqi.info/feed/{city}/?token={AQI_API_KEY}'
  
    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200 and data['status'] == 'ok':
            aqi = data['data']['aqi']
            return jsonify({'aqi': aqi, 'city': city})
        else:
            return jsonify({'error': data.get('data', 'Failed to retrieve AQI')}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500



NEWS_API_KEY = 'pub_605312e53e8da917a4a1228232572b28a4267'
@app.route('/api/news', methods=['GET'])
def get_aqi_news():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'City name is required'}), 400

    encoded_city = quote(city)
    url = f'https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&q=air quality {encoded_city}'

    try:
        response = requests.get(url)
        print("Response Status Code:", response.status_code)
        print("Response Data:", response.text) 
        data = response.json()

        if response.status_code == 200:
            articles = data.get('results', [])  
            return jsonify({'articles': articles[:10]}) 
        else:
            error_message = data.get('message', 'Failed to retrieve news')
            print("Error Message:", error_message)  
            return jsonify({'error': error_message}), response.status_code
    except Exception as e:
        print("Exception occurred:", str(e))
        return jsonify({'error': str(e)}), 500

  
  
    
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=True)

    def __init__(self, name, email, password, city):
        self.name = name
        self.email = email
        self.password = password
        self.city = city 
         
           
class CarbonFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    transport = db.Column(db.Float, nullable=False, default=0.0)
    electricity = db.Column(db.Float, nullable=False, default=0.0)
    waste = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.Column(db.Integer, default=0)
    user = db.relationship('User', backref='posts')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user = db.relationship('User', backref='comments')
    post = db.relationship('Post', backref='comments')


admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Post, db.session))
admin.add_view(ModelView(Comment, db.session))

@app.route('/', methods=['GET'])
def index():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmpassword']
        city = request.form['city']

      
        if password != confirm_password:
            flash("Passwords do not match!")
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("User with this email already exists.")
            return render_template('register.html')

        new_user = User(name=name, email=email, password=password, city=city)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        
        if not email or not password:
            return render_template('login.html', email=email)

        user = User.query.filter_by(email=email, password=password).first()
        
        if user:
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.name
            return redirect(url_for('home'))
        
        flash("Invalid Email or Password.")
        return redirect(url_for('login'))

    return render_template('login.html')   


@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    leaderboard = db.session.query(
        User.name, 
        User.city, 
        db.func.sum(CarbonFootprint.total).label('total_footprint')
    ).join(CarbonFootprint).group_by(User.id).order_by(db.func.sum(CarbonFootprint.total).desc()).all()

    leaderboard_with_rank = [
        {
            "rank": idx + 1, 
            "name": name, 
            "city": city, 
            "total_footprint": total_footprint
        } 
        for idx, (name, city, total_footprint) in enumerate(leaderboard)
    ]

    return render_template('leaderboard.html', leaderboard=leaderboard_with_rank)





@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'),message="Incorrect Details")
    return render_template('home.html', username=session['username'])

@app.route('/community', methods=['GET', 'POST'])
def community():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        user_id = session['user_id']
        new_post = Post(content=content, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()
        flash("Post created successfully!")

    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('community.html', posts=posts)

@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return redirect(url_for('community'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    content = request.form['comment']
    user_id = session['user_id']
    new_comment = Comment(content=content, user_id=user_id, post_id=post_id)
    db.session.add(new_comment)
    db.session.commit()
    return redirect(url_for('community'))



@app.route('/logout')
def logout():
    session.clear()  
    flash("You have logged out successfully.")
    return redirect(url_for('index')) 
 
@app.route('/carbon_tracker', methods=['GET', 'POST'])
def carbon_tracker():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    carbon_footprint_result = None 

    if request.method == 'POST':
        try:
            transport = float(request.form['transport'])
            electricity = float(request.form['electricity'])
            waste = float(request.form['waste'])
            user_id = session['user_id']

            total = transport * 0.25 + electricity * 0.75 + waste * 1.2

            entry = CarbonFootprint(user_id=user_id, transport=transport, electricity=electricity, waste=waste, total=total)
            db.session.add(entry)
            db.session.commit()
            flash("Carbon footprint logged successfully!")

            carbon_footprint_result = total 

        except Exception as e:
            flash(f"Error: {str(e)}")

    user_id = session['user_id']
    entries = CarbonFootprint.query.filter_by(user_id=user_id).order_by(CarbonFootprint.date).all()

    dates = [entry.date.strftime('%Y-%m-%d') for entry in entries]
    totals = [entry.total for entry in entries]

    fig = Figure(figsize=(8, 6))
    ax = fig.subplots()
    ax.plot(dates, totals, marker='o', color='green', label='Total CO2')
    ax.set_title('Your Carbon Footprint Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Total CO2 (kg)')
    ax.grid(True)
    ax.legend()


    fig.autofmt_xdate(rotation=45)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plot_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    return render_template('carbon_tracker.html', entries=entries, plot_data=plot_data, carbon_footprint_result=carbon_footprint_result)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)