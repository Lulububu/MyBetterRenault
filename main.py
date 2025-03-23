from flask import Flask, render_template, request, redirect, url_for, flash, session
from renault_api.renault_client import RenaultClient
from aiohttp import ClientSession
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

async def get_client_and_vehicle(vin):
    """Helper function to get client and account ID"""
    websession = ClientSession()
    try:
    
        
        
        client = RenaultClient(websession=websession, locale="fr_FR")
        await client.session.login(session['username'], session['password'])
        account = await client.get_api_account(session['account_id'])
        vehicle = await account.get_api_vehicle(vin)
        return client, vehicle, websession
    except Exception as e:
        await websession.close()
        raise e

@app.route('/')
def index():
    # if 'logged_in' in session:
    #     return redirect(url_for('dashboard'))
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

            person = await client.get_person();
            myrenault_account = next((account for account in person.accounts if account.accountType == "MYRENAULT"), None)

            session['account_id'] = myrenault_account.accountId
           
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
async def dashboard():
    try:
        async with ClientSession() as websession:
            client = RenaultClient(websession=websession, locale="fr_FR")
            await client.session.login(session['username'], session['password'])
            
            account = await client.get_api_account(session['account_id'])
            vehicles = await account.get_vehicles()
           
            return render_template('dashboard.html', vehicles=vehicles.vehicleLinks)
    except Exception as e:
        flash(f'Erreur lors de la récupération des véhicules: {str(e)}', 'error')
        print(f"Erreur: {str(e)}")
        return str(e)
        # return redirect(url_for('index'))

@app.route('/vehicle/<vin>/status')
async def vehicle_status(vin):
    try:
        client, vehicle, websession = await get_client_and_vehicle(vin)
            
        battery_status = await vehicle.get_battery_status()
        location = await vehicle.get_location()
        
        return render_template('vehicle_status.html', 
                            vin=vin, 
                            battery_status=battery_status,
                            location=location)
    except Exception as e:
        flash(f'Erreur: {str(e)}', 'error')
        return 'ohh'
        # return redirect(url_for('dashboard'))


@app.route('/vehicle/<vin>/charging', methods=['GET', 'POST'])
async def vehicle_charging(vin):
    try:
        client, vehicle, websession = await get_client_and_vehicle(vin)
        
        if request.method == 'POST':
            action = request.form.get('action')
            try:
                if action == 'start':
                    await vehicle.set_charge_start()
                    flash('Démarrage de la charge...', 'success')
                elif action == 'stop':
                    await vehicle.set_charge_stop()
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
