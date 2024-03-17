import copy
import requests
import io

from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from resources.lib.api.premiumize_api import Premiumize
from resources.lib.api.real_debrid_api import RealDebrid
from resources.lib.utils.kodi import get_setting, log

from resources.lib.torf._torrent import Torrent
from resources.lib.utils.rd_utils import add_rd_magnet
from resources.lib.utils.utils import (
    Indexer,
    get_cached,
    get_info_hash_from_magnet,
    info_hash_to_magnet,
    is_url,
    set_cached,
    supported_video_extensions,
)


dialog_update = {"count": -1, "percent": 50}

USER_AGENT_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}


def check_debrid_cached(query, results, mode, media_type, dialog, rescrape, episode=1):
    if not rescrape:
        if query:
            if mode == "tv" or media_type == "tv":
                cached_results = get_cached(query, params=(episode, "deb"))
            else:
                cached_results = get_cached(query, params=("deb"))
            
            if cached_results:
                return cached_results

    lock = Lock()
    cached_results = []
    uncached_results = []

    rd_enabled = get_setting("real_debrid_enabled")
    pm_enabled = get_setting("premiumize_enabled")

    if rd_enabled and pm_enabled:
        total = len(results) * 2
    else:
        total = len(results)

    get_magnet_and_infohash(results, lock)

    with ThreadPoolExecutor(max_workers=total) as executor:
        if rd_enabled:
            rd_client = RealDebrid(encoded_token=get_setting("real_debrid_token"))
            [
                executor.submit(
                    check_rd_cached,
                    rd_client,
                    res,
                    cached_results,
                    uncached_results,
                    total,
                    dialog,
                    lock=lock,
                )
                for res in copy.deepcopy(results)
            ]
        if pm_enabled:
            pm_client = Premiumize(token=get_setting("premiumize_token"))
            [
                executor.submit(
                    check_pm_cached,
                    pm_client,
                    res,
                    cached_results,
                    uncached_results,
                    total,
                    dialog,
                    lock=lock,
                )
                for res in copy.deepcopy(results)
            ]
        executor.shutdown(wait=True)
    dialog_update["count"] = -1
    dialog_update["percent"] = 50

    if get_setting("show_uncached"):
        cached_results.extend(uncached_results)

    if query:
        if mode == "tv" or media_type == "tv":
            set_cached(cached_results, query, params=(episode, "deb"))
        else:
            set_cached(cached_results, query, params=("deb"))

    return cached_results


def check_rd_cached(client, res, cached_results, uncached_result, total, dialog, lock):
    debrid_dialog_update(total, dialog, lock)
    info_hash = res.get("infoHash")
    magnet = res.get("magnet")
    try:
        if info_hash and magnet:
            torr_available = client.get_torrent_instant_availability(info_hash)
            if info_hash in torr_available:
                with lock:
                    res["debridCached"] = True
                    res["debridType"] = "RD"
                    if res.get("indexer") in [Indexer.TORRENTIO, Indexer.ELHOSTED]:
                        magnet = info_hash_to_magnet(info_hash)
                torrent_id = add_rd_magnet(client, magnet)
                if torrent_id:
                    res["debridId"] = torrent_id
                    torr_info = client.get_torrent_info(torrent_id)
                    with lock:
                        if len(torr_info["links"]) > 1:
                            res["debridPack"] = True
                        cached_results.append(res)
            else:
                with lock:
                    res["debridCached"] = False
                    uncached_result.append(res)
    except Exception as e:
        log(f"Error: {str(e)}")


def check_pm_cached(client, res, cached_results, uncached_result, total, dialog, lock):
    debrid_dialog_update(total, dialog, lock)
    info_hash = res.get("infoHash")
    magnet = res.get("magnet")
    extensions = supported_video_extensions()[:-1]
    try:
        if info_hash and magnet:
            torr_available = client.get_torrent_instant_availability(info_hash)
            if torr_available.get("response")[0]:
                with lock:
                    res["debridCached"] = True
                    res["debridType"] = "PM"
                    if res.get("indexer") in [Indexer.TORRENTIO, Indexer.ELHOSTED]:
                        magnet = info_hash_to_magnet(info_hash)
                response_data = client.create_download_link(magnet)
                if "error" in response_data.get("status"):
                    log(
                        f"Failed to get link from Premiumize {response_data.get('message')}"
                    )
                    return
                content = response_data.get("content")
                files_names = [
                    item["path"].rsplit("/", 1)[-1]
                    for item in content
                    for x in extensions
                    if item["path"].lower().endswith(x)
                ]
                with lock:
                    if len(files_names) > 1:
                        res["debridPack"] = True
                    cached_results.append(res)
            else:
                with lock:
                    res["debridCached"] = False
                    uncached_result.append(res)
    except Exception as e:
        log(f"Error: {str(e)}")


def get_magnet_and_infohash(results, lock):
    with lock:
        for res in results:
            guid = res.get("guid")
            if guid:
                if guid.startswith("magnet:?") or len(guid) == 40:
                    info_hash = (
                        res["infoHash"].lower()
                        if res.get("infoHash")
                        else get_info_hash_from_magnet(guid).lower()
                    )
                else:
                    # For some indexers, the guid is a torrent file url
                    download_url = res.get("guid")
                    guid, info_hash = get_magnet_from_uri(download_url)
            else:
                download_url = res.get("magnetUrl") or res.get("downloadUrl")
                guid, info_hash = get_magnet_from_uri(download_url)

            res["magnet"] = guid
            res["infoHash"] = info_hash


def get_magnet_from_uri(uri):
    magnet_link = ""
    info_hash = ""

    if is_url(uri):
        res = requests.get(
            uri, allow_redirects=False, timeout=20, headers=USER_AGENT_HEADER
        )
        if res.is_redirect:
            uri = res.headers.get("Location")
            if uri.startswith("magnet:"):
                magnet_link = uri
                info_hash = get_info_hash_from_magnet(uri)
        elif (
            res.status_code == 200
            and res.headers.get("Content-Type") == "application/x-bittorrent"
        ):
            torrent = Torrent.read_stream(io.BytesIO(res.content))
            magnet_link = str(torrent.magnet())
            info_hash = torrent.magnet().infohash
        else:
            log(f"Could not get torrent data from: {uri}")
            
    return magnet_link, info_hash


def debrid_dialog_update(total, dialog, lock):
    with lock:
        dialog_update["count"] += 1
        dialog_update["percent"] += 2

        dialog.update(
            dialog_update.get("percent"),
            f"Jacktook [COLOR FFFF6B00]Debrid[/COLOR]",
            f"Checking: {dialog_update.get('count')}/{total}",
        )
