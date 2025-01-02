import json
from requests import Session
from lib.utils.kodi_utils import translation


class Jackgram:
    def __init__(self, host, notification):
        self.host = host.rstrip("/")
        self._notification = notification
        self.session = Session()

    def search(self, tmdb_id, query, mode, media_type, season, episode):
        try:
            if mode == "tv" or media_type == "tv":
                url = f"{self.host}/stream/series/{tmdb_id}:{season}:{episode}.json"
            elif mode == "movies" or media_type == "movies":
                url = f"{self.host}/stream/movie/{tmdb_id}.json"
            else:
                url = f"{self.host}/search?query={query}"

            res = self.session.get(url, timeout=10)
            if res.status_code != 200:
                return
            if mode in ["tv", "movies"]:
                return self.parse_response(res)
            else:
                return self.parse_response_search(res)
        except Exception as e:
            self._notification(f"{translation(30232)}: {str(e)}")

    def get_latest(self, page):
        url = f"{self.host}/stream/latest?page={page}"
        res = self.session.get(url, timeout=10)
        if res.status_code != 200:
            return
        return res.json()

    def parse_response(self, res):
        res = json.loads(res.text)
        results = []
        for item in res["streams"]:
            results.append(
                {
                    "title": item["title"],
                    "type": "Direct",
                    "indexer": item["name"],
                    "size": item["size"],
                    "publishDate": item["date"],
                    "duration": item["duration"],
                    "downloadUrl": item["url"],
                }
            )
        return results

    def parse_response_search(self, res):
        res = json.loads(res.text)
        results = []
        for item in res["results"]:
            for file in item["files"]:
                date = "" if file["date"] == None else file["date"]
                results.append(
                    {
                        "title": file["title"],
                        "type": "Direct",
                        "indexer": file["name"],
                        "size": file["size"],
                        "publishDate": date,
                        "duration": file["duration"],
                        "downloadUrl": file["url"],
                    }
                )
        return results
