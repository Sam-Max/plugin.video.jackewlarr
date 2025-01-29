import sys
from urllib import parse
from lib.gui.custom_dialogs import run_next_dialog, run_resume_dialog
from lib.navigation import (
    addon_update,
    animation_item,
    animation_menu,
    anime_item,
    anime_menu,
    anime_search,
    clear_all_cached,
    clear_history,
    cloud,
    cloud_details,
    direct_menu,
    donate,
    files,
    get_rd_downloads,
    history,
    list_trakt_page,
    movies_items,
    next_page_anime,
    open_burst_config,
    play_from_pack,
    play_url,
    pm_auth,
    rd_info,
    search_tmdb_genres,
    search_tmdb_year,
    telegram_menu,
    test_resume_dialog,
    test_run_next,
    test_source_select,
    torrentio_selection,
    play_torrent,
    rd_auth,
    rd_remove_auth,
    root_menu,
    search,
    search_direct,
    search_item,
    settings,
    titles,
    torrents,
    trakt_auth,
    trakt_auth_revoke,
    trakt_list_content,
    tv_episodes_details,
    tv_seasons_details,
    tv_shows_items,
)
from lib.telegram import (
    get_telegram_files,
    get_telegram_latest,
    get_telegram_latest_files,
)
from lib.tmdb import handle_tmdb_query, search_tmdb
from lib.utils.torrent_utils import (
    display_picture,
    display_text,
    torrent_action,
    torrent_files,
)
from lib.stremio.ui import stremio_login, stremio_toggle_addons, stremio_logout

def addon_router():
    param_string = sys.argv[2][1:]
    actions = {
        "run_next_dialog": run_next_dialog,
        "run_resume_dialog": run_resume_dialog,
        "tv_shows_items": tv_shows_items,
        "tv_seasons_details": tv_seasons_details,
        "tv_episodes_details": tv_episodes_details,
        "movies_items": movies_items,
        "direct_menu": direct_menu,
        "anime_menu": anime_menu,
        "anime_item": anime_item,
        "anime_search": anime_search,
        "search": search,
        "search_tmdb":search_tmdb,
        "search_tmdb_year": search_tmdb_year,
        "search_tmdb_genres": search_tmdb_genres,
        "handle_tmdb_query": handle_tmdb_query,
        "search_direct": search_direct,
        "search_item": search_item,
        "next_page_anime": next_page_anime,
        "play_torrent": play_torrent,
        "play_from_pack": play_from_pack,
        "play_url": play_url,
        "trakt_list_content": trakt_list_content,
        "list_trakt_page": list_trakt_page,
        "cloud": cloud,
        "cloud_details": cloud_details,
        "settings": settings,
        "files": files,
        "titles": titles,
        "history": history,
        "donate": donate,
        "clear_all_cached": clear_all_cached,
        "clear_history": clear_history,
        "addon_update": addon_update,
        "open_burst_config": open_burst_config,
        "rd_auth": rd_auth,
        "rd_remove_auth": rd_remove_auth,
        "rd_info": rd_info,
        "get_rd_downloads": get_rd_downloads,
        "trakt_auth": trakt_auth,
        "trakt_auth_revoke": trakt_auth_revoke,
        "pm_auth": pm_auth,
        "torrents": torrents,
        "torrent_action": torrent_action,
        "torrent_files": torrent_files,
        "torrentio_selection": torrentio_selection,
        "get_telegram_files": get_telegram_files,
        "get_telegram_latest": get_telegram_latest,
        "get_telegram_latest_files": get_telegram_latest_files,
        "telegram_menu": telegram_menu,
        "display_picture": display_picture,
        "display_text": display_text,
        "test_source_select": test_source_select,
        "test_run_next": test_run_next,
        "test_resume_dialog": test_resume_dialog,
        "animation_menu": animation_menu,
        "animation_item": animation_item,
        "stremio_toggle_addons": stremio_toggle_addons,
        'stremio_login': stremio_login,
        'stremio_logout': stremio_logout,
    }

    if param_string:
        params = dict(parse.parse_qsl(param_string))
        action = params.get("action")
        action_func = actions.get(action)
        if action_func:
            action_func(params)
            return

    root_menu()
