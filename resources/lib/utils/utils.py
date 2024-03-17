from datetime import datetime, timedelta
import hashlib
import os
import re
import unicodedata

from resources.lib.db.cached import Cache
from resources.lib.db.database import get_db
from resources.lib.tmdbv3api.objs.find import Find
from resources.lib.tmdbv3api.objs.genre import Genre
from resources.lib.tmdbv3api.objs.movie import Movie
from resources.lib.tmdbv3api.objs.search import Search
from resources.lib.tmdbv3api.objs.season import Season
from resources.lib.tmdbv3api.objs.tv import TV

from resources.lib.torf._magnet import Magnet
from resources.lib.fanarttv import search_api_fanart_tv
from resources.lib.utils.kodi import (
    ADDON_PATH,
    container_refresh,
    get_cache_expiration,
    get_int_setting,
    get_setting,
    get_torrest_setting,
    is_cache_enabled,
    log,
    translation,
)

from resources.lib.tmdbv3api.objs.discover import Discover
from resources.lib.tmdbv3api.objs.trending import Trending

from xbmcgui import ListItem, Dialog
from xbmcplugin import addDirectoryItem
from xbmc import getSupportedMedia


cache = Cache()

db = get_db()

PROVIDER_COLOR_MIN_BRIGHTNESS = 50

URL_REGEX = r"^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$"

video_extensions = (
    ".001",
    ".3g2",
    ".3gp",
    ".asf",
    ".asx",
    ".avc",
    ".avi",
    ".avs",
    ".bdm",
    ".bdmv",
    ".bin",
    ".bivx",
    ".dat",
    ".divx",
    ".dv",
    ".dvr-ms",
    ".evo",
    ".f4v",
    ".fli",
    ".flv",
    ".h264",
    ".img",
    ".iso",
    ".m2t",
    ".m2ts",
    ".m2v",
    ".m3u8",
    ".m4v",
    ".mk3d",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mpl",
    ".mpls",
    ".mts",
    ".nrg",
    ".nuv",
    ".ogm",
    ".ogv",
    ".pva",
    ".qt",
    ".rcv",
    ".rec",
    ".rmvb",
    ".sdp",
    ".svq3",
    ".tp",
    ".trp",
    ".ts",
    ".ty",
    ".udf",
    ".vc1",
    ".vdr",
    ".viv",
    ".vob",
    ".vp3",
    ".webm",
    ".wmv",
    ".xvid",
)


class Enum:
    @classmethod
    def values(cls):
        return [value for name, value in vars(cls).items() if not name.startswith("_")]


class Indexer(Enum):
    PROWLARR = "Prowlarr"
    JACKETT = "Jackett"
    TORRENTIO = "Torrentio"
    ELHOSTED = "Elfhosted"


def list_item(label, icon):
    item = ListItem(label)
    item.setArt(
        {
            "icon": os.path.join(ADDON_PATH, "resources", "img", icon),
            "thumb": os.path.join(ADDON_PATH, "resources", "img", icon),
            "fanart": os.path.join(ADDON_PATH, "fanart.png"),
        }
    )
    return item


def add_play_item(
    list_item,
    ids,
    tvdata,
    title,
    url="",
    magnet="",
    torrent_id="",
    info_hash="",
    debrid_type="",
    mode="",
    is_torrent=False,
    is_debrid=False,
    func=None,
    plugin=None,
):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(
            func,
            title=title,
            ids=ids,
            tvdata=tvdata,
            url=url,
            magnet=magnet,
            torrent_id=torrent_id,
            info_hash=info_hash,
            is_torrent=is_torrent,
            is_debrid=is_debrid,
            mode=mode,
            debrid_type=debrid_type,
        ),
        list_item,
        isFolder=False,
    )


def add_pack_item(
    list_item, func, tvdata, ids, info_hash, torrent_id, debrid_type, mode, plugin
):
    addDirectoryItem(
        plugin.handle,
        plugin.url_for(
            func,
            query=f"{info_hash} {torrent_id} {debrid_type}",
            tvdata=tvdata,
            mode=mode,
            ids=ids,
        ),
        list_item,
        isFolder=True,
    )


def set_video_item(list_item, poster, overview):
    list_item.setArt(
        {
            "poster": poster,
            "thumb": os.path.join(ADDON_PATH, "resources", "img", "magnet.png"),
            "icon": os.path.join(ADDON_PATH, "resources", "img", "magnet.png"),
        }
    )
    info_tag = list_item.getVideoInfoTag()
    info_tag.setMediaType("video")
    info_tag.setPlot(overview)

    list_item.setProperty("IsPlayable", "true")


def set_watched_file(
    title, ids, tvdata, magnet, url, debrid_type, is_debrid, is_torrent
):
    if title in db.database["jt:lfh"]:
        return

    if is_debrid:
        debrid_color = get_random_color(debrid_type)
        title = f"[B][COLOR {debrid_color}][{debrid_type}][/COLOR][/B]-{title}"
    else:
        title = f"[B][Uncached][/B]-{title}"

    if title not in db.database["jt:watch"]:
        db.database["jt:watch"][title] = True

    db.database["jt:lfh"][title] = {
        "timestamp": datetime.now(),
        "ids": ids,
        "tvdata": tvdata,
        "url": url,
        "is_debrid": is_debrid,
        "is_torrent": is_torrent,
        "magnet": magnet,
    }
    db.commit()


def set_watched_title(title, ids, mode=""):
    if title != "None":
        db.database["jt:lth"][title] = {
            "timestamp": datetime.now(),
            "ids": ids,
            "mode": mode,
        }
        db.commit()


def is_torrent_watched(title):
    return db.database["jt:watch"].get(title, False)


def search_fanart_tv(tvdb_id, mode="tv"):
    identifier = "{}|{}".format("fanarttv", tvdb_id)
    data = cache.get(identifier, hashed_key=True)
    if not data:
        fanart_data = search_api_fanart_tv(mode, "en", tvdb_id)
        if fanart_data:
            cache.set(
                identifier,
                data,
                timedelta(hours=get_cache_expiration() if is_cache_enabled() else 0),
                hashed_key=True,
            )
    return data


def get_cached(path, params={}):
    identifier = "{}|{}".format(path, params)
    return cache.get(identifier, hashed_key=True)


def set_cached(results, path, params={}):
    identifier = "{}|{}".format(path, params)
    cache.set(
        identifier,
        results,
        timedelta(hours=get_cache_expiration() if is_cache_enabled() else 0),
        hashed_key=True,
    )


def db_get(name, func, path, params):
    identifier = "{}|{}".format(path, params)
    data = cache.get(identifier, hashed_key=True)
    if not data:
        if name == "search_api":
            data = func()
        cache.set(
            identifier,
            data,
            timedelta(hours=get_cache_expiration() if is_cache_enabled() else 0),
            hashed_key=True,
        )
    return data


def tmdb_get(path, params={}):
    identifier = "{}|{}".format(path, params)
    data = cache.get(identifier, hashed_key=True)
    if not data:
        if path == "search_tv":
            data = Search().tv_shows(params)
        elif path == "search_movie":
            data = Search().movies(params)
        elif path == "movie_details":
            data = Movie().details(params)
        elif path == "tv_details":
            data = TV().details(params)
        elif path == "season_details":
            data = Season().details(params["id"], params["season"])
        elif path == "movie_genres":
            data = Genre().movie_list()
        elif path == "tv_genres":
            data = Genre().tv_list()
        elif path == "discover_movie":
            discover = Discover()
            data = discover.discover_movies(params)
        elif path == "discover_tv":
            discover = Discover()
            data = discover.discover_tv_shows(params)
        elif path == "trending_movie":
            trending = Trending()
            data = trending.movie_week(page=params)
        elif path == "trending_tv":
            trending = Trending()
            data = trending.tv_day(page=params)
        elif path == "find":
            data = Find().find_by_tvdb_id(params)
        cache.set(
            identifier,
            data,
            timedelta(hours=get_cache_expiration() if is_cache_enabled() else 0),
            hashed_key=True,
        )
    return data


def get_movie_data(id):
    details = tmdb_get("movie_details", id)
    imdb_id = details.external_ids.get("imdb_id")
    runtime = details.runtime
    return imdb_id, "", runtime


def get_tv_data(id):
    details = tmdb_get("tv_details", id)
    imdb_id = details.external_ids.get("imdb_id")
    tvdb_id = details.external_ids.get("tvdb_id")
    return imdb_id, tvdb_id


# This method was taken from script.elementum.jackett
def get_random_color(provider_name):
    hash = hashlib.sha256(provider_name.encode("utf")).hexdigest()
    colors = []

    spec = 10
    for i in range(0, 3):
        offset = spec * i
        rounded = round(
            int(hash[offset : offset + spec], 16) / int("F" * spec, 16) * 255
        )
        colors.append(int(max(rounded, PROVIDER_COLOR_MIN_BRIGHTNESS)))

    while (sum(colors) / 3) < PROVIDER_COLOR_MIN_BRIGHTNESS:
        for i in range(0, 3):
            colors[i] += 10

    for i in range(0, 3):
        colors[i] = f"{colors[i]:02x}"

    return "FF" + "".join(colors).upper()


def get_colored_languages(languages):
    if languages:
        colored_languages = []
        for lang in languages:
            lang_color = get_random_color(lang)
            colored_lang = f"[B][COLOR {lang_color}][{lang}][/COLOR][/B]"
            colored_languages.append(colored_lang)
        return colored_languages


def get_full_languages(languages):
    if languages:
        return ", " + ", ".join(languages)
    return ""


def clear_tmdb_cache():
    db.database["jt:tmdb"] = {}
    db.commit()


def clear_all_cache():
    cache.clean_all()
    db.database["jt:tmdb"] = {}
    db.commit()


def clear(type=""):
    dialog = Dialog()
    confirmed = dialog.yesno(
        "Clear History",
        "Do you want to clear this history list?.",
    )
    if confirmed:
        if type == "lth":
            db.database["jt:lth"] = {}
        else:
            db.database["jt:lfh"] = {}
        db.commit()
        container_refresh()


def limit_results(results):
    indexer = get_setting("indexer")
    if indexer == Indexer.JACKETT:
        limit = get_int_setting("jackett_results_per_page")
    elif indexer == Indexer.PROWLARR:
        limit = get_int_setting("prowlarr_results_per_page")
    elif indexer == Indexer.TORRENTIO:
        limit = get_int_setting("torrentio_results_per_page")
    elif indexer == Indexer.ELHOSTED:
        limit = get_int_setting("elfhosted_results_per_page")
    return results[:limit]


def get_description_length():
    indexer = get_setting("indexer")
    if indexer == Indexer.JACKETT:
        desc_length = "jackett_desc_length"
    elif indexer == Indexer.PROWLARR:
        desc_length = "prowlarr_desc_length"
    elif indexer == Indexer.TORRENTIO:
        desc_length = "torrentio_desc_length"
    elif indexer == Indexer.ELHOSTED:
        desc_length = "elfhosted_desc_length"
    return int(get_setting(desc_length))


def remove_duplicate(results):
    seen_values = []
    result_dict = []
    for res in results:
        if res not in seen_values:
            result_dict.append(res)
            seen_values.append(res)
    return result_dict


def process_results(res, mode, episode_name, episode, season):
    res = remove_duplicate(res)
    res = limit_results(res)
    if mode == "tv":
        res = filter_by_episode(res, episode_name, episode, season)
    res = filter_by_quality(res)
    res = sort_results(res)
    return res


def sort_by_priority_language(results):
    priority_lang = get_setting("torrentio_priority_lang")
    counter = 0
    for res in results:
        if "languages" in res and priority_lang in res["languages"]:
            results.remove(res)
            results.insert(counter, res)
            counter += 1
    return results


def filter_by_priority_language(results):
    indexer = get_setting("indexer")
    if indexer == Indexer.TORRENTIO:
        filtered_results = []
        priority_lang = get_setting("torrentio_priority_lang")
        for res in results:
            if priority_lang in res["languages"]:
                filtered_results.append(res)
        return filtered_results


def sort_results(results):
    indexer = get_setting("indexer")
    if indexer == Indexer.JACKETT:
        sort_by = get_setting("jackett_sort_by")
    elif indexer == Indexer.PROWLARR:
        sort_by = get_setting("prowlarr_sort_by")
    elif indexer == Indexer.TORRENTIO:
        sort_by = get_setting("torrentio_sort_by")
    elif indexer == Indexer.ELHOSTED:
        sort_by = get_setting("elfhosted_sort_by")

    if sort_by == "Seeds":
        sort_results = sorted(results, key=lambda r: int(r["seeders"]), reverse=True)
    elif sort_by == "Size":
        sort_results = sorted(results, key=lambda r: r["size"], reverse=True)
    elif sort_by == "Date":
        sort_results = sorted(results, key=lambda r: r["publishDate"], reverse=True)
    elif sort_by == "Quality":
        sort_results = sorted(results, key=lambda r: r["Quality"], reverse=True)
    elif sort_by == "Cached":
        sort_results = sorted(results, key=lambda r: r["debridCached"], reverse=True)
    elif sort_by == "None":
        sort_results = results
    elif sort_by == "Language":
        sort_results = sort_by_priority_language(results)

    return sort_results


def filter_by_episode(results, episode_name, episode_num, season_num):
    episode_num = f"{int(episode_num):02}"
    season_num = f"{int(season_num):02}"

    filtered_episodes = []
    pattern1 = "S%sE%s" % (season_num, episode_num)
    pattern2 = "%sx%s" % (season_num, episode_num)
    pattern3 = "\s%s\s" % (episode_num)
    pattern4 = "\.S%s" % (season_num)
    pattern5 = "\.S%sE%s" % (season_num, episode_num)
    pattern6 = "\sS%sE%s\s" % (season_num, episode_num)

    pattern = "|".join(
        [pattern1, pattern2, pattern3, pattern4, pattern5, pattern6, episode_name]
    )

    for res in results:
        title = res["title"]
        match = re.search(f"r{pattern}", title)
        if match:
            filtered_episodes.append(res)
    return filtered_episodes


def filter_by_quality(results):
    quality_720p = []
    quality_1080p = []
    quality_4k = []
    no_quarlity = []

    for res in results:
        title = res["title"]
        if "480p" in title:
            res["quality_title"] = "[B][COLOR orange]480p - [/COLOR][/B]" + res["title"]
            res["Quality"] = "480p"
            quality_720p.append(res)
        elif "720p" in title:
            res["quality_title"] = "[B][COLOR orange]720p - [/COLOR][/B]" + res["title"]
            res["Quality"] = "720p"
            quality_720p.append(res)
        elif "1080p" in title:
            res["quality_title"] = "[B][COLOR blue]1080p - [/COLOR][/B]" + res["title"]
            res["Quality"] = "1080p"
            quality_1080p.append(res)
        elif "2160" in title:
            res["quality_title"] = "[B][COLOR yellow]4k - [/COLOR][/B]" + res["title"]
            res["Quality"] = "4k"
            quality_4k.append(res)
        else:
            res["quality_title"] = "[B][COLOR yellow]N/A - [/COLOR][/B]" + res["title"]
            res["Quality"] = "N/A"
            no_quarlity.append(res)

    combined_list = quality_4k + quality_1080p + quality_720p + no_quarlity
    return combined_list


def supported_video_extensions():
    media_types = getSupportedMedia("video")
    return media_types.split("|")


def is_video(s):
    return s.lower().endswith(video_extensions)


def get_info_hash_from_magnet(magnet):
    return Magnet.from_string(magnet).infohash


def is_magnet_link(link):
    if link.startswith("magnet:?"):
        return link


def is_url(url):
    return bool(re.match(URL_REGEX, url))


def info_hash_to_magnet(info_hash):
    return f"magnet:?xt=urn:btih:{info_hash}"


def get_state_string(state):
    if 0 <= state <= 9:
        return translation(30650 + state)
    return translation(30660)


def get_service_address():
    return (
        "127.0.0.1"
        if get_torrest_setting("service_enabled")
        else get_torrest_setting("service_address")
    )


def get_credentials():
    return get_torrest_setting("auth_username"), get_torrest_setting("auth_password")


def ssl_enabled():
    return get_torrest_setting("ssl_connection")


def get_port():
    return get_torrest_setting("port")


def unicode_flag_to_country_code(unicode_flag):
    if len(unicode_flag) != 2:
        return "Invalid flag Unicode"

    first_letter = unicodedata.name(unicode_flag[0]).replace(
        "REGIONAL INDICATOR SYMBOL LETTER ", ""
    )
    second_letter = unicodedata.name(unicode_flag[1]).replace(
        "REGIONAL INDICATOR SYMBOL LETTER ", ""
    )

    country_code = first_letter.lower() + second_letter.lower()
    return country_code
