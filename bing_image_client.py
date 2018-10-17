import logging
import random
import requests


class BingImageClient:
    """
    Simple class to search for GIFs that match certain terms
    """

    SEARCH_URL = "https://api.cognitive.microsoft.com/bing/v7.0/images/search"

    def __init__(self, api_token, logger=None):
        self.api_token = api_token
        self.logger = logger or logging.getLogger("BingImageClient")

    def random(self, terms, rating="G", lang="en-US"):
        """
        Return a random image that matches the given terms, or None if no matches are found

        :param terms:
        :param rating:
        :param lang:
        :return:
        """
        results = self.search(terms, 50, rating, lang)
        return random.choice(results) if results else None

    def search(self, terms, search_limit=10, rating="G", lang="en-US"):
        """
        Find GIFs that match the given terms and return a collection of URLS

        :param terms:
        :param search_limit:
        :param rating:
        :param lang:
        :return:
        """
        full_results = self.search_full(terms, search_limit, rating, lang)
        return [x.get("contentUrl") for x in full_results if x.get("contentUrl")]

    def search_full(self, terms, search_limit=10, rating="G", lang="en-US"):
        """
        Find GIFs that match the given terms and return the full GLIPHY result

        :param terms:
        :param search_limit:
        :param rating:
        :param lang:
        :return:
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
           "imageType": "Photo"  # "Photo", "Clipart", "AnimatedGif", "AnimatedGifHttps"
        }
        response = requests.get(self.SEARCH_URL, headers=headers, params=params)
        if not response or response.status_code != 200:
            self.logger.info("search failed: %s", repr(response))
            return None
        results = response.json().get("value", [])
        self.logger.info("search found %d images", len(results))
        return results


if __name__ == "__main__":
    import pprint
    import webbrowser

    print("here")
    FORMAT = "%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    Key1 = "52df9faf6d1b4d0cb1f2e30f6cf5a968"
    gc = BingImageClient(Key1)
    resp = gc.search("funny dad joke", search_limit=10)

    pprint.pprint(resp)
    for x in resp:
        webbrowser.open_new_tab(x)
