import re
from resources.lib.anilist import anilist_client
from resources.lib.utils.kodi import action, bytes_to_human_readable, log
from resources.lib.tmdbv3api.objs.find import Find
from resources.lib.utils.utils import (
    Indexer,
    add_play_item,
    add_pack_item,
    fanartv_get,
    get_description_length,
    get_random_color,
    info_hash_to_magnet,
    is_torrent_watched,
    set_video_item,
    tmdb_get,
)
from xbmcgui import ListItem
from xbmcplugin import endOfDirectory

def indexer_show_results(results, mode, query, id, tvdb_id, plugin, func, func2, func3, func4):
    poster = ""
    overview = ""
    description_length = get_description_length()

    # Direct Search if query is None
    if query is not None:  
        if mode == "tv":
            if tvdb_id == "-1": # for anime episode
                _, result = anilist_client().get_by_id(id)
                overview = result.get("description", "")
                poster = result.get("coverImage", {}).get("large", "")
            else:
                result = Find().find_by_tvdb_id(tvdb_id)
                overview = result["tv_results"][0].get("overview", "")
                data = fanartv_get(tvdb_id, mode)
                if data:
                    poster = data["clearlogo2"]
        elif mode == "movie":
            details = tmdb_get("movie_details", id)
            overview = details.get("overview", "")
            data = fanartv_get(tvdb_id, mode)
            if data:
                poster = data["clearlogo2"]

    for res in results:
        title = res["title"]
        if len(title) > description_length:
            title = title[:description_length]

        quality_title = res["quality_title"]
        if len(quality_title) > description_length:
            quality_title = quality_title[:description_length]

        magnet = ""
        date = res.get("publishDate", "")
        match = re.search(r"\d{4}-\d{2}-\d{2}", date)
        if match:
            date = match.group()
        size = bytes_to_human_readable(int(res.get("size")))
        seeders = res["seeders"]
        tracker = res["indexer"]

        watched = is_torrent_watched(quality_title)
        if watched:
            quality_title = f"[COLOR palevioletred]{quality_title}[/COLOR]"

        tracker_color = get_random_color(tracker)
        torr_title = f"[B][COLOR {tracker_color}][{tracker}][/COLOR][/B] {quality_title}[CR][I][LIGHT][COLOR lightgray]{date}, {size}, {seeders} seeds[/COLOR][/LIGHT][/I]"

        debrid_type = res["debridType"]
        debrid_type_color = get_random_color(debrid_type)
        format_debrid_type = f"[B][COLOR {debrid_type_color}][{debrid_type}][/COLOR][/B]"
        
        if res["debridCached"]:
            debrid_links = res.get("debridLinks")
            debrid_id = res.get("debridId")
            if debrid_id:
                list_item = ListItem(label=f"[{format_debrid_type}-Pack]-{torr_title}")
                add_pack_item(list_item, func2, debrid_id, debrid_type, plugin)
            else:
                url = debrid_links[0]
                title = f"[B][Cached][/B]-{title}"
                list_item = ListItem(label=f"[{format_debrid_type}-Cached]-{torr_title}")
                list_item.addContextMenuItems([("Download to Disk", action(plugin, func4, query=f"{url}"))])
                set_video_item(list_item, poster, overview)
                add_play_item(list_item, url, magnet, id, title, func, plugin)
        else:
            download_url = res.get("downloadUrl") or res.get("magnetUrl")
            guid = res.get("guid")
            if guid:
                if res.get("indexer") in [Indexer.TORRENTIO, Indexer.ELHOSTED]:
                    magnet = info_hash_to_magnet(guid)
                else:
                    if guid.startswith("magnet:?"):
                        magnet = guid
                    else:
                        # For some indexers, the guid is a torrent file url
                        download_url = res.get("guid")
            list_item = ListItem(label=torr_title)
            set_video_item(list_item, poster, overview)
            if magnet:
                list_item.addContextMenuItems(
                    [("Download to Debrid", action(plugin, func3, query= f"{magnet} {debrid_type}"))]
                )
            add_play_item(list_item, download_url, magnet, id, title, func, plugin)

    endOfDirectory(plugin.handle)

