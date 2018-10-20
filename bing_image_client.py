import logging
import random
from string import atoi

import requests


class BingImageClient:
    """
    Simple class to search for GIFs that match certain terms
    """

    # TO DO:
    # - exclude functionality should be moved to search_full()
    # - If exclude/size filter result in less than requested number, logic should search next page of results

    SEARCH_URL = "https://api.cognitive.microsoft.com/bing/v7.0/images/search"

    def __init__(self, api_token, logger=None, max_size_in_bytes=0):
        self.api_token = api_token
        self.logger = logger or logging.getLogger("BingImageClient")
        self.max_size_in_bytes = max_size_in_bytes

    def random(self, terms, rating="G", lang="en-US", exclude=[]):
        """
        Return a random image that matches the given terms, or None if no matches are found
        """
        results = self.search(terms, 100, rating, lang)
        filtered_results = [x for x in results if x not in exclude]
        return random.choice(filtered_results) if filtered_results else None

    def _content_size(self, result):
        content_size = result.get("contentSize")
        if not content_size:
            return 0
        if content_size.endswith(" B"):
            return int(content_size[:-2])
        if content_size.endswith(" KB"):
            return int(float(content_size[:-3]) * 1024)
        if content_size.endswith(" MB"):
            return int(float(content_size[:-3]) * 1024 * 1024)
        if content_size.endswith(" GB"):
            return int(float(content_size[:-3]) * 1024 * 1024 * 1024)
        # Give up
        return 0

    def search(self, terms, search_limit=10, rating="G", lang="en-US"):
        """
        Find images that match the given terms and return a collection of URLS
        """
        results = self.search_full(terms, search_limit, rating, lang) or []
        return [x.get("contentUrl") for x in results if x.get("contentUrl")]

    def search_full(self, terms, search_limit=10, rating="G", lang="en-US"):
        """
        Find image records that match the given conditions
        """
        self.logger.info("searching for %s", terms)
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_token
        }
        params = {
            "q": terms,
            "size": "large",
            "safeSearch": "Strict" if rating == "G" else "Moderate",
            "mkt": lang,
            "count": search_limit,
            #  "license": "public",
            #"imageType": "Photo"  # "Photo", "Clipart", "AnimatedGif", "AnimatedGifHttps"
        }
        response = requests.get(self.SEARCH_URL, headers=headers, params=params)
        if not response or response.status_code != 200:
            self.logger.info("search failed: %s", repr(response))
            return None
        results = response.json().get("value", [])
        self.logger.info("search found %d images", len(results))
        if len(results) and self.max_size_in_bytes:
            results = [x for x in results if self._content_size(x) < self.max_size_in_bytes]
            self.logger.info("Of those, %d images were smaller than %d bytes", len(results), self.max_size_in_bytes)
        return results


if __name__ == "__main__":
    import pprint
    import webbrowser

    print("here")
    FORMAT = "%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    Key1 = "c217198fee0c48158ff90e3d3e1d4c21"
    gc = BingImageClient(Key1, max_size_in_bytes=100*1024)
    resp = gc.search_full("impatient foot tapping", search_limit=10)

    pprint.pprint(resp)
    # for x in resp:
    #     webbrowser.open_new_tab(x)
