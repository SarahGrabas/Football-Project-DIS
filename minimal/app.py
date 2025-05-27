from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Abbreviation lookup
TEAM_ABBR = {
    "Arsenal": "ARS", "Aston Villa": "AVL", "AFC Bournemouth": "BOU",
    "Brentford": "BRE", "Brighton & Hove Albion": "BHA", "Burnley": "BUR",
    "Chelsea": "CHE", "Crystal Palace": "CRY", "Everton": "EVE",
    "Fulham": "FUL", "Liverpool": "LIV", "Luton Town": "LUT",
    "Manchester City": "MCI", "Manchester United": "MUN", "Newcastle United": "NEW",
    "Nottingham Forest": "NFO", "Sheffield United": "SHU", "Tottenham Hotspur": "TOT",
    "West Ham United": "WHU", "Wolverhampton Wanderers": "WOL"
}

def get_db_connection():
    conn = sqlite3.connect('yourdata.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_team_abbr(lineup):
    conn = get_db_connection()
    for player in lineup.values():
        if player:
            row = conn.execute("SELECT Team FROM my_table WHERE Player = ?", (player,)).fetchone()
            if row:
                team_name = row['Team']
                return TEAM_ABBR.get(team_name, team_name[:3].upper())
    return "UNK"

@app.route("/lineup", methods=["GET", "POST"])
def lineup():
    conn = get_db_connection()
    players = conn.execute("SELECT Player, Pos, Team FROM 'my_table'").fetchall()
    conn.close()

    gks = [p['Player'] for p in players if 'GK' in p['Pos']]
    dfs = [p['Player'] for p in players if 'DF' in p['Pos']]
    mfs = [p['Player'] for p in players if 'MF' in p['Pos']]
    fws = [p['Player'] for p in players if 'FW' in p['Pos']]
    teams = sorted(set(p['Team'] for p in players))

    if request.method == "POST":
        if 'lineup1' not in session:
            session['lineup1'] = request.form.to_dict()
        elif 'lineup2' not in session:
            session['lineup2'] = request.form.to_dict()
            return redirect(url_for('h2h'))
        return redirect(url_for('lineup'))

    return render_template("lineup.html", gks=gks, dfs=dfs, mfs=mfs, fws=fws, teams=teams,
                           lineup1=session.get('lineup1'), lineup2=session.get('lineup2'))

@app.route("/h2h")
def h2h():
    lineup1 = session.get('lineup1')
    lineup2 = session.get('lineup2')
    if not lineup1 or not lineup2:
        return redirect(url_for('lineup'))

    conn = get_db_connection()

    def get_player_info(name):
        return conn.execute("SELECT * FROM 'my_table' WHERE Player = ?", (name,)).fetchone()

    def extract_lineup_data(lineup):
        keys = ['gk'] + [f'df{i}' for i in range(4)] + [f'mf{i}' for i in range(3)] + [f'fw{i}' for i in range(3)]
        return [get_player_info(lineup.get(k)) for k in keys if lineup.get(k)]

    team1_players = extract_lineup_data(lineup1)
    team2_players = extract_lineup_data(lineup2)

    def stat_sum(players, key):
        return sum(p[key] for p in players if p[key] is not None)

    def stat_avg(players, key):
        values = [p[key] for p in players if p[key] is not None]
        return round(sum(values) / len(values), 1) if values else 0

    stats = {
        'Gls': (stat_sum(team1_players, 'Gls'), stat_sum(team2_players, 'Gls')),
        'Ast': (stat_sum(team1_players, 'Ast'), stat_sum(team2_players, 'Ast')),
        'Age (avg)': (stat_avg(team1_players, 'Age'), stat_avg(team2_players, 'Age')),
        'Starts': (stat_sum(team1_players, 'Starts'), stat_sum(team2_players, 'Starts')),
        'CrdY': (stat_sum(team1_players, 'CrdY'), stat_sum(team2_players, 'CrdY')),
        'CrdR': (stat_sum(team1_players, 'CrdR'), stat_sum(team2_players, 'CrdR')),
    }

    return render_template("h2h.html", team1=lineup1, team2=lineup2,
                           team1_data=team1_players, team2_data=team2_players, stats=stats)

@app.route("/players")
def show_players():
    conn = get_db_connection()
    rows = conn.execute("SELECT Player, Age, Pos, Team, Gls, Ast FROM 'my_table'").fetchall()
    conn.close()
    return render_template("players.html", rows=rows)

@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for('lineup'))

@app.route("/simulate")
def simulate():
    lineup1 = session.get('lineup1')
    lineup2 = session.get('lineup2')
    if not lineup1 or not lineup2:
        return redirect(url_for('lineup'))

    conn = get_db_connection()
    def get_players(lineup):
        order = ['gk'] + [f'df{i}' for i in range(4)] + [f'mf{i}' for i in range(3)] + [f'fw{i}' for i in range(3)]
        return [conn.execute("SELECT * FROM 'my_table' WHERE Player = ?", (lineup[pos],)).fetchone()
                for pos in order if lineup.get(pos)]

    players1 = get_players(lineup1)
    players2 = get_players(lineup2)
    conn.close()

    return render_template("simulate.html",
                           players1=players1, players2=players2,
                           team1_abbr=get_team_abbr(lineup1),
                           team2_abbr=get_team_abbr(lineup2))

@app.route("/run_simulation")
def run_simulation():
    import random

    def get_players(lineup):
        order = ['gk'] + [f'df{i}' for i in range(4)] + [f'mf{i}' for i in range(3)] + [f'fw{i}' for i in range(3)]
        return [lineup.get(pos) for pos in order if lineup.get(pos)]

    def fetch_player_stats(player_names):
        conn = get_db_connection()
        players = []
        for name in player_names:
            row = conn.execute("SELECT Player, Pos, Gls, CrdY, CrdR FROM 'my_table' WHERE Player = ?", (name,)).fetchone()
            if row:
                players.append({
                    'name': row['Player'],
                    'pos': row['Pos'],
                    'goals': row['Gls'],
                    'yellow': 0,
                    'red': False,
                    'crdY': row['CrdY'],
                    'crdR': row['CrdR']
                })
        conn.close()
        return players

    lineup1 = session.get('lineup1')
    lineup2 = session.get('lineup2')
    if not lineup1 or not lineup2:
        return jsonify({'log': ["Lineups missing."]})

    team1 = {'name': 'Team 1', 'score': 0, 'players': fetch_player_stats(get_players(lineup1))}
    team2 = {'name': 'Team 2', 'score': 0, 'players': fetch_player_stats(get_players(lineup2))}

    log = []
    position_weight = {'FW': 1.5, 'MF': 1.2, 'DF': 0.8, 'GK': 0.2}

    def active_players(team):
        return [p for p in team['players'] if not p['red']]

    def pick_scorer(team, opponent):
        candidates = active_players(team)
        player_advantage = len(candidates) - len(active_players(opponent))
        scoring_boost = 1 + (0.1 * max(0, player_advantage))
        weights = [((p['goals'] + 1) * position_weight.get(p['pos'], 1) * scoring_boost) for p in candidates]
        return random.choices(candidates, weights=weights)[0]

    def give_yellow(team, minute):
        candidates = active_players(team)
        if not candidates: return
        weights = [(5 + p['crdY']) if p['crdY'] >= 1 else 1 for p in candidates]
        p = random.choices(candidates, weights=weights)[0]
        p['yellow'] += 1
        if p['yellow'] == 2:
            p['red'] = True
            log.append(f"{minute}': 🟥 {p['name']} gets a 2nd yellow → RED")
        else:
            log.append(f"{minute}': 🟨 {p['name']} gets a yellow card")

    def give_red(team, minute):
        candidates = active_players(team)
        if not candidates: return
        weights = [(2 + p['crdR']) if p['crdR'] >= 1 else 1 for p in candidates]
        p = random.choices(candidates, weights=weights)[0]
        p['red'] = True
        log.append(f"{minute}': 🟥 {p['name']} is sent off (straight red)")

    for minute in range(1, 91):
        event_pool = ['nothing'] * 160 + ['goal1'] * 6 + ['goal2'] * 6 + ['y1'] * 3 + ['y2'] * 3 + ['r1'] + ['r2']
        event = random.choice(event_pool)
        if event == 'goal1' and active_players(team1):
            scorer = pick_scorer(team1, team2)
            team1['score'] += 1
            log.append(f"{minute}': ⚽ {scorer['name']} scores for Team 1!")
        elif event == 'goal2' and active_players(team2):
            scorer = pick_scorer(team2, team1)
            team2['score'] += 1
            log.append(f"{minute}': ⚽ {scorer['name']} scores for Team 2!")
        elif event == 'y1':
            give_yellow(team1, minute)
        elif event == 'y2':
            give_yellow(team2, minute)
        elif event == 'r1':
            give_red(team1, minute)
        elif event == 'r2':
            give_red(team2, minute)
        else:
            log.append(f"{minute}'")

    log.append(f"\n🏑 Final Score: Team 1 {team1['score']} - {team2['score']} Team 2")
    return jsonify({'log': log})
