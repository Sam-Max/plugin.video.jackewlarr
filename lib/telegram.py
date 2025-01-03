from lib.api.jacktook.kodi import kodilog
from lib.clients.jackgram import Jackgram
from lib.utils.client_utils import validate_host
from lib.utils.tmdb_utils import tmdb_get

from lib.utils.utils import (
    TMDB_POSTER_URL,
    Indexer,
    add_next_button,
    execute_thread_pool,
    list_item,
    set_content_type,
    set_media_infotag,
)

from lib.utils.kodi_utils import (
    ADDON_HANDLE,
    build_url,
    get_setting,
    notification,
    set_view,
)

from xbmcplugin import addDirectoryItem, endOfDirectory


def get_telegram_latest(params):
    indexer = get_setting("indexer")
    if indexer != Indexer.JACKGRAM:
        notification("You need to select Jackgram indexer")
        return
    page = int(params.get("page"))
    host = get_setting("jackgram_host")
    if not validate_host(host):
        return
    jackgram_client = Jackgram(host, notification)
    results = jackgram_client.get_latest(page=page)
    execute_thread_pool(results, telegram_items)
    add_next_button("get_telegram_latest", page=page)
    endOfDirectory(ADDON_HANDLE)
    set_view("widelist")


def telegram_items(info):
    mode = info["type"]
    title = info["title"]
    if mode == "tv":
        details = tmdb_get("tv_details", info["tmdb_id"])
    else:
        details = tmdb_get("movie_details", info["tmdb_id"])
    poster_path = f"{TMDB_POSTER_URL}{details.poster_path or ''}"
    overview = details.overview or ""
    item = list_item(title, poster_path=poster_path, icon="trending.png")
    set_media_infotag(item, mode, title, overview=overview)
    addDirectoryItem(
        ADDON_HANDLE,
        build_url("get_telegram_files", data=info),
        item,
        isFolder=True,
    )


def get_telegram_files(params):
    data = eval(params["data"])
    mode = data["type"]

    set_content_type(mode)

    execute_thread_pool(data["files"], telegram_files_items, data)
    endOfDirectory(ADDON_HANDLE)


def telegram_files_items(info, data):
    mode = info["mode"]
    if mode == "tv":
        details = tmdb_get(
            "episode_details",
            params={
                "id": data["tmdb_id"],
                "season": info["season"],
                "episode": info["episode"],
            },
        )
        poster_path = TMDB_POSTER_URL + details.still_path
    else:
        details = tmdb_get("movie_details", data["tmdb_id"])
        poster_path = TMDB_POSTER_URL + details.poster_path

    overview = details.overview or ""

    item = list_item(info["title"], poster_path=poster_path)
    set_media_infotag(item, info["mode"], info["title"], overview=overview)
    item.setProperty("IsPlayable", "true")
    addDirectoryItem(
        ADDON_HANDLE,
        build_url("play_torrent", data=info),
        item,
        isFolder=False,
    )
