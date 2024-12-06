#!/usr/bin/env python3
from datetime import datetime
import json
import re
import sys
from urllib.parse import quote, urlencode
from lib.utils.custom_dialogs import CustomDialog
import xbmc
import xbmcgui
from xbmcgui import Window
import xbmcaddon
import time
import sqlite3 as database
from xbmcvfs import translatePath as translate_path, delete as xbmc_delete
from xbmc import executeJSONRPC

_URL = sys.argv[0]

MOVIES_TYPE = "movies"
SHOWS_TYPE = "tvshows"
EPISODES_TYPE = "episodes"
TITLES_TYPE = "titles"

TORREST_ADDON_ID = "plugin.video.torrest"
JACKTORR_ADDON_ID = "plugin.video.jacktorr"
ELEMENTUM_ADDON_ID = "plugin.video.elementum"
JACKTOOK_BURST_ADOON_ID = "script.jacktook.burst"

try:
    JACKTORR_ADDON = xbmcaddon.Addon("plugin.video.jacktorr")
except:
    JACKTORR_ADDON = None

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")
ADDON_ICON = ADDON.getAddonInfo("icon")
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_VERSION = ADDON.getAddonInfo("version")
ADDON_NAME = ADDON.getAddonInfo("name")

progressDialog = xbmcgui.DialogProgress()


def get_jacktorr_setting(value, default=None):
    value = JACKTORR_ADDON.getSetting(value)
    if not value:
        return default

    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        return value


def get_setting(value, default=None):
    value = ADDON.getSetting(value)
    if not value:
        return default

    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        return value


def set_setting(id, value):
    ADDON.setSetting(id=id, value=value)


def get_property(prop):
    return Window(10000).getProperty(prop)


def set_property(prop, value):
    return Window(10000).setProperty(prop, value)


def clear_property(prop):
    return Window(10000).clearProperty(prop)


def burst_addon_settings():
    close_all_dialog()
    xbmc.executebuiltin("Addon.OpenSettings(%s)" % JACKTOOK_BURST_ADOON_ID)


def get_kodi_version():
    build = xbmc.getInfoLabel("System.BuildVersion")
    kodi_version = int(build.split()[0][:2])
    return kodi_version


def addon_status():
    msg = f"[B]Jacktook Version[/B]: {ADDON_VERSION}\n\n"
    try:
        msg += f"[B]Jacktorr Server IP/Address[/B]: {JACKTORR_ADDON.getSetting('service_host')}\n"
        msg += (
            f"[B]Jacktorr Server Port[/B]: {JACKTORR_ADDON.getSetting('service_port')}"
        )
    except:
        pass
    return xbmcgui.Dialog().textviewer("Status", msg, False)


def donate_message():
    msg = "If you like Jacktook you can support \n"
    msg += "its development by making a small donation to:\n\n"
    msg += "[COLOR snow]https://ko-fi.com/sammax09[/COLOR]"
    dialog = CustomDialog("customdialog.xml", ADDON_PATH, "Default", heading="", text=msg)
    dialog.doModal()


def is_torrest_addon():
    return xbmc.getCondVisibility(f"System.HasAddon({TORREST_ADDON_ID})")


def is_jacktorr_addon():
    return xbmc.getCondVisibility(f"System.HasAddon({JACKTORR_ADDON_ID})")


def is_elementum_addon():
    return xbmc.getCondVisibility(f"System.HasAddon({ELEMENTUM_ADDON_ID})")


def translation(id_value):
    return ADDON.getLocalizedString(id_value)


def logger(message, level=xbmc.LOGINFO):
    xbmc.log("[JACKTOOK] " + str(message), level)


def get_url(**kwargs):
    return "{}?{}".format(_URL, urlencode(kwargs))


def set_art(list_item, artwork_url):
    if artwork_url:
        list_item.setArt({"poster": artwork_url, "thumb": artwork_url})


def slugify(text):
    text = text.lower()
    text = re.sub(r"\[.*?\]", "", text)
    text = text.replace("(", "").replace(")", "")
    text = text.replace("'", "").replace("’", "")
    text = text.replace("+", "").replace("@", "")
    text = re.sub(r"[^a-zA-Z0-9_]+", "-", text)
    text = text.strip("-")
    return text


def compat(line1, line2, line3):
    message = line1
    if line2:
        message += "\n" + line2
    if line3:
        message += "\n" + line3
    return message


def refresh():
    xbmc.executebuiltin("Container.Refresh")


def notification(message, heading=ADDON_NAME, icon=ADDON_ICON, time=2000, sound=True):
    xbmcgui.Dialog().notification(heading, message, icon, time, sound)


def dialog_ok(heading, line1, line2="", line3=""):
    return xbmcgui.Dialog().ok(heading, compat(line1=line1, line2=line2, line3=line3))


def dialog_text(heading, content="", file=None):
    dialog = xbmcgui.Dialog()
    if file:
        with open(file, encoding="utf-8") as r:
            content = r.readlines()
            content = "".join(content)
    dialog.textviewer(heading, str(content), False)
    return dialog


def dialogyesno(header, text):
    dialog = xbmcgui.Dialog()
    confirmed = dialog.yesno(
        header,
        text,
    )
    if confirmed:
        return True
    else:
        return False


def close_all_dialog():
    execute_builtin("Dialog.Close(all,true)")


def container_update(name, **kwargs):
    """
    Update the container to the specified path.

    :param path: The path where to update.
    :type path: str
    """
    return "Container.Update({})".format(url_for_args(name, kwargs))


def container_refresh():
    execute_builtin("Container.Refresh")


def action(plugin, func, *args, **kwargs):
    return "RunPlugin({})".format(plugin.url_for(func, *args, **kwargs))


def action_url_run(name, **kwargs):
    return "RunPlugin({})".format(url_for_args(name, kwargs))


def url_for_args(name, kwargs):
    qs_kwargs = dict(((k, v) for k, v in list(kwargs.items())))
    query = "?" + urlencode(qs_kwargs) if qs_kwargs else ""
    return f"plugin://{ADDON_ID}/{name}" + query


def url_for(name, **kwargs):
    qs_kwargs = dict(((k, v) for k, v in list(kwargs.items())))
    query = "?" + urlencode(qs_kwargs) if qs_kwargs else ""
    return f"plugin://{ADDON_ID}/{name}" + query


def url_for_path(name, path):
    path = path if path.startswith("/") else "/" + path
    return f"plugin://{ADDON_ID}/{name}" + path


def play_info_hash(info_hash):
    url = f"plugin://{JACKTORR_ADDON_ID}/play_info_hash?info_hash={quote(info_hash)}"
    return f"PlayMedia({url})"


def buffer_and_play(info_hash, file_id, path):
    url = f"plugin://{JACKTORR_ADDON_ID}/buffer_and_play?info_hash={info_hash}&file_id={file_id}&path={quote(path)}"
    return f"PlayMedia({url})"


def play_media(plugin, func, *args, **kwargs):
    execute_builtin("PlayMedia({})".format(plugin.url_for(func, *args, **kwargs)))


def show_busy_dialog():
    execute_builtin("ActivateWindow(busydialognocancel)")


def show_picture(url):
    xbmc.executebuiltin('ShowPicture("{}")'.format(url))


def container_refresh():
    execute_builtin("Container.Refresh")


def hide_busy_dialog():
    execute_builtin("Dialog.Close(busydialognocancel)")
    execute_builtin("Dialog.Close(busydialog)")


def execute_builtin(command, block=False):
    return xbmc.executebuiltin(command, block)


def delete_file(file):
    xbmc_delete(file)


def update_local_addons():
    execute_builtin("UpdateLocalAddons", True)
    sleep(2500)


def disable_enable_addon(addon_name=ADDON_NAME):
    try:
        executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": addon_name, "enabled": False},
                }
            )
        )
        executeJSONRPC(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": addon_name, "enabled": True},
                }
            )
        )
    except:
        pass


def update_kodi_addons_db(addon_name=ADDON_NAME):
    try:
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        dbcon = database.connect(
            translate_path("special://database/Addons33.db"), timeout=40.0
        )
        dbcon.execute(
            "INSERT OR REPLACE INTO installed (addonID, enabled, lastUpdated) VALUES (?, ?, ?)",
            (addon_name, 1, date),
        )
        dbcon.close()
    except:
        pass


def bytes_to_human_readable(size, unit="B"):
    units = {"B": 0, "KB": 1, "MB": 2, "GB": 3, "TB": 4, "PB": 5}

    while size >= 1024 and unit != "PB":
        size /= 1024
        unit = list(units.keys())[list(units.values()).index(units[unit] + 1)]

    return f"{size:.2f} {unit}"


def convert_size_to_bytes(size_str: str) -> int:
    """Convert size string to bytes."""
    match = re.match(r"(\d+(?:\.\d+)?)\s*(GB|MB)", size_str, re.IGNORECASE)
    if match:
        size, unit = match.groups()
        size = float(size)
        return int(size * 1024**3) if "GB" in unit.upper() else int(size * 1024**2)
    return 0


def sleep(miliseconds):
    xbmc.sleep(miliseconds)


def show_keyboard(id, default="", hidden=False):
    keyboard = xbmc.Keyboard(default, translation(id), hidden)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()
    

def get_current_view_id():
    return xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()


def set_view_mode(view_id):
    xbmc.executebuiltin("Container.SetViewMode({})".format(view_id))


def set_view(name):
    views_dict = {
        "list": 50,
        "poster": 51,
        "iconwall": 52,
        "shift": 53,
        "infowall": 54,
        "widelist": 55,
        "wall": 500,
        "banner": 501,
        "fanart": 502,
    }
    execute_builtin("Container.SetViewMode({})".format(views_dict[name]))


def container_content():
    return xbmc.getInfoLabel("Container.Content")


def copy2clip(txt):
    import subprocess

    platform = sys.platform
    if platform == "win32":
        try:
            cmd = "echo %s|clip" % txt.strip()
            return subprocess.check_call(cmd, shell=True)
        except:
            pass
    elif platform == "linux2":
        try:
            from subprocess import PIPE, Popen

            p = Popen(["xsel", "-pi"], stdin=PIPE)
            p.communicate(input=txt)
        except:
            pass


def get_datetime(string=False, dt=False):
    d = datetime.now()
    if dt:
        return d
    if string:
        return d.strftime("%Y-%m-%d")
    return datetime.date(d)
