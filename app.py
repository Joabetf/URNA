import uuid
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configurações do Banco de Dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'uma_chave_secreta_muito_segura' # Mantenha esta linha

db = SQLAlchemy(app)

# Definição dos modelos (tabelas do banco de dados)
class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    voted_elections = db.relationship('Vote', backref='user', lazy=True)

class Election(db.Model):
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    options = db.relationship('Option', backref='election', lazy=True)
    votes = db.relationship('Vote', backref='election', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100), nullable=False)
    election_id = db.Column(db.String, db.ForeignKey('election.id'), nullable=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False)
    election_id = db.Column(db.String, db.ForeignKey('election.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("elections"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id").strip()
        if user_id:
            user = User.query.get(user_id)
            if not user:
                user = User(id=user_id)
                db.session.add(user)
                db.session.commit()
            session["user_id"] = user_id
            return redirect(url_for("elections"))
    return render_template("login.html")

@app.route("/elections")
def elections():
    if "user_id" not in session:
        return redirect(url_for("login"))

    elections = Election.query.all()
    user_votes = [vote.election_id for vote in Vote.query.filter_by(user_id=session["user_id"]).all()]

    return render_template("elections.html", elections=elections, user_votes=user_votes)

@app.route("/vote/<election_id>", methods=["GET", "POST"])
def vote(election_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    election = Election.query.get(election_id)
    if not election:
        return "Eleição não encontrada!", 404

    has_voted = Vote.query.filter_by(user_id=session["user_id"], election_id=election_id).first()
    if has_voted:
        return "Você já votou nesta eleição.", 403

    if request.method == "POST":
        selected_options = request.form.getlist("vote_option")
        
        for option_id in selected_options:
            vote = Vote(user_id=session["user_id"], election_id=election_id, option_id=option_id)
            db.session.add(vote)
        
        db.session.commit()
        return redirect(url_for("elections"))

    return render_template("vote.html", election=election)

@app.route("/results/<election_id>")
def results(election_id):
    election = Election.query.get(election_id)
    if not election:
        return "Eleição não encontrada!", 404
    
    results = {}
    total_votes = 0
    
    for option in election.options:
        vote_count = Vote.query.filter_by(option_id=option.id).count()
        results[option.text] = vote_count
        total_votes += vote_count

    return render_template("results.html", election=election, results=results, total_votes=total_votes)

@app.route("/create_poll", methods=["GET", "POST"])
def create_poll():
    if request.method == "POST":
        title = request.form.get("title")
        poll_type = request.form.get("type")
        options_str = request.form.get("options")
        
        options_list = [o.strip() for o in options_str.split(',') if o.strip()]
        
        if title and poll_type and options_list:
            election_id = str(uuid.uuid4())
            new_election = Election(id=election_id, title=title, type=poll_type)
            db.session.add(new_election)
            
            for option_text in options_list:
                new_option = Option(text=option_text, election=new_election)
                db.session.add(new_option)
            
            db.session.commit()
            return redirect(url_for("elections"))

    return render_template("create_poll.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)