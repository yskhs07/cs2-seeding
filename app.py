# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
db = SQLAlchemy(app)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group = db.Column(db.String(1))
    matches_played = db.Column(db.Integer, default=0)
    rounds_won = db.Column(db.Integer, default=0)
    rounds_lost = db.Column(db.Integer, default=0)
    matches_won = db.Column(db.Integer, default=0)

    @property
    def round_difference(self):
        return self.rounds_won - self.rounds_lost

    @property
    def win_rate(self):
        if self.matches_played == 0:
            return 0.0
        return self.matches_won / self.matches_played

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    start_time = db.Column(db.DateTime, nullable=False)
    is_bo3 = db.Column(db.Boolean, default=False)
    completed = db.Column(db.Boolean, default=False)
    score1 = db.Column(db.Integer, default=0)
    score2 = db.Column(db.Integer, default=0)
    stage = db.Column(db.String(20))  # 'group', 'semifinal', 'final'

    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])

@app.route('/')
def index():
    teams = Team.query.all()
    matches = Match.query.order_by(Match.start_time).all()
    return render_template('index.html', teams=teams, matches=matches)

@app.route('/add_team', methods=['POST'])
def add_team():
    name = request.form.get('team_name')
    group = request.form.get('group')
    team = Team(name=name, group=group)
    db.session.add(team)
    db.session.commit()
    flash('Team added successfully!')
    return redirect(url_for('index'))

@app.route('/add_match', methods=['POST'])
def add_match():
    team1_id = request.form.get('team1')
    team2_id = request.form.get('team2')
    start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    is_bo3 = request.form.get('is_bo3') == 'true'
    stage = request.form.get('stage')

    match = Match(
        team1_id=team1_id,
        team2_id=team2_id,
        start_time=start_time,
        is_bo3=is_bo3,
        stage=stage
    )
    db.session.add(match)
    db.session.commit()
    flash('Match added successfully!')
    return redirect(url_for('index'))

@app.route('/update_score/<int:match_id>', methods=['POST'])
def update_score(match_id):
    match = Match.query.get_or_404(match_id)
    score1 = int(request.form.get('score1'))
    score2 = int(request.form.get('score2'))
    
    match.score1 = score1
    match.score2 = score2
    match.completed = True
    
    # Update team statistics
    team1 = match.team1
    team2 = match.team2
    
    team1.matches_played += 1
    team2.matches_played += 1
    team1.rounds_won += score1
    team2.rounds_won += score2
    team1.rounds_lost += score2
    team2.rounds_lost += score1
    
    if score1 > score2:
        team1.matches_won += 1
    else:
        team2.matches_won += 1
    
    db.session.commit()
    flash('Score updated successfully!')
    return redirect(url_for('index'))

@app.route('/get_standings')
def get_standings():
    teams = Team.query.all()
    standings = {}
    
    for team in teams:
        if team.group not in standings:
            standings[team.group] = []
        standings[team.group].append({
            'name': team.name,
            'matches_played': team.matches_played,
            'matches_won': team.matches_won,
            'round_difference': team.round_difference
        })
    
    # Sort teams in each group
    for group in standings:
        standings[group].sort(key=lambda x: (-x['matches_won'], -x['round_difference']))
    
    return standings

@app.route('/setup_tournament', methods=['POST'])
def setup_tournament():
    # Clear existing tournament data
    db.session.query(Match).delete()
    db.session.query(Team).delete()
    
    # Create teams and assign to groups
    teams = []
    for i in range(9):
        team_name = request.form.get(f'team{i}')
        group = chr(65 + (i // 3))  # A, B, or C
        team = Team(name=team_name, group=group)
        teams.append(team)
        db.session.add(team)
    
    db.session.commit()
    
    # Generate group stage matches
    current_time = datetime.now()
    for group in ['A', 'B', 'C']:
        group_teams = [t for t in teams if t.group == group]
        # Generate round-robin matches
        for i in range(len(group_teams)):
            for j in range(i + 1, len(group_teams)):
                match = Match(
                    team1_id=group_teams[i].id,
                    team2_id=group_teams[j].id,
                    start_time=current_time,
                    is_bo3=False,
                    stage='group'
                )
                db.session.add(match)
                current_time += timedelta(hours=1)
    
    db.session.commit()
    flash('Tournament setup completed!')
    return redirect(url_for('index'))

@app.route('/get_match/<int:match_id>')
def get_match(match_id):
    match = Match.query.get_or_404(match_id)
    return {
        'id': match.id,
        'start_time': match.start_time.strftime('%Y-%m-%dT%H:%M'),
        'score1': match.score1,
        'score2': match.score2
    }

@app.route('/edit_match/<int:match_id>', methods=['POST'])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    data = request.get_json()
    
    match.start_time = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M')
    match.score1 = int(data['score1'])
    match.score2 = int(data['score2'])
    
    db.session.commit()
    return {'success': True}

@app.route('/delete_match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    db.session.delete(match)
    db.session.commit()
    return {'success': True}

@app.route('/generate_playoffs')
def generate_playoffs():
    # Get group winners and best second place
    standings = get_standings()
    playoff_teams = []
    
    # Get group winners
    for group in ['A', 'B', 'C']:
        if group in standings:
            playoff_teams.append(standings[group][0])  # First place in each group
    
    # Get best second place
    second_places = []
    for group in ['A', 'B', 'C']:
        if group in standings and len(standings[group]) > 1:
            second_places.append(standings[group][1])
    
    if second_places:
        best_second = max(second_places, key=lambda x: (x['matches_won'], x['round_difference']))
        playoff_teams.append(best_second)
    
    # Generate semifinal matches
    current_time = datetime.now()
    
    # Semifinal 1: Best group winner vs Best second place
    # Semifinal 2: Second best group winner vs Third best group winner
    if len(playoff_teams) == 4:
        match1 = Match(
            team1_id=playoff_teams[0]['id'],
            team2_id=playoff_teams[3]['id'],
            start_time=current_time,
            is_bo3=True,
            stage='semifinal'
        )
        current_time += timedelta(hours=3)
        
        match2 = Match(
            team1_id=playoff_teams[1]['id'],
            team2_id=playoff_teams[2]['id'],
            start_time=current_time,
            is_bo3=True,
            stage='semifinal'
        )
        
        db.session.add(match1)
        db.session.add(match2)
        db.session.commit()
    
    return {'success': True}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)