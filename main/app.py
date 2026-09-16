from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio, random, math
from datetime import datetime, timedelta, timezone

app = FastAPI(title='RailCast Dynamic ETA API', version='1.0.0')
BASE = Path(__file__).parent

# Demo data. Replace this layer with authorised railway/GPS feeds for production.
TRAINS = {
    '12345': {
        'number': '12345', 'name': 'Demo Rajdhani Express', 'from': 'New Delhi', 'to': 'Patna Jn',
        'route': [
            ('New Delhi', 28.6139, 77.2090, 0),
            ('Kanpur Central', 26.4499, 80.3319, 440),
            ('Prayagraj Jn', 25.4358, 81.8463, 630),
            ('Varanasi Jn', 25.3176, 82.9739, 780),
            ('Buxar', 25.5740, 83.9770, 890),
            ('Ara Jn', 25.5560, 84.6620, 960),
            ('Patna Jn', 25.5941, 85.1376, 1030),
        ],
        'base_delay': 7, 'speed': 86
    },
    '12951': {
        'number': '12951', 'name': 'Demo Mumbai Rajdhani', 'from': 'Mumbai Central', 'to': 'New Delhi',
        'route': [
            ('Mumbai Central', 18.9690, 72.8194, 0),
            ('Surat', 21.1702, 72.8311, 260),
            ('Vadodara', 22.3072, 73.1812, 400),
            ('Ratlam', 23.3342, 75.0367, 610),
            ('Kota', 25.2138, 75.8648, 790),
            ('New Delhi', 28.6139, 77.2090, 1050),
        ],
        'base_delay': 3, 'speed': 82
    },
    '22691': {
        'number': '22691', 'name': 'Demo Bengaluru Express', 'from': 'KSR Bengaluru', 'to': 'Hazrat Nizamuddin',
        'route': [
            ('KSR Bengaluru', 12.9784, 77.6408, 0),
            ('Dharwad', 15.4589, 75.0078, 410),
            ('Pune', 18.5204, 73.8567, 760),
            ('Bhopal', 23.2599, 77.4126, 1320),
            ('Agra Cantt', 27.1603, 77.9986, 1650),
            ('Hazrat Nizamuddin', 28.5895, 77.3068, 1740),
        ],
        'base_delay': 11, 'speed': 78
    }
}

state = {}
for t in TRAINS.values():
    state[t['number']] = {'segment': 1, 'progress': 0.58, 'delay': t['base_delay'], 'congestion': 34, 'weather': 18}

clients = set()


def predict(train, s):
    route = train['route']
    i = min(s['segment'], len(route)-1)
    current = route[i]
    next_stop = route[min(i+1, len(route)-1)]
    remaining_km = max(1, (next_stop[3] - current[3]) * 1.0 * (1-s['progress']) + 5)
    congestion = s['congestion']
    weather = s['weather']
    dwell = 2.5
    # Transparent demo predictor: speed + delay + congestion + weather + dwell.
    speed_factor = max(0.62, 1 - congestion/300 - weather/500)
    travel_hours = remaining_km / (train['speed'] * speed_factor)
    eta_min = max(1, round(travel_hours * 60 + s['delay'] + dwell))
    confidence = max(72, min(98, round(96 - congestion*0.08 - weather*0.05 - abs(s['delay'])*0.12)))
    reasons = []
    if s['delay'] >= 8: reasons.append('Current delay is propagating')
    if congestion >= 55: reasons.append('High route congestion')
    elif congestion >= 35: reasons.append('Moderate route congestion')
    if weather >= 45: reasons.append('Weather impact detected')
    if not reasons: reasons.append('Normal operating conditions')
    return eta_min, confidence, reasons, current, next_stop


def snapshot(train_no):
    train = TRAINS[train_no]
    s = state[train_no]
    eta_min, confidence, reasons, current, next_stop = predict(train, s)
    now = datetime.now(timezone.utc)
    eta = now + timedelta(minutes=eta_min)
    return {
        'number': train['number'], 'name': train['name'], 'from': train['from'], 'to': train['to'],
        'current': current[0], 'next': next_stop[0], 'lat': current[1] + (next_stop[1]-current[1])*s['progress'],
        'lng': current[2] + (next_stop[2]-current[2])*s['progress'], 'delay': s['delay'],
        'congestion': s['congestion'], 'weather': s['weather'], 'etaMinutes': eta_min,
        'eta': eta.isoformat(), 'confidence': confidence, 'reasons': reasons,
        'route': [{'name': n, 'lat': lat, 'lng': lng, 'km': km} for n,lat,lng,km in train['route']]
    }


@app.get('/')
def home():
    return FileResponse(BASE / 'static' / 'index.html')

@app.get('/api/trains')
def trains():
    return [snapshot(n) for n in TRAINS]

@app.get('/api/trains/{train_no}')
def train(train_no: str):
    if train_no not in TRAINS:
        return {'error': 'Train not found'}
    return snapshot(train_no)

@app.get('/api/health')
def health():
    return {'status':'ok', 'service':'RailCast', 'time':datetime.now(timezone.utc).isoformat()}

@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    await ws.accept(); clients.add(ws)
    try:
        while True:
            await asyncio.sleep(5)
            for n, t in TRAINS.items():
                s = state[n]
                s['progress'] += 0.035 + random.random()*0.025
                if s['progress'] >= 1:
                    s['segment'] = min(s['segment']+1, len(t['route'])-2)
                    s['progress'] = 0.03
                    s['delay'] = max(0, s['delay'] + random.choice([-2,-1,0,1,2]))
                s['congestion'] = max(10, min(85, s['congestion'] + random.choice([-5,-2,0,2,5])))
                s['weather'] = max(5, min(70, s['weather'] + random.choice([-3,0,2])))
            payload = {'type':'update','timestamp':datetime.now(timezone.utc).isoformat(),'trains':[snapshot(n) for n in TRAINS]}
            dead=[]
            for c in clients:
                try: await c.send_json(payload)
                except Exception: dead.append(c)
            for c in dead: clients.discard(c)
    except WebSocketDisconnect:
        clients.discard(ws)
