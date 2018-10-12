import logging
import random
import requests


class GliphyClient:
    """
    Simple class to search for GIFs that match certain terms
    """

    SEARCH_URL = "http://api.giphy.com/v1/gifs/search"

    def __init__(self, api_token, logger=None):
        self.api_token = api_token
        self.logger = logger or logging.getLogger("GliphyClient")

    def random(self, terms, rating="PG", lang="en-US"):
        """
        Return a random image that matches the given terms

        :param terms:
        :param rating:
        :param lang:
        :return:
        """
        return random.choice(self.search(terms, 50, rating, lang))

    def search(self, terms, search_limit=10, rating="G", lang="en"):
        """
        Find GIFs that match the given terms and return a collection of URLS

        :param terms:
        :param search_limit:
        :param rating:
        :param lang:
        :return:
        """
        full_results = self.search_full(terms, search_limit, rating, lang)
        just_urls = (x.get("images", {}).get("fixed_height_downsampled", {}).get("url") for x in full_results)
        return [x for x in just_urls if x]

    def search_full(self, terms, search_limit=10, rating="G", lang="en"):
        """
        Find GIFs that match the given terms and return the full GLIPHY result

        :param terms:
        :param search_limit:
        :param rating:
        :param lang:
        :return:
        """
        self.logger.info("searching gliphy for %s", terms)
        params = dict(q=terms, api_key=self.api_token, limit=search_limit, rating=rating, lang=lang)
        response = requests.get(self.SEARCH_URL, params=params)
        if not response or response.status_code != 200:
            self.logger.info("gliphy failed: %s", repr(response))
            return None
        results = response.json().get("data", [])
        self.logger.info("gliphy found %d images", len(results))
        return results


if __name__ == "__main__":
    import pprint
    print("here")
    FORMAT = "%(asctime)s | %(process)d | %(name)s | %(levelname)s | %(thread)d | %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    gc = GliphyClient("9sjCBr6oSL4Z1TdEvZv9hsz69cEXWZ1L")
    resp = gc.random("pug puppy funny")
    pprint.pprint(resp)
