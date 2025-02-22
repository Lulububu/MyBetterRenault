from flask import Flask, render_template, request, redirect, url_for, flash, session
from renault_api.renault_client import RenaultClient
import aiohttp
from aiohttp import ClientSession
import asyncio
from dotenv import load_dotenv
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
load_dotenv()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

async def get_client_and_account():
    """Helper function to get client and account ID"""
    async with ClientSession() as websession:
        client = RenaultClient(websession=websession, locale='fr_FR')
        await client.session.login(session['username'], session['password'])
        person = await client.get_person()
        accounts = await person.get_accounts()
        return client, accounts[0]

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
async def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Veuillez remplir tous les champs', 'error')
        return redirect(url_for('index'))
    
    try:
        async with ClientSession() as websession:
            client = RenaultClient(websession=websession, locale='fr_FR')
            await client.session.login(username, password)
            print(f"Accounts: {await client.get_api_accounts()}")
            # Test connection by getting person info
            await client.get_person()
           
            session['logged_in'] = True
            session['username'] = username
            session['password'] = password
            flash('Connexion réussie!', 'success')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Erreur de connexion: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
async def dashboard():
    try:
        client, account_id = await get_client_and_account()
        vehicles = await client.get_vehicles(account_id)
        return render_template('dashboard.html', vehicles=vehicles)
    except Exception as e:
        flash(f'Erreur lors de la récupération des véhicules: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/vehicle/<vin>/status')
@login_required
async def vehicle_status(vin):
    try:
        client, account_id = await get_client_and_account()
        vehicle = await client.get_vehicle(account_id, vin)
        
        battery_status = await vehicle.get_battery_status()
        location = await vehicle.get_location()
        
        return render_template('vehicle_status.html', 
                            vin=vin, 
                            battery_status=battery_status,
                            location=location)
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/vehicle/<vin>/location')
@login_required
async def vehicle_location(vin):
    try:
        client, account_id = await get_client_and_account()
        vehicle = await client.get_vehicle(account_id, vin)
        location = await vehicle.get_location()
        
        if location:
            return render_template('vehicle_location.html', 
                                vin=vin, 
                                location=location)
        flash('Position du véhicule non disponible', 'error')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/vehicle/<vin>/charging', methods=['GET', 'POST'])
@login_required
async def vehicle_charging(vin):
    try:
        client, account_id = await get_client_and_account()
        vehicle = await client.get_vehicle(account_id, vin)
        
        if request.method == 'POST':
            action = request.form.get('action')
            try:
                if action == 'start':
                    await vehicle.charge_start()
                    flash('Démarrage de la charge...', 'success')
                elif action == 'stop':
                    await vehicle.charge_stop()
                    flash('Arrêt de la charge...', 'success')
            except Exception as e:
                flash(f'Erreur lors de la commande de charge: {str(e)}', 'error')
        
        battery_status = await vehicle.get_battery_status()
        charging_settings = await vehicle.get_charging_settings()
        
        return render_template('vehicle_charging.html',
                            vin=vin,
                            battery_status=battery_status,
                            charging_settings=charging_settings)
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)