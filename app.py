import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import re

from helpers import apology, login_required, lookup, usd

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False             #Indica que la sesión no será permanente (se borra al cerrar el navegador)
app.config["SESSION_TYPE"] = "filesystem"              #Almacena la sesión en archivos locales (en el proyecto) en lugar de usar cookies.
Session(app)                                        # Aplica la configuración de sesiones al proyecto.

db = SQL("sqlite:///finance.db")


@app.after_request                  # Indica que esta función se ejecutará después de cada solicitud al servidor.
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0                                                     # evita todo tipo de cache asi tenga que reiniciar la pagina
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
def buy():
    if request.method == "POST":
        query = request.form.get("query").strip().lower()
        matching_games = []

        for category, games_list in games.items():
            for game in games_list:
                if re.search(query, game["name"], re.IGNORECASE):
                    matching_games.append(game)

        return render_template("buy.html", games=matching_games)

    # Si es GET, muestra todos los juegos
    all_games = [game for games_list in games.values() for game in games_list]
    return render_template("buy.html", games=all_games)


@app.route("/history", methods=["GET", "POST"])          #todo esto se ejecuta cuando este en la pagina de history
@login_required                 #necesita estar autentificado
def history():
    """Show user's transaction history."""
    user_id = session["user_id"]        # obtiene el user_id con la cuenta logeada

    # Ejecuta una consulta SQL para obtener solo las transacciones del usuario logeado, ordenadas por fecha de la más reciente a la más antigua.
    if request.method == "POST":
        user_cpu = request.form.get("cpu")
        user_gpu = request.form.get("gpu")
        user_ram = request.form.get("ram")
        compatible_games = []

        for category, games_list in games.items():
            for game in games_list:
                if (
                    user_cpu == game["cpu"] or is_higher_cpu(user_cpu, game["cpu"])
                ) and (
                    user_gpu == game["gpu"] or is_higher_gpu(user_gpu, game["gpu"])
                ) and int(user_ram) >= int(game["ram"]):
                    compatible_games.append(game)

        return render_template("history.html", compatible_games=compatible_games)

    return render_template("history.html", compatible_games=None)     # si hay transacciones simplemente pasa la lista


@app.route("/login", methods=["GET", "POST"]) #todo esto se ejecuta cuando este en la pagina de login
def login():
    """Log user in"""
    session.clear()
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):    # len !1 solo tiene que haber un usuario con ese nombre / check_password_hash funcion predefinida para comparar en este caso rows que es la contrasena encriptada y hash que es la contrasena que acaba de poner el usuario
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]      # autentidica y inicia sesion
        return redirect("/")                # una vez autenticado lo envia a la pagina principal
    else:
        return render_template("login.html")    # muestra el formulario para iniciar sesion


@app.route("/logout")
def logout():
    """Log user out"""
    session.clear()
    return redirect("/")



@app.route("/register", methods=["GET", "POST"])        #todo esto se ejecuta cuando este en la pagina de register
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")             # obtiene datos de el usuario
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:                                        # si no ingresa un nombre marca error
            return apology("must provide username", 400)

        if not password or not confirmation:                    # si no ingresa la contrasena o la confirmacion marca error
            return apology("must provide password", 400)

        if password != confirmation:                            # si la contrasena no es igual a la confirmacion marca error
            return apology("passwords must match", 400)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                       username, generate_password_hash(password))                  # guarda la contrasena en el lugar correspondiente
        except ValueError:                                                          # si el usuario ya ha sido registrado marca error   lo de antes el !=
            return apology("username already exists", 400)

        return redirect("/login")           # al registrarse redirige a login

    return render_template("register.html")         # si el usuario solo visita la pagina muestra el formulario de registro



@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")                 # obtiene los datos
        confirmation = request.form.get("confirmation")

        if not current_password or not new_password or not confirmation:        # si alguno de los datos estan vacios marca error
            return apology("All fields are required.", 400)

        if new_password != confirmation:                                        # si la nueva contrasena es diferente de la confirmacion amrca error
            return apology("New passwords must match.", 400)

        user_id = session["user_id"]                # identifica aal usuario
        rows = db.execute("SELECT hash FROM users WHERE id = ?", user_id)           # consulta la contrasena de la base de datos

        if not check_password_hash(rows[0]["hash"], current_password):              # compara ambas contrasenas si no son iguales marca error
            return apology("Current password is incorrect.", 403)

        db.execute("UPDATE users SET hash = ? WHERE id = ?",
                   generate_password_hash(new_password), user_id)                   # actualiza la nueva contrasena

        flash("Password changed successfully!")             # si todo sale bien marca exito
        return redirect("/")                                # redirige a la pagina principal

    return render_template("change_password.html")          # si el usuario entra a la pagina sin enviar el formulario simplemente lo muestra



#recuerda antes de ejecutar crear la tabla de las transacciones

games = {
    "Bajo": [
        {"name": "Minecraft", "cpu": "AMD Athlon II", "gpu": "Nvidia GeForce 9600 GT", "ram": "2", "image": "minecraft.jpg"},
        {"name": "Stardew Valley", "cpu": "Intel Core i3", "gpu": "256 MB de vRAM", "ram": "2", "image": "SV.png"},
        {"name": "Far Cry", "cpu": "AMD Athlon II", "gpu": "256 MB of vRAM", "ram": "1", "image": "2.jpg"},
        {"name": "Far Cry 2", "cpu": "AMD Athlon 64", "gpu": "256 MB of vRAM", "ram": "1", "image": "3.jpg"},
        {"name": "GTA: San Andreas", "cpu": "AMD Athlon Processor", "gpu": "64 MB of vRAM", "ram": "1", "image": "GTASA.jpg"},
        {"name": "Assassin's Creed", "cpu": "AMD Athlon 64", "gpu": "256 MB of vRAM", "ram": "2", "image": "AC1.png"},
        {"name": "Assassin's Creed II", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "2", "image": "AC2.jpg"},
        {"name": "Assassin's Creed: Brotherhood", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "2", "image": "ACB.jpg"},
        {"name": "Assassin's Creed: Revelations", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "2", "image": "ASR.jpg"},
        {"name": "Assassin's Creed III", "cpu": "Intel Core 2 Duo", "gpu": "512 MB of vRAM", "ram": "4", "image": "a1.jpg"},
        {"name": "Assassin's Creed IV: Black Flag Jackdaw Edition", "cpu": "AMD Athlon II X4 620 2.6 GHz", "gpu": "Nvidia Geforce GTX 260", "ram": "4", "image": "a2.jpg"},
        {"name": "Assassin's Creed: Rogue", "cpu": "AMD Athlon II X4 620 2.6 GHz", "gpu": "Nvidia Geforce GTX 260", "ram": "4", "image": "a3.jpg"},
        {"name": "Shadow Warrior", "cpu": "2.4 GHz Dual Core Processor", "gpu": "ATI Radeon HD 3870", "ram": "2", "image": "a5.jpg"},
        {"name": "Blasphemous", "cpu": "Intel Core2 Duo E8400", "gpu": "Nvidia Geforce GTX 260", "ram": "4", "image": "B1.jpg"},
        {"name": "Far Cry 3", "cpu": "AMD Athlon 64", "gpu": "1 GB of vRAM", "ram": "4", "image": "FC3.jpg"},
        {"name": "Call of Duty", "cpu": "Intel Pentium III", "gpu": "32 MB compatible con DirectX 9.0b", "ram": "1", "image": "CA1.jpg"},
        {"name": "Call of Duty 2", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce FX 5200", "ram": "1", "image": "CA2.png"},
        {"name": "Call of Duty: Modern Warfare 2", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce 6600GT", "ram": "1", "image": "a6.jpg"},
        {"name": "Call of Duty: Modern Warfare 3", "cpu": "Intel Core 2 Duo E6600", "gpu": "NVIDIA GeForce 8600GT", "ram": "2", "image": "a7.jpg"},
        {"name": "Call of Duty: Modern Warfare 4", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce 6600GT", "ram": "1", "image": "CAM4.png"},
        {"name": "Call of Duty: World at War", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce 6600GT", "ram": "1", "image": "CAWW.png"},
        {"name": "Call of Duty: Black Ops", "cpu": "Intel Core 2 Duo E6600", "gpu": "NVIDIA GeForce 8600GT", "ram": "2", "image": "CABO1.jpg"},
        {"name": "Call of Duty: Black Ops II", "cpu": "Intel Core 2 Duo E8200", "gpu": "NVIDIA GeForce 8800GT", "ram": "4", "image": "a8.jpg"},
        {"name": "Fable: The Lost Chapters", "cpu": "1.4 GHz", "gpu": "64 MB of vRAM", "ram": "1", "image": "F1.jpg"},
        {"name": "Fable Anniversary", "cpu": "Intel Core 2 Duo", "gpu": "NVIDIA GeForce 7600GT", "ram": "3", "image": "FA.jpg"},
        {"name": "Max Payne", "cpu": "Intel Pentium III", "gpu": "Aceleradora 3D 16 MB (DirectX 8.0)", "ram": "1", "image": "MP.jpg"},
        {"name": "Prince of Persia: The Sands of Time", "cpu": "AMD Athlon 64", "gpu": "256 MB compatible con DirectX 9.0b", "ram": "1", "image": "POP.jpg"},
        {"name": "Diablo II", "cpu": "1 GHZ", "gpu": "Tarjeta DirectX con resolución de 800 x 600", "ram": "1", "image": "D2.png"},
        {"name": "StarCraft", "cpu": "Pentium 90", "gpu": "SVGA", "ram": "1", "image": "ST.jpg"},
        {"name": "Warcraft III", "cpu": "Pentium II", "gpu": "8 MB of vRAM", "ram": "1", "image": "WC3.jpg"},
        {"name": "Command & Conquer: Red Alert 2", "cpu": "Pentium II", "gpu": "2 MB of vRAM", "ram": "1", "image": "CYC2.jpg"},
        {"name": "Quake III Arena", "cpu": "Pentium", "gpu": "4 MB of vRAM", "ram": "1", "image": "QA3.jpg"},
        {"name": "Half-Life", "cpu": "Pentium", "gpu": "Intel HD 3000", "ram": "1", "image": "HL.png"},
        {"name": "The Elder Scrolls III: Morrowind", "cpu": "Pentium III", "gpu": "32 MB of vRAM", "ram": "1", "image": "ES3.jpg"},
        {"name": "Baldur's Gate I", "cpu": "Intel Dual Core", "gpu": "OpenGL 2.0 compatible", "ram": "1", "image": "a9.jpg"},
        {"name": "Baldur's Gate II", "cpu": "Intel Dual Core", "gpu": "OpenGL 2.0 compatible", "ram": "1", "image": "BG2.jpg"},
        {"name": "Heroes of Might and Magic III", "cpu": "AMD Athlon64 X2", "gpu": "NVIDIA GeForce 8600GT", "ram": "2", "image": "HOM3.jpg"},
        {"name": "Silent Hill 2", "cpu": "Intel Pentium III", "gpu": "32 MB of vRAM", "ram": "1", "image": "SH2.jpg"},
        {"name": "Thief II: The Metal Age", "cpu": "1.8 GHZ", "gpu": "Gráfica 3D compatible con DirectX 7", "ram": "1", "image": "1.jpg"},
        {"name": "Fallout", "cpu": "Pentium 90", "gpu": "SVGA", "ram": "1", "image": "F11.jpg"},
        {"name": "Fallout 2", "cpu": "Intel Pentium 4", "gpu": "Nvidia GeForce 6100", "ram": "1", "image": "F2.jpg"},
        {"name": "Resident Evil 1", "cpu": "Intel Core 2 Duo", "gpu": "Nvidia Geforce GTX 260", "ram": "2", "image": "4.jpg"},
        {"name": "Resident Evil 2", "cpu": "Intel Core i3", "gpu": "Intel HD 3000", "ram": "2", "image": "5.jpg"},
        {"name": "Resident Evil: Revelations 2", "cpu": "Intel Core 2 Duo E6700", "gpu": "NVIDIA GeForce 8800 GT", "ram": "2", "image": "a10.jpg"},
        {"name": "Resident Evil 3: Nemesis", "cpu": "Pentium200MHz", "gpu": "Gráfica 3D compatible con DirectX 7", "ram": "1", "image": "6.jpg"},
        {"name": "Resident Evil 4", "cpu": "Intel Core 2 Duo", "gpu": "NVIDIA GeForce 8600GT", "ram": "2", "image": "7.jpg"},
        {"name": "Resident Evil 5", "cpu": "Intel Core 2 Quad", "gpu": "NVIDIA GeForce 9800", "ram": "4", "image": "8.jpg"},
        {"name": "Resident Evil 6", "cpu": "Intel CoreTM2 Duo", "gpu": "NVIDIA GeForce 8800GTS", "ram": "2", "image": "9.jpg"},
        {"name": "League of Legends", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce 9600GT", "ram": "2", "image": "11.jpg"},
        {"name": "Terraria", "cpu": "1.6 GHZ", "gpu": "128 MB of vRAM", "ram": "1", "image": "13.jpg"},
        {"name": "Hotline Miami", "cpu": "1.2 GHZ", "gpu": "32 MB of vRAM", "ram": "1", "image": "14.jpg"},
        {"name": "Celeste", "cpu": "Intel Core i3", "gpu": "Intel HD 4000", "ram": "2", "image": "15.jpg"},
        {"name": "FTL: Faster Than Light", "cpu": "Intel 2.0 GHZ", "gpu": "128 MB of vRAM", "ram": "1", "image": "16.jpg"},
        {"name": "Don't Starve", "cpu": "1.7 GHZ", "gpu": "Radeon HD5450", "ram": "1", "image": "17.jpg"},
        {"name": "Undertale", "cpu": "Windows XP", "gpu": "128 MB of vRAM", "ram": "2", "image": "18.jpg"},
        {"name": "Papers, Please", "cpu": "Intel Core 2 Duo", "gpu": "OpenGL 1.4", "ram": "2", "image": "19.jpg"},
        {"name": "Super Meat Boy", "cpu": "1.4 GHZ", "gpu": "Pixel Shader 3.0", "ram": "1", "image": "20.jpg"},
        {"name": "The Binding of Isaac: Rebirth", "cpu": "Intel Core 2 Duo", "gpu": "Discreet video card", "ram": "2", "image": "21.jpg"},
        {"name": "Hotline Miami 2", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "1", "image": "22.jpg"},
        {"name": "Braid", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce GTX 660", "ram": "4", "image": "24.jpg"},
        {"name": "Limbo", "cpu": "Intel 2.0 GHZ", "gpu": "Shader Model 3.0", "ram": "1", "image": "25.jpg"},
        {"name": "Rocket League", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce 8800", "ram": "4", "image": "27.jpg"},
        {"name": "Dota 2", "cpu": "AMD at 2.8 GHz", "gpu": "NVIDIA GeForce 8600", "ram": "4", "image": "28.jpg"},
        {"name": "World of Warcraft", "cpu": "Intel Core 2 Duo E6600", "gpu": "NVIDIA GeForce 8800GT", "ram": "2", "image": "29.jpg"},
        {"name": "Counter-Strike: Global Offensive", "cpu": "Intel Core 2 Duo E6600", "gpu": "256 MB of vRAM", "ram": "2", "image": "30.jpg"},
        {"name": "Age of Empires II", "cpu": "Intel Core 2 Duo", "gpu": "NVIDIA GeForce GT 420", "ram": "4", "image": "32.jpg"},
        {"name": "SimCity 4", "cpu": "Intel Pentium III", "gpu": "32 MB of vRAM", "ram": "1", "image": "33.jpg"},
        {"name": "Devil May Cry HD Collection", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 760", "ram": "4", "image": "34.jpg"},
        {"name": "Devil May Cry 3 Special Edition", "cpu": "Intel Pentium III", "gpu": "256 MB VRAM", "ram": "1", "image": "35.jpg"},
        {"name": "Devil May Cry 4: Special Edition", "cpu": "Intel Core 2 Duo", "gpu": "NVIDIA GeForce 8800 GTS", "ram": "2", "image": "36.jpg"},
        {"name": "Northgard The Viking Age Edition", "cpu": "Intel Core 2 Duo", "gpu": "Nvidia GTS 260", "ram": "1", "image": "38.jpg"},
        {"name": "Amnesia Videogame Collection", "cpu": "Intel 2.0 GHZ", "gpu": "Radeon X1000", "ram": "2", "image": "39.jpg"},
        {"name": "The Witcher: Enhanced Edition Director's Cut", "cpu": "Intel Pentium 4", "gpu": "GeForce 7800 GTX", "ram": "2", "image": "40.jpg"},
        {"name": "The Witcher 2: Assassins of Kings Enhanced Editon", "cpu": "Intel Dual Core", "gpu": "NVIDIA GeForce 8800", "ram": "2", "image": "41.jpg"},
        {"name": "Gears of War", "cpu": "2.4 GHZ", "gpu": "NVIDIA GeForce 6600", "ram": "1", "image": "42.jpg"},
        {"name": "Hollow Knight", "cpu": "Intel Core 2 Duo E5200", "gpu": "NVIDIA GeForce 9800GTX", "ram": "4", "image": "43.jpg"},
        {"name": "Cuphead", "cpu": "Intel Core i3", "gpu": "Intel HD 4000", "ram": "4", "image": "44.jpg"},
        {"name": "Portal", "cpu": "1.7 GHZ", "gpu": " DirectX® 8.1 compatible graphics card", "ram": "1", "image": "45.jpg"},
        {"name": "Portal 2", "cpu": "3.0 GHZ", "gpu": "NVIDIA GeForce 7600", "ram": "2", "image": "46.jpg"},
        {"name": "Left 4 Dead", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce 6600", "ram": "1", "image": "47.jpg"},
        {"name": "Left 4 Dead 2", "cpu": "Intel Pentium 4", "gpu": "NVIDIA GeForce 6600", "ram": "2", "image": "48.jpg"},
        {"name": "Dark Souls: Prepare to Die Edition", "cpu": "Intel Core 2 Duo E6850", "gpu": "NVIDIA GeForce 9800GTX", "ram": "2", "image": "49.jpg"},
        {"name": "Dark Souls II", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce GTX 465", "ram": "4", "image": "50.jpg"},
        {"name": "Dead Cells", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce 450 GTS", "ram": "2", "image": "53.jpg"},
        {"name": "Risk of Rain 2", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 580", "ram": "4", "image": "55.jpg"},
        {"name": "Torchlight", "cpu": "x86 compatible processor at 800 MHz", "gpu": "64 MB of vRAM", "ram": "1", "image": "56.jpg"},
        {"name": "Torchlight II", "cpu": "1.4 GHZ", "gpu": "256 MB of vRAM", "ram": "1", "image": "57.jpg"},
        {"name": "Bastion", "cpu": "1.7 GHZ", "gpu": "512 MB of vRAM", "ram": "2", "image": "58.jpg"},
        {"name": "Slay the Spire", "cpu": "Intel 2.0 GHZ", "gpu": "256 MB of vRAM", "ram": "4", "image": "59.jpg"},
        {"name": "Ori and the Blind Forest", "cpu": "Intel Core 2 Duo E4500", "gpu": "GeForce 240 GT", "ram": "4", "image": "60.jpg"},
        {"name": "Shovel Knight", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "2", "image": "62.jpg"},
        {"name": "Gris", "cpu": "Intel Core 2 Duo E6750", "gpu": "Geforce GT 430", "ram": "4", "image": "64.jpg"},
        {"name": "Fez", "cpu": "Intel Core 2 Duo", "gpu": "OpenGL 3.0 Support", "ram": "2", "image": "65.jpg"},
        {"name": "Oxenfree", "cpu": "Intel Core i3", "gpu": "1 GB of vRAM", "ram": "2", "image": "66.jpg"},
        {"name": "Crypt of the NecroDancer", "cpu": "Intel 2.0 GHZ", "gpu": "512 MB of vRAM", "ram": "1", "image": "67.jpg"},
        {"name": "Castle Crashers", "cpu": "Intel Core 2 Duo", "gpu": "256 MB of vRAM", "ram": "1", "image": "68.jpg"},
        {"name": "Katana ZERO", "cpu": "Intel Pentium E2180", "gpu": "NVIDIA GeForce 7600GT", "ram": "1", "image": "69.jpg"},
        {"name": "Moonlighter", "cpu": "Intel Core 2 Quad", "gpu": "Nvidia Geforce GTX 260", "ram": "4", "image": "70.jpg"},
        {"name": "Mortal Kombat: Komplete Edition", "cpu": "Intel Core 2 Duo", "gpu": "NVIDIA GeForce 8800 GTS", "ram": "2", "image": "a11.jpg"},
        {"name": "Battlefield: Bad Company 2", "cpu": "Intel Core 2 Duo", "gpu": "NIDIA GeForce 7800 GT", "ram": "2", "image": "a12.jpg"},
        {"name": "Battlefield 3", "cpu": "Intel Core 2 Duo", "gpu": "512 MB of vRAM", "ram": "2", "image": "a13.jpg"},
        {"name": "Battlefield 4", "cpu": "Intel 2 Core Duo", "gpu": "NVIDIA GeForce 8800GT", "ram": "4", "image": "a14.jpg"},
        {"name": "Alan Wake", "cpu": "Intel Core 2 Duo", "gpu": "512 MB of vRAM", "ram": "2", "image": "a15.jpg"},
        {"name": "Tomb Raider", "cpu": "Intel Core 2 Duo", "gpu": "512 MB of vRAM", "ram": "2", "image": "b1.jpg"},
        {"name": "Grand Theft Auto V", "cpu": "Intel Core 2 Quad", "gpu": "NVIDIA GeForce 9800 GT", "ram": "4", "image": "a28.jpg"},



    ],
    "Medio": [
        {"name": "Hyper Light Drifter", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX Vega 6", "ram": "8", "image": "63.jpg"},
        {"name": "Devil May Cry 5 Deluxe Edition", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "37.jpg"},
        {"name": "Mortal Kombat XL", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 460", "ram": "4", "image": "a16.jpg"},
        {"name": "Mortal Kombat 11", "cpu": "Intel Core i5", "gpu": "GeForce GTX 1050", "ram": "8", "image": "a17.jpg"},
        {"name": "Far Cry 5", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 670", "ram": "8", "image": "a18.jpg"},
        {"name": "Cyberpunk 2077", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 780", "ram": "8", "image": "a19.jpg"},
        {"name": "Dark Souls III", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 750 Ti", "ram": "8", "image": "a20.jpg"},
        {"name": "Sekiro: Shadows Die Twice", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a21.jpg"},
        {"name": "Fortnite", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1050", "ram": "8", "image": "a22.jpg"},
        {"name": "Apex Legends", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 970", "ram": "8", "image": "a23.jpg"},
        {"name": "Tom Clancy's Rainbow Six Siege", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce GTX 460", "ram": "6", "image": "a24.jpg"},
        {"name": "Overwatch", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 600", "ram": "6", "image": "a25.jpg"},
        {"name": "PUBG", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a26.jpg"},
        {"name": "Battlefield V", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1050", "ram": "8", "image": "a27.jpg"},
        {"name": "Destiny 2", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce GTX 660", "ram": "6", "image": "a29.jpg"},
        {"name": "Borderlands 3", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 680", "ram": "6", "image": "a32.jpg"},
        {"name": "The Witcher 3: Wild Hunt", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "6", "image": "a35.jpg"},
        {"name": "Horizon Zero Dawn", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 780", "ram": "8", "image": "a36.jpg"},
        {"name": "Watch Dogs", "cpu": "AMD Phenom II X4 940", "gpu": "NVIDIA GeForce GTX 460", "ram": "6", "image": "307.jpg"},
        {"name": "Watch Dogs 2", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "8", "image": "306.jpg"},
        {"name": "Need for Speed Heat", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a37.jpg"},
        {"name": "Assassin's Creed Unity", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 680", "ram": "6", "image": "a38.jpg"},
        {"name": "Assassin's Creed Syndicate", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "6", "image": "a39.jpg"},
        {"name": "Assassin's Creed Origins", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "6", "image": "a40.jpg"},
        {"name": "Assassin's Creed Odyssey", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "8", "image": "a42.jpg"},
        {"name": "Assassin's Creed Valhalla", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 960", "ram": "16", "image": "a43.jpg"},
        {"name": "Assassin's Creed Mirage Master Assassin Edition", "cpu": "Intel Core i7", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "a44.jpg"},
        {"name": "Call of Duty: Warzone", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "a45.jpg"},
        {"name": "Call of Duty MW", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1650", "ram": "8", "image": "a46.jpg"},
        {"name": "Call of Duty: Cold War", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1650", "ram": "8", "image": "a47.jpg"},
        {"name": "Call of Duty: Black Ops III", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 470", "ram": "6", "image": "a48.jpg"},
        {"name": "Final Fantasy VII Remake: Intergrade", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 780", "ram": "8", "image": "a49.jpg"},
        {"name": "Crisis Core: Final Fantasy VII Reunion", "cpu": "Intel Core i3", "gpu": "AMD Radeon RX 460", "ram": "8", "image": "a50.jpg"},
        {"name": "Final Fantasy XV", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a51.jpg"},
        {"name": "Metro Exodus", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1050", "ram": "8", "image": "a33.jpg"},
        {"name": "Red Dead Redemption", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 580", "ram": "8", "image": "q1.jpg"},
        {"name": "Red Dead Redemption 2", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "a53.jpg"},
        {"name": "Gears Of War 4", "cpu": "Intel Core i5", "gpu": "GeForce 750 Ti", "ram": "8", "image": "a52.jpg"},
        {"name": "Gears 5", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a54.jpg"},
        {"name": "Dragon Age: Inquisition", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce 8800GT", "ram": "8", "image": "a55.jpg"},
        {"name": "Fallout 76", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 780", "ram": "8", "image": "a56.jpg"},
        {"name": "Battlefield 1", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "8", "image": "a57.jpg"},
        {"name": "Control", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 780", "ram": "8", "image": "a59.jpg"},
        {"name": "DOOM Eternal", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "a60.jpg"},
        {"name": "Resident Evil Village", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 560", "ram": "8", "image": "a61.jpg"},
        {"name": "Resident Evil 2 (2019)", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a62.jpg"},
        {"name": "Resident Evil 3 (2020)", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 760", "ram": "8", "image": "a63.jpg"},
        {"name": "Resident Evil 4 Remake", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 560", "ram": "8", "image": "a64.jpg"},
        {"name": "Prince of Persia: The Lost Crown", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 970", "ram": "8", "image": "a65.jpg"},
        {"name": "Uncharted 4: Legacy of Thieves Collection", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a66.jpg"},
        {"name": "Marvel’s Spider-Man: Miles Morales", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a67.jpg"},
        {"name": "Marvel's Spider-Man Remastered", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a68.jpg"},
        {"name": "God of War", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a69.jpg"},
        {"name": "God of War Ragnarok", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "a70.jpg"},
        {"name": "Baldur's Gate III", "cpu": "Intel Core i5", "gpu": "Nvidia GTX 970", "ram": "8", "image": "a71.jpg"},
        {"name": "Shadow Warrior 2", "cpu": "Intel Core i3", "gpu": "GeForce GT 560 Ti", "ram": "8", "image": "a72.jpg"},
        {"name": "Shadow Warrior 3", "cpu": "Intel Core i5", "gpu": "GeForce GTX 760", "ram": "8", "image": "a73.jpg"},
        {"name": "Ghost of Tsushima Directors Cut", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 960", "ram": "8", "image": "a74.jpg"},
        {"name": "Halo The Master Chief Collection", "cpu": "Intel Core i3", "gpu": "NVIDIA GeForce GTS 450", "ram": "8", "image": "a75.jpg"},
        {"name": "Shadow of the Tomb Raider", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 660", "ram": "8", "image": "a31.jpg"},
        {"name": "Rise of the Tomb Raider: 20 Year Celebration", "cpu": "Intel Core i3", "gpu": "NVIDIA GTX 650", "ram": "6", "image": "b2.jpg"},
        {"name": "Halo Infinite", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 1050 Ti", "ram": "8", "image": "b3.jpg"},
        {"name": "Marvels Guardians of the Galaxy", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1060", "ram": "8", "image": "b4.jpg"},
        {"name": "Middle Earth: Shadow of War", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX GTX 660", "ram": "8", "image": "b5.jpg"},
        {"name": "Middle Earth: Shadow of Mordor", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 460", "ram": "4", "image": "b6.jpg"},
        {"name": "The Elder Scrolls V: Skyrim", "cpu": "Intel Core i5", "gpu": "Nvidia GTX 470", "ram": "8", "image": "b7.jpg"},

    ],
    "Alto": [
        {"name": "Lords of the Fallen", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 590", "ram": "12", "image": "lod.jpg"},
        {"name": "Elden Ring", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 580", "ram": "12", "image": "b8.jpg"},
        {"name": "Hogwarts Legacy", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 960", "ram": "16", "image": "b9.jpg"},
        {"name": "Avatar: Frontiers of Pandora", "cpu": "Intel Core i7", "gpu": "NVIDIA GTX 1070", "ram": "16", "image": "b10.jpg"},
        {"name": "Ghostwire Tokyo Deluxe Edition", "cpu": "Intel Core i7", "gpu": "NVIDIA GTX 1060", "ram": "12", "image": "a76.jpg"},
        {"name": "Indiana Jones and the Great Circle Premium", "cpu": "Intel Core i7", "gpu": "NVIDIA RTX 2060 Super", "ram": "16", "image": "a77.jpg"},
        {"name": "Silent Hill 2 Remake Deluxe Edition", "cpu": "Intel Core i7", "gpu": "NVIDIA GeForce GTX 1070 Ti", "ram": "16", "image": "a78.jpg"},
        {"name": "Horizon Zero Dawn Remastered", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 1650", "ram": "16", "image": "a79.jpg"},
        {"name": "Horizon Forbidden West", "cpu": "Intel Core i5", "gpu": "NVIDIA GeForce GTX 1650", "ram": "16", "image": "a80.jpg"},
        {"name": "Black Myth: Wukong", "cpu": "Intel Core i5", "gpu": "AMD Radeon RX 580", "ram": "16", "image": "a81.jpg"},
        {"name": "Alan Wake 2", "cpu": "Intel Core i5", "gpu": "NVIDIA RTX 2060", "ram": "16", "image": "a82.jpg"},
        {"name": "Dragons Dogma 2 PC", "cpu": "Intel Core i5", "gpu": "NVIDIA GTX 1070", "ram": "16", "image": "dd2.jpg"},

    ],
    "Ultra": [

    ],
}

def is_higher_cpu(user_cpu, game_cpu):
    cpu_hierarchy = {
        "Pentium 90": 1,
        "Pentium200MHz": 2,
        "1 GHZ": 4,
        "1.2 GHZ": 5,
        "1.4 GHZ": 7,
        "1.6 GHZ": 8,
        "1.7 GHZ": 9,
        "1.8 GHZ": 10,
        "Intel 2.0 GHZ": 11,
        "AMD at 2.8 GHz": 12,
        "2.4 GHZ": 13,
        "3.0 GHZ": 14,
        "Pentium II": 14,
        "Intel Pentium III": 15,
        "Intel Pentium 4": 16,
        "Intel Pentium E2180": 17,
        "Intel Dual Core": 18,
        "AMD Athlon Processor": 19,
        "AMD Athlon 64": 20,
        "AMD Athlon 64 X2": 21,
        "AMD Athlon II": 22,
        "AMD Athlon II X4 620 2.6 GHz": 23,
        "AMD Phenom II X4 940": 24,
        "Intel Core 2 Duo": 25,
        "Intel CoreTM2 Duo": 26,
        "Intel Core 2 Duo E4500": 27,
        "Intel Core 2 Duo E5200": 28,
        "Intel Core 2 Duo E6600": 29,
        "Intel Core 2 Duo E6700": 30,
        "Intel Core 2 Duo E6750": 31,
        "Intel Core 2 Duo E6850": 32,
        "Intel Core 2 Duo E8200": 33,
        "Intel Core2 Duo E8400": 34,
        "2.4 GHz Dual Core Processor": 35,
        "Intel Core 2 Quad": 36,
        "AMD FX 4300": 37,
        "Intel Core i3": 37,
        "AMD FX 6300": 37,
        "AMD FX 8350": 38,
        "Intel Core i5": 38,
        "AMD FX 9590": 39,
        "Intel Core i7": 39,
        "Intel Core i9": 40}
    return cpu_hierarchy.get(user_cpu, 0) > cpu_hierarchy.get(game_cpu, 0)

def is_higher_gpu(user_gpu, game_gpu):
    gpu_hierarchy = {
        "OpenGL 1.4": 1,
        "2 MB of vRAM": 2,
        "4 MB of vRAM": 3,
        "8 MB of vRAM": 4,
        "32 MB of vRAM": 5,
        "Gráfica 3D compatible con DirectX 7": 6,
        "NVIDIA GeForce 6100": 7,
        "NVIDIA GeForce FX 5200": 8,
        "NVIDIA GeForce 6600": 9,
        "NVIDIA GeForce 6600GT": 10,
        "NVIDIA GeForce 7600": 11,
        "NVIDIA GeForce 7600GT": 12,
        "NVIDIA GeForce 240 GT": 13,
        "NVIDIA GeForce GT 420": 14,
        "Geforce GT 430": 15,
        "NVIDIA GeForce 450 GTS": 16,
        "OpenGL 2.0 compatible": 17,
        "OpenGL 3.0 Support": 18,
        "Tarjeta DirectX con resolución de 800 x 600": 19,
        "Radeon X1000": 20,
        "64 MB of vRAM": 21,
        "128 MB of vRAM": 22,
        "256 MB of vRAM": 23,
        "256 MB compatible con DirectX 9.0b": 24,
        "32 MB compatible con DirectX 9.0b": 25,
        "512 MB of vRAM": 25,
        "1 GB of vRAM": 26,
        "NVIDIA GeForce 8600": 26,
        "NVIDIA GeForce 8600GT": 27,
        "NIDIA GeForce 7800 GT": 28,
        "NVIDIA GeForce 7800 GTX": 29,
        "NVIDIA GeForce 8800": 30,
        "NVIDIA GeForce 8800GT": 31,
        "NVIDIA GeForce 8800GTS": 32,
        "NVIDIA GeForce 9600GT": 33,
        "NVIDIA GeForce 9800": 34,
        "NVIDIA GeForce 9800 GT": 35,
        "NVIDIA GeForce 9800GTX": 36,
        "ATI Radeon HD 3870": 37,
        "Nvidia GTS 260": 38,
        "Nvidia Geforce GTX 260": 38,
        "NVIDIA GTX 500": 39,
        "NVIDIA GeForce GTX 460": 40,
        "NVIDIA GeForce GTX 465": 41,
        "NVIDIA GeForce GTX 470": 42,
        "NVIDIA GeForce GTS 450": 43,
        "Intel HD 3000": 44,
        "NVIDIA GTX 580": 45,
        "GeForce GT 560 Ti": 46,
        "NVIDIA GTX 600": 47,
        "NVIDIA GTX 650": 48,
        "NVIDIA GeForce GTX 660": 49,
        "NVIDIA GeForce GTX 670": 50,
        "NVIDIA GeForce GTX 680": 51,
        "NVIDIA GTX 750": 52,
        "NVIDIA GeForce GTX 750 Ti": 53,
        "NVIDIA GTX 760": 54,
        "NVIDIA GeForce GTX 780": 55,
        "AMD Radeon RX Vega 6": 56,
        "NVIDIA GTX 960": 57,
        "NVIDIA GTX 970": 58,
        "AMD Radeon RX 460": 59,
        "AMD Radeon RX 560": 60,
        "NVIDIA GTX 1050": 61,
        "NVIDIA GeForce GTX 1050 Ti": 62,
        "AMD Radeon RX 580": 63,
        "AMD Radeon RX 590": 64,
        "NVIDIA GTX 1060": 65,
        "NVIDIA GTX 1070": 66,
        "NVIDIA GeForce GTX 1070 Ti": 67,
        "NVIDIA GTX 1650": 68,
        "NVIDIA RTX 2060": 69,
        "NVIDIA RTX 2060 Super": 70,
        "NVIDIA RTX 2070": 71,
        "NVIDIA RTX 3080": 72
    }
    return gpu_hierarchy.get(user_gpu, 0) > gpu_hierarchy.get(game_gpu, 0)

