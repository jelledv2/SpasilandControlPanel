from flask import Flask, render_template, redirect, url_for, request
import subprocess
import os

app = Flask(__name__)

PAGE="index.html"

running_processes = {}

import os, subprocess

def run_command(action_name, cmd):
    if action_name in running_processes:
        stop_process_logic(action_name)

    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    proc = subprocess.Popen(
        cmd,
        env=env
    )

    running_processes[action_name] = proc
    return f"Gestart: {action_name} (PID {proc.pid})"

def stop_process_logic(action_name):
    proc = running_processes.get(action_name)
    if not proc:
        return False

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    del running_processes[action_name]
    return True

@app.route("/stop/<action_name>", methods=["POST"])
def stop_process(action_name):
    if not stop_process_logic(action_name):
        return render_template(PAGE, output=f"Proces {action_name} niet actief", active=set(running_processes.keys()))

    return render_template(PAGE, output=f"Gestopt: {action_name}", active=set(running_processes.keys()))

@app.route("/", methods=["GET"])
def index():
    return render_template(PAGE, output="Nog geen actie uitgevoerd.")

@app.route("/action/<action_name>", methods=["POST"])
def do_action(action_name):
    if action_name == "netflix":
        output = run_command(action_name, [
            "chromium",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "https://www.netflix.com"
            ])
    elif action_name == "youtube":
        output = run_command(action_name, [   
            "flatpak",
            "run",
            "rocks.shy.VacuumTube",
            "--fullscreen"
            ])
    elif action_name == "spotify":
        output = run_command(action_name, [
            "chromium",
            "--new-window",
            "--kiosk",
            "https://open.spotify.com/"
            ])
    elif action_name == "vrtmax":
        output = run_command(action_name, [
            "firefox",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "https://www.vrt.be/vrtmax/"
            ])
    elif action_name == "play":
        output = run_command(action_name, [
            "chromium",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "https://www.play.tv"
            ])
    elif action_name == "off":
        output = run_command(action_name, [
            "sudo",
            "shutdown",
            "-h",
            "now"
            ])
    else:
        output = "onbekende actie"
    return render_template(PAGE, output=output, active=set(running_processes.keys()))

@app.route("/action/link", methods=["POST"])
def handle_link():
    url = request.form.get("user_text", "").strip()
    if not url:
        return render_template(PAGE, output="Lege input ontvangen.", active=set(running_processes.keys()))

    output = run_command("youtube", [
        "firefox",
        "--enable-widevine",
        "--new-window",
        "--kiosk",
        url
        ])

    return render_template(PAGE, output=output, active=set(running_processes.keys())
    )


if __name__ == "__main__":
    # Luister op alle interfaces, poort 5000 (bijv. http://pi-ip:5000/)
    app.run(host="0.0.0.0", port=5000)
