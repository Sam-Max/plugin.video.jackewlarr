import xbmcgui
from typing import List
from lib.stremio.addons_manager import AddonManager, Addon
from lib.api.jacktook.kodi import kodilog
from lib.db.cached import cache
from datetime import timedelta
from lib.stremio.client import Stremio
from lib.utils.kodi_utils import ADDON

STREMIO_ADDONS_KEY = "stremio_addons"
STREMIO_CATALOG_KEY = "stremio_catalog"


def get_addons_catalog():
    catalog = cache.get(STREMIO_CATALOG_KEY, hashed_key=True)
    if not catalog:
        stremio = Stremio()
        try:
            catalog = stremio.get_community_addons()
        except Exception as e:
            kodilog(f"Failed to fetch catalog: {e}")
            return AddonManager([])

        selected_keys = cache.get(STREMIO_ADDONS_KEY, hashed_key=True) or ""
        if not selected_keys:
            selected_keys = "com.stremio.torrentio.addon"
            cache.set(STREMIO_ADDONS_KEY, selected_keys, timedelta(days=365 * 20), hashed_key=True)
        
        cache.set(STREMIO_CATALOG_KEY, catalog, timedelta(days=1), hashed_key=True)
    return AddonManager(catalog)


def get_selected_addon_urls() -> List[str]:
    selected_addons = cache.get(STREMIO_ADDONS_KEY, hashed_key=True) or ""
    return selected_addons.split(",")


def get_selected_addons() -> List[Addon]:
    catalog = get_addons_catalog()
    selected_ids = cache.get(STREMIO_ADDONS_KEY, hashed_key=True) or ""
    return [addon for addon in catalog.addons if addon.url() in selected_ids]


def stremio_addons_import(params):
    # Create a dialog box
    dialog = xbmcgui.Dialog()

    dialog.ok(
        "Stremio Add-ons Import",
        "To import your add-ons, please log in with your Stremio email and password.\n\n"
        + "Your login details will not be saved and are only used once for this process.",
    )

    # Show an input dialog for email
    email = dialog.input(heading="Enter your Email", type=xbmcgui.INPUT_ALPHANUM)

    if not email:
        return

    # Show a password dialog
    password = dialog.input(heading="Enter your Password", type=xbmcgui.INPUT_ALPHANUM)

    if not password:
        return

    try:
        stremio = Stremio()
        stremio.login(email, password)
    except Exception as e:
        dialog.ok("Login Failed", f"Failed to login: {e}")
        return

    try:
        addons = stremio.get_my_addons()
        cache.set(
            STREMIO_CATALOG_KEY, addons, timedelta(days=365 * 20), hashed_key=True
        )
        manager = AddonManager(addons).get_addons_with_resource_and_id_prefix(
            "stream", "tt"
        )
        selected_addons = [addon.key() for addon in manager]
        cache.set(
            STREMIO_ADDONS_KEY,
            ",".join(selected_addons),
            timedelta(days=365 * 20),
            hashed_key=True,
        )
        settings = ADDON.getSettings()
        ADDON.setSetting("stremio_loggedin", "true")
        settings.setString("stremio_email", email)
        settings.setString("stremio_pass", password)
    except Exception as e:
        dialog.ok(
            "Add-ons Import Failed",
            "Please try again later and report the issue if the problem persists. For more details, check the log file.",
        )
        kodilog(f"Failed to import addons: {e} Response ")
        return

    dialog.ok("Addons Imported", f"Successfully imported addons from your account.")
    
    stremio_addons_manager(None)

def stremio_logout(params):
    dialog = xbmcgui.Dialog()

    confirm = dialog.yesno(
        "Log Out from Stremio",
        "Are you sure you want to log out? You can continue using Stremio without logging in, but your settings will be reset to the default configuration.",
        nolabel="Cancel",
        yeslabel="Log Out",
    )
    if confirm:
        cache.set(
            STREMIO_ADDONS_KEY, None, timedelta(seconds=1), hashed_key=True
        )
        cache.set(
            STREMIO_CATALOG_KEY, None, timedelta(seconds=1), hashed_key=True
        )
        settings = ADDON.getSettings()
        ADDON.setSetting("stremio_loggedin", "false")
        settings.setString("stremio_email", "")
        settings.setString("stremio_pass", "")
        _ = get_addons_catalog()
        stremio_addons_manager(None)

def stremio_addons_manager(params):
    selected_ids = get_selected_addon_urls()
    addon_manager = get_addons_catalog()

    addons = addon_manager.get_addons_with_resource_and_id_prefix("stream", "tt")

    dialog = xbmcgui.Dialog()
    selected_addon_ids = [addons.index(addon) for addon in addons if addon.key() in selected_ids]

    options = []
    for addon in addons:
        option = xbmcgui.ListItem(
            label=addon.manifest.name,
            label2=f"{addon.manifest.description}"
            )
        option.setArt({"icon": addon.manifest.logo if addon.manifest.logo else None})
        options.append(option)

    settings = ADDON.getSettings()
    title = "Stremio Community Addons List" if not ADDON.getSetting("stremio_loggedin") != "true" else settings.getString("stremio_email")
    selected_indexes = dialog.multiselect(title, options, preselect=selected_addon_ids, useDetails=True)

    if selected_indexes is None:
        return


    selected_addon_ids = [addons[index].key() for index in selected_indexes]


    cache.set(
        STREMIO_ADDONS_KEY,
        ",".join(selected_addon_ids),
        timedelta(days=365 * 20),
        hashed_key=True,
    )
