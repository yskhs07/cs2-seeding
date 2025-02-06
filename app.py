# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List
import random  # Add this at the top with other imports

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group = db.Column(db.String(1))
    matches_played = db.Column(db.Integer, default=0)
    rounds_won = db.Column(db.Integer, default=0)
    rounds_lost = db.Column(db.Integer, default=0)
    matches_won = db.Column(db.Integer, default=0)
    # Add player fields
    player1 = db.Column(db.String(100))
    player2 = db.Column(db.String(100))
    player3 = db.Column(db.String(100))
    player4 = db.Column(db.String(100))
    player5 = db.Column(db.String(100))
    captain = db.Column(db.Integer)  # 1-5 representing which player is captain

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
    score1 = db.Column(db.Integer, default=0)
    score2 = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    stage = db.Column(db.String(20), default='group')
    is_bo3 = db.Column(db.Boolean, default=True)
    is_bo5 = db.Column(db.Boolean, default=False)
    # Map scores
    map1_score1 = db.Column(db.Integer, default=0)
    map1_score2 = db.Column(db.Integer, default=0)
    map2_score1 = db.Column(db.Integer, default=0)
    map2_score2 = db.Column(db.Integer, default=0)
    map3_score1 = db.Column(db.Integer, default=0)
    map3_score2 = db.Column(db.Integer, default=0)
    map4_score1 = db.Column(db.Integer, default=0)
    map4_score2 = db.Column(db.Integer, default=0)
    map5_score1 = db.Column(db.Integer, default=0)
    map5_score2 = db.Column(db.Integer, default=0)

    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])

@app.route('/')
def index():
    teams = Team.query.all()
    matches = Match.query.all()
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
    try:
        match = Match.query.get_or_404(match_id)
        print(f"Updating match {match_id}")
        
        if match.stage == 'group':
            score1 = int(request.form.get('score1', 0))
            score2 = int(request.form.get('score2', 0))
            print(f"Received scores: {score1} - {score2}")
            
            # Update match scores
            match.score1 = score1
            match.score2 = score2
            match.completed = True
            
            # First, reset all team statistics
            teams = Team.query.all()
            for team in teams:
                team.matches_played = 0
                team.matches_won = 0
                team.rounds_won = 0
                team.rounds_lost = 0
            
            # Then recalculate from all completed matches
            group_matches = Match.query.filter_by(stage='group', completed=True).all()
            print(f"Recalculating stats from {len(group_matches)} completed matches")
            
            for m in group_matches:
                # Update matches played
                m.team1.matches_played += 1
                m.team2.matches_played += 1
                
                # Update rounds won/lost
                m.team1.rounds_won += m.score1
                m.team2.rounds_won += m.score2
                m.team1.rounds_lost += m.score2
                m.team2.rounds_lost += m.score1
                
                # Update matches won
                if m.score1 > m.score2:
                    m.team1.matches_won += 1
                elif m.score2 > m.score1:
                    m.team2.matches_won += 1
            
            db.session.commit()
            print("Database commit successful")
            flash('Score updated successfully!')
            
    except Exception as e:
        print(f"Error in update_score: {str(e)}")
        db.session.rollback()
        flash('Error updating score')
        
    return redirect(url_for('index'))

@app.route('/get_standings')
def get_standings():
    teams = Team.query.all()
    standings = {}
    
    for team in teams:
        if team.group not in standings:
            standings[team.group] = []
        standings[team.group].append({
            'id': team.id,
            'name': team.name,
            'matches_played': team.matches_played,
            'matches_won': team.matches_won,
            'round_difference': team.round_difference,
            'rounds_won': team.rounds_won,
            'rounds_lost': team.rounds_lost
        })
    
    # Sort teams in each group by matches won, then round difference
    for group in standings:
        standings[group].sort(key=lambda x: (-x['matches_won'], -x['round_difference']))
    
    return standings

@app.route('/setup_tournament', methods=['POST'])
def setup_tournament():
    try:
        # Don't clear team data anymore, only matches
        db.session.query(Match).delete()
        
        # Get all team names and player information
        team_names = []
        team_players = []
        team_captains = []
        
        for i in range(9):
            team_name = request.form.get(f'team{i}')
            if team_name:
                players = []
                for j in range(5):
                    player = request.form.get(f'team{i}_player{j+1}', '')
                    players.append(player)
                captain = request.form.get(f'team{i}_captain', 1)
                
                team_names.append(team_name)
                team_players.append(players)
                team_captains.append(captain)
        
        # Shuffle the teams randomly
        indices = list(range(len(team_names)))
        random.shuffle(indices)
        
        # Create or update teams and assign to groups
        for idx in indices:
            # Assign groups (A, B, C) based on index
            group = chr(65 + (idx // 3))  # A, B, or C based on division by 3
            
            # Try to find existing team
            team = Team.query.filter_by(name=team_names[idx]).first()
            if team:
                team.group = group
                team.player1 = team_players[idx][0]
                team.player2 = team_players[idx][1]
                team.player3 = team_players[idx][2]
                team.player4 = team_players[idx][3]
                team.player5 = team_players[idx][4]
                team.captain = team_captains[idx]
            else:
                team = Team(
                    name=team_names[idx],
                    group=group,
                    player1=team_players[idx][0],
                    player2=team_players[idx][1],
                    player3=team_players[idx][2],
                    player4=team_players[idx][3],
                    player5=team_players[idx][4],
                    captain=team_captains[idx]
                )
                db.session.add(team)
        
        db.session.commit()
        
        # Generate group stage matches
        current_time = datetime.now()
        for group in ['A', 'B', 'C']:
            group_teams = Team.query.filter_by(group=group).all()
            # Generate round-robin matches - each team plays against others once
            for i in range(len(group_teams)):
                for j in range(i + 1, len(group_teams)):
                    match = Match(
                        team1_id=group_teams[i].id,
                        team2_id=group_teams[j].id,
                        start_time=current_time,
                        stage='group'
                    )
                    db.session.add(match)
                    current_time += timedelta(hours=1)
        
        db.session.commit()
        flash('Tournament setup completed!')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Error in setup_tournament: {str(e)}")
        db.session.rollback()
        flash('Error setting up tournament')
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

@app.route('/get_map_scores/<int:match_id>')
def get_map_scores(match_id):
    match = Match.query.get_or_404(match_id)
    scores = {}
    max_maps = 5 if match.is_bo5 else 3
    
    for i in range(1, max_maps + 1):
        scores[f'map{i}_score1'] = getattr(match, f'map{i}_score1', 0)
        scores[f'map{i}_score2'] = getattr(match, f'map{i}_score2', 0)
    
    return jsonify(scores)

@app.route('/edit_match/<int:match_id>', methods=['POST'])
def edit_match(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        data = request.get_json()
        
        # Update overall match score
        match.score1 = int(data.get('score1', 0))
        match.score2 = int(data.get('score2', 0))
        match.completed = data.get('completed', False)
        
        # Update individual map scores
        max_maps = 5 if match.is_bo5 else 3
        for i in range(1, max_maps + 1):
            setattr(match, f'map{i}_score1', int(data.get(f'map{i}_score1', 0)))
            setattr(match, f'map{i}_score2', int(data.get(f'map{i}_score2', 0)))
        
        db.session.commit()
        
        # Only check for finals generation if this was a semifinal match
        if match.stage == 'semifinal' and match.completed:
            # Check if both semifinals are complete with valid scores
            semifinal_matches = Match.query.filter_by(stage='semifinal').all()
            both_completed = True
            
            if len(semifinal_matches) == 2:
                for semi in semifinal_matches:
                    if not semi.completed or not (semi.score1 >= 2 or semi.score2 >= 2):
                        both_completed = False
                        break
                
                # Only generate finals if both semifinals are complete and finals don't exist
                if both_completed:
                    existing_final = Match.query.filter_by(stage='final').first()
                    if not existing_final:
                        # Get winners from semifinals
                        winners = []
                        for semi in semifinal_matches:
                            winner = semi.team1 if semi.score1 > semi.score2 else semi.team2
                            winners.append(winner)
                        
                        # Create finals match
                        finals_match = Match(
                            team1=winners[0],
                            team2=winners[1],
                            stage='final',
                            is_bo5=True,
                            start_time=datetime.now()
                        )
                        db.session.add(finals_match)
                        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error in edit_match: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    db.session.delete(match)
    db.session.commit()
    return {'success': True}

@app.route('/generate_playoffs', methods=['GET', 'POST'])
def generate_playoffs():
    try:
        # Clear any existing playoff matches
        Match.query.filter(Match.stage.in_(['semifinal', 'final'])).delete()
        
        # Get group winners and runners-up
        playoff_teams = []
        for group in ['A', 'B', 'C']:
            group_teams = Team.query.filter_by(group=group).order_by(
                Team.matches_won.desc(),
                (Team.rounds_won - Team.rounds_lost).desc()
            ).limit(2).all()
            playoff_teams.extend(group_teams)
        
        # Sort teams by wins and round difference for seeding
        playoff_teams.sort(key=lambda x: (x.matches_won, x.rounds_won - x.rounds_lost), reverse=True)
        
        # Generate semifinals (BO3)
        current_time = datetime.now()
        semifinal1 = Match(
            team1_id=playoff_teams[0].id,
            team2_id=playoff_teams[3].id,
            start_time=current_time,
            stage='semifinal',
            is_bo3=True,
            is_bo5=False
        )
        
        semifinal2 = Match(
            team1_id=playoff_teams[1].id,
            team2_id=playoff_teams[2].id,
            start_time=current_time + timedelta(hours=1),
            stage='semifinal',
            is_bo3=True,
            is_bo5=False
        )
        
        db.session.add(semifinal1)
        db.session.add(semifinal2)
        db.session.commit()
        
        flash('Playoffs generated successfully!')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Error generating playoffs: {str(e)}")
        db.session.rollback()
        flash('Error generating playoffs')
        return redirect(url_for('index'))

@app.route('/check_semifinals_status')
def check_semifinals_status():
    # Get all semifinal matches
    semifinal_matches = Match.query.filter_by(stage='semifinal').all()
    
    # Check if both semifinals are completed and have valid scores
    both_completed = True
    if len(semifinal_matches) == 2:
        for match in semifinal_matches:
            if not match.completed:
                both_completed = False
            else:
                # Verify one team has won (2-0 or 2-1)
                if not (match.score1 >= 2 or match.score2 >= 2):
                    both_completed = False
    else:
        both_completed = False
    
    return jsonify({'both_completed': both_completed})

@app.route('/generate_finals', methods=['POST'])
def generate_finals():
    # Only generate finals if it doesn't exist yet
    existing_final = Match.query.filter_by(stage='final').first()
    if existing_final:
        return jsonify({'success': False, 'message': 'Finals already exist'})

    # Get completed semifinals
    semifinal_matches = Match.query.filter_by(stage='semifinal', completed=True).all()
    
    if len(semifinal_matches) == 2:
        # Get winners from each semifinal
        winners = []
        for match in semifinal_matches:
            winner = match.team1 if match.score1 > match.score2 else match.team2
            winners.append(winner)
        
        # Create finals match
        finals_match = Match(
            team1=winners[0],
            team2=winners[1],
            stage='final',
            score1=0,
            score2=0,
            completed=False
        )
        db.session.add(finals_match)
        db.session.commit()
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Not all semifinals are completed'})

@app.route('/reset_tournament', methods=['POST'])
def reset_tournament():
    try:
        # Delete all matches
        db.session.query(Match).delete()
        
        # Delete all teams
        db.session.query(Team).delete()
        
        # Commit the changes
        db.session.commit()
        flash('Tournament reset successfully!')
    except Exception as e:
        print(f"Error in reset_tournament: {str(e)}")
        db.session.rollback()
        flash('Error resetting tournament')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)