from flask import Flask, render_template, redirect, url_for, request, jsonify
import subprocess
import os
import time
import re

app = Flask(__name__)

PAGE="index.html"

running_processes = {}
disco_light_on = False

import os, subprocess

def run_command(action_name, cmd):
    if action_name != "link" and action_name in running_processes:
        stop_process_logic(action_name)

    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    proc = subprocess.Popen(
        cmd,
        env=env
    )

    running_processes[action_name] = proc
    return f"Gestart: {action_name} (PID {proc.pid})"

CHROMIUM_PROFILE_DIRS = {
    "netflix":  "/home/jelle/.config/chromium-netflix",
    "spotify":  "/home/jelle/.config/chromium-spotify",
    "vrtmax":   "/home/jelle/.config/chromium-vrtmax",
    "play":     "/home/jelle/.config/chromium-play",
    "link":     "/home/jelle/.config/chromium-link",
    "command":  "/home/jelle/.config/chromium-command",
}

def stop_process_logic(action_name):
    if action_name == "youtube":
        subprocess.run(["flatpak", "kill", "rocks.shy.VacuumTube"])
        running_processes.pop(action_name, None)
        return True

    if action_name in CHROMIUM_PROFILE_DIRS:
        profile_dir = CHROMIUM_PROFILE_DIRS[action_name]
        subprocess.run(["pkill", "-f", profile_dir])
        running_processes.pop(action_name, None)
        return True

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
        return render_template(PAGE, output=f"Proces {action_name} niet actief", active=set(running_processes.keys()), disco_on=disco_light_on)

    return render_template(PAGE, output=f"Gestopt: {action_name}", active=set(running_processes.keys()), disco_on=disco_light_on)

@app.route("/lights/disco/on", methods=["POST"])
def disco_on():
    global disco_light_on
    subprocess.Popen(["sudo", "python3", "/home/jelle/disco_light.py", "on"])
    disco_light_on = True
    return jsonify(success=True, disco_on=True)


@app.route("/lights/disco/off", methods=["POST"])
def disco_off():
    global disco_light_on
    subprocess.Popen(["sudo", "python3", "/home/jelle/disco_light.py", "off"])
    disco_light_on = False
    return jsonify(success=True, disco_on=False)


@app.route("/", methods=["GET"])
def index():
    return render_template(PAGE, output="Nog geen actie uitgevoerd.", disco_on=disco_light_on)

@app.route("/action/<action_name>", methods=["POST"])
def do_action(action_name):
    if action_name == "netflix":
        output = run_command(action_name, [
            "chromium",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "--user-data-dir=/home/jelle/.config/chromium-netflix",
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
            "--user-data-dir=/home/jelle/.config/chromium-spotify",
            "https://open.spotify.com/"
            ])
    elif action_name == "vrtmax":
        output = run_command(action_name, [
            "chromium",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "--user-data-dir=/home/jelle/.config/chromium-vrtmax",
            "https://www.vrt.be/vrtmax/"
            ])
    elif action_name == "play":
        output = run_command(action_name, [
            "chromium",
            "--enable-widevine",
            "--new-window",
            "--kiosk",
            "--user-data-dir=/home/jelle/.config/chromium-play",
            "https://www.play.tv"
            ])
    elif action_name == "stremio":
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        env["QT_SCALE_FACTOR"] = "1.7"
        proc = subprocess.Popen(["stremio"], env=env)
        running_processes[action_name] = proc
        output = f"Gestart: stremio (PID {proc.pid})"
    elif action_name == "command":
        user_input = request.form.get("user_command", "").strip()
        if not user_input:
            return render_template(PAGE, output="Lege input ontvangen.", active=set(running_processes.keys()))
        command = user_input.split()
        output = run_command(action_name, command)

    elif action_name == "off":
        output = run_command(action_name, [
            "sudo",
            "shutdown",
            "-h",
            "now"
            ])
    elif action_name == "restart":
        output = run_command(action_name, [
            "sudo",
            "reboot"
            ])
    else:
        output = "onbekende actie"
    return render_template(PAGE, output=output, active=set(running_processes.keys()), disco_on=disco_light_on)

@app.route("/action/link", methods=["POST"])
def handle_link():
    user_input = request.form.get("user_text", "").strip()
    if not user_input:
        return render_template(PAGE, output="Lege input ontvangen.", active=set(running_processes.keys()))

    if user_input.startswith("http://") or user_input.startswith("https://"):
        url = user_input
    else:
        import urllib.parse
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(user_input)

    output = run_command("link", [
        "chromium",
        "--enable-widevine",
        "--new-window",
        "--kiosk",
        "--user-data-dir=/home/jelle/.config/chromium-link",
        url
        ])

    return render_template(PAGE, output=output, active=set(running_processes.keys()), disco_on=disco_light_on)



@app.route("/kill/<int:pid>", methods=["POST"])
def kill_process(pid):
    import psutil
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        return jsonify(success=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return jsonify(success=False, error=str(e)), 400


@app.route("/processes")
def get_processes():
    import psutil
    sort_by = request.args.get("sort", "cpu")
    cpu_count = psutil.cpu_count() or 1

    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            info = proc.info
            ram_mb = info['memory_info'].rss // (1024 * 1024) if info['memory_info'] else 0
            procs.append({
                'pid': info['pid'],
                'name': info['name'],
                'cpu': round(info['cpu_percent'] / cpu_count, 1),
                'ram_mb': ram_mb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if sort_by == "ram":
        procs.sort(key=lambda p: p['ram_mb'], reverse=True)
    else:
        procs.sort(key=lambda p: p['cpu'], reverse=True)

    return jsonify(processes=procs[:5])


@app.route("/stats")
def get_stats():
    import psutil

    cpu_percent = psutil.cpu_percent(interval=None)

    ram = psutil.virtual_memory()
    ram_used_mb = ram.used // (1024 * 1024)
    ram_total_mb = ram.total // (1024 * 1024)
    ram_percent = ram.percent

    disk = psutil.disk_usage("/")
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)
    disk_percent = disk.percent

    temp = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = round(int(f.read().strip()) / 1000, 1)
    except Exception:
        pass

    uptime_seconds = int(time.time() - psutil.boot_time())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}u {minutes}m {seconds}s"

    return jsonify(
        cpu_percent=cpu_percent,
        ram_used_mb=ram_used_mb,
        ram_total_mb=ram_total_mb,
        ram_percent=ram_percent,
        disk_used_gb=round(disk_used_gb, 1),
        disk_total_gb=round(disk_total_gb, 1),
        disk_percent=disk_percent,
        temp=temp,
        uptime=uptime_str,
    )


@app.route("/audio/surround", methods=["POST"])
def open_surround():
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    proc = subprocess.Popen(["qpwgraph", "/home/jelle/surround.qpwgraph"], env=env)
    running_processes["surround"] = proc
    return jsonify(success=True)


@app.route("/audio/surround/stop", methods=["POST"])
def close_surround():
    stop_process_logic("surround")
    return jsonify(success=True)


def pulse_env():
    env = os.environ.copy()
    uid = os.getuid()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("PULSE_SERVER", f"unix:/run/user/{uid}/pulse/native")
    return env


@app.route("/audio/volume", methods=["GET"])
def get_volume():
    env = pulse_env()
    try:
        vol_out = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], env=env, text=True)
        match = re.search(r'(\d+)%', vol_out)
        volume = int(match.group(1)) if match else 0

        mute_out = subprocess.check_output(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], env=env, text=True)
        muted = "yes" in mute_out.lower()

        return jsonify(volume=volume, muted=muted)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route("/audio/volume", methods=["POST"])
def set_volume():
    env = pulse_env()
    data = request.get_json()
    volume = max(0, min(150, int(data.get("volume", 50))))
    try:
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"], env=env, check=True)
        return jsonify(success=True, volume=volume)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@app.route("/audio/mute", methods=["POST"])
def toggle_mute():
    env = pulse_env()
    try:
        subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], env=env, check=True)
        mute_out = subprocess.check_output(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], env=env, text=True)
        muted = "yes" in mute_out.lower()
        return jsonify(success=True, muted=muted)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


if __name__ == "__main__":
    # Luister op alle interfaces, poort 5000 (bijv. http://pi-ip:5000/)
    app.run(host="0.0.0.0", port=5000)
