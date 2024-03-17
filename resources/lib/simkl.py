import os
import re
from resources.lib.api.fma_api import FindMyAnime
from resources.lib.api.simkl_api import SIMKLAPI
from resources.lib.utils.kodi import ADDON_PATH, log
from resources.lib.utils.utils import get_cached, set_cached, tmdb_get
from xbmcgui import ListItem
from xbmcplugin import addDirectoryItem, endOfDirectory

IMAGE_PATH = "https://wsrv.nl/?url=https://simkl.in/episodes/%s_w.webp"


def search_simkl_episodes(title, id, mal_id, func, plugin):
    fma = FindMyAnime()
    data = fma.get_anime_data(id, "Anilist")
    s_id = extract_season(data[0]) if data else ""
    season = s_id[0] if s_id else 1

    imdb_id = "tt0000000"
    title = re.sub(r"Season\s\d", "", title).strip()
    res = tmdb_get("search_tv", title)
    if res["results"]:
        for res in res["results"]:
            ids = res.get("genre_ids")
            if 16 in ids:  # anime category
                details = tmdb_get("tv_details", res.get("id"))
                imdb_id = details.external_ids.get("imdb_id")
                break

    _, res = search_simkl_api(id, mal_id, type="anime_episodes")

    simkl_parse_show_results(res, title, id, imdb_id, season, func, plugin)


def search_simkl_api(id, mal_id, type):
    cached_results = get_cached(type, params=(id))
    if cached_results:
        return "", cached_results

    simkl = SIMKLAPI()
    if type == "anime_ids":
        message, ids = simkl.get_mapping_ids("mal", mal_id)
        if ids:
            data = ids.get("imdb")
        else:
            data = -1

    elif type == "anime_episodes":
        message, data = simkl.get_anilist_episodes(mal_id)

    set_cached(data, type, params=(id))

    return message, data


def simkl_parse_show_results(response, title, id, imdb_id, season, func, plugin):
    for res in response:
        if res["type"] == "episode":
            ep_name = res.get("title")
            if ep_name:
                ep_name = f"{season}x{res['episode']} {ep_name}"
            else:
                ep_name = f"Episode {res['episode']}"

            episode = res["episode"]
            description = res.get("description", "")

            date = res.get("date", "")
            match = re.search(r"\d{4}-\d{2}-\d{2}", date)
            if match:
                date = match.group()

            coverImage = ""
            if res.get("img"):
                coverImage = IMAGE_PATH % res["img"]

            list_item = ListItem(label=ep_name)
            list_item.setArt(
                {
                    "poster": coverImage,
                    "icon": os.path.join(
                        ADDON_PATH, "resources", "img", "trending.png"
                    ),
                    "fanart": coverImage,
                }
            )
            list_item.setProperty("IsPlayable", "false")

            info_tag = list_item.getVideoInfoTag()
            info_tag.setMediaType("video")
            info_tag.setTitle(ep_name)
            info_tag.setFirstAired(date)
            info_tag.setPlot(description)

            addDirectoryItem(
                plugin.handle,
                plugin.url_for(
                    func,
                    mode="tv",
                    query=title,
                    ids=f"{id}, {-1}, {imdb_id}",
                    tvdata=f"{ep_name}, {episode}, {season}",
                ),
                list_item,
                isFolder=True,
            )

    endOfDirectory(plugin.handle)


def extract_season(res):
    regexes = [
        r"season\s(\d+)",
        r"\s(\d+)st\sseason(?:\s|$)",
        r"\s(\d+)nd\sseason(?:\s|$)",
        r"\s(\d+)rd\sseason(?:\s|$)",
        r"\s(\d+)th\sseason(?:\s|$)",
    ]
    s_ids = []
    for regex in regexes:
        if isinstance(res.get("title"), dict):
            s_ids += [
                re.findall(regex, name, re.IGNORECASE)
                for lang, name in res.get("title").items()
                if name is not None
            ]
        else:
            s_ids += [
                re.findall(regex, name, re.IGNORECASE) for name in res.get("title")
            ]

        s_ids += [
            re.findall(regex, name, re.IGNORECASE) for name in res.get("synonyms")
        ]

    s_ids = [s[0] for s in s_ids if s]

    if not s_ids:
        regex = r"\s(\d+)$"
        cour = False
        if isinstance(res.get("title"), dict):
            for lang, name in res.get("title").items():
                if name is not None and (
                    " part " in name.lower() or " cour " in name.lower()
                ):
                    cour = True
                    break
            if not cour:
                s_ids += [
                    re.findall(regex, name, re.IGNORECASE)
                    for lang, name in res.get("title").items()
                    if name is not None
                ]
                s_ids += [
                    re.findall(regex, name, re.IGNORECASE)
                    for name in res.get("synonyms")
                ]
        else:
            for name in res.get("title"):
                if " part " in name.lower() or " cour " in name.lower():
                    cour = True
                    break
            if not cour:
                s_ids += [
                    re.findall(regex, name, re.IGNORECASE) for name in res.get("title")
                ]
                s_ids += [
                    re.findall(regex, name, re.IGNORECASE)
                    for name in res.get("synonyms")
                ]
        s_ids = [s[0] for s in s_ids if s and int(s[0]) < 20]

    return s_ids
