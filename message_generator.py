import random

import toolbox
from toolbox import nested_get


class StateDefn:
    def __init__(self, next_state=None, no_result_state=None, dialog_options=[]):
        self.next_state = next_state
        self.no_result_state = no_result_state or "no-result"
        self.dialog_options = dialog_options

class DialogOption:
    def __init__(self, dialogue, prompt=None, search=None, image_list=None):
        self.search = search
        self.prompt = prompt or "Keep this one?"
        self.dialogue = dialogue
        self.image_list = image_list


cute_animals = [
    "https://i.ytimg.com/vi/opKg3fyqWt4/hqdefault.jpg",
    "http://cdn2.holytaco.com/wp-content/uploads/images/2009/12/dog-cute-baby.jpg",
    "http://1.bp.blogspot.com/-NnDHYuLcDbE/ToJ6Rd6Dl5I/AAAAAAAACa4/NzFAKfIV_CQ/s400/golden_retriever_puppies.jpg",
    "https://pbs.twimg.com/profile_images/497043545505947648/ESngUXG0.jpeg",
    "https://assets.rbl.ms/10706353/980x.jpg",
    "http://stuffpoint.com/dogs/image/92783-dogs-cute-puppy.png",
    "https://groomarts.com/assets/images/_listItem/cute-puppy-1.jpg",
    "https://pbs.twimg.com/profile_images/568848749611724800/Gv5zUXpu.jpeg",
    "https://i.ytimg.com/vi/rT_I_GV_oEM/hqdefault.jpg",
    "http://2.bp.blogspot.com/-GWvh8d_O8QE/UcnF6E7hJpI/AAAAAAAAAF8/VzvEBk3cVsk/s1600/cute+pomeranian+puppies.jpg",
    "https://i.ytimg.com/vi/Gw_xvtWJ6q0/hqdefault.jpg",
    "http://3.bp.blogspot.com/-Nlispwf06Ec/UaeSfJ3jXrI/AAAAAAAALl4/UxXUUzEyUdg/s640/cute+puppies+1.jpg",
    "https://groomarts.com/assets/images/_listItem/cute-puppy-2.jpg",
    "http://1.bp.blogspot.com/-HpbjntFMqpQ/TyOKIp8s-6I/AAAAAAAAE6Q/kBJdpTqgx80/s1600/Cute-Kissing-Puppies-02.jpg",
    "https://i.ytimg.com/vi/XhDZGkA1cDk/hqdefault.jpg",
    "https://pbs.twimg.com/profile_images/555279965194051585/swMjWLLf.jpeg",
    "https://i.ytimg.com/vi/xTVDBegsddE/hqdefault.jpg",
    "http://1.bp.blogspot.com/-Jp-_R2WUyVg/USXcf-GJi_I/AAAAAAAAAQ0/7QWew3pXoM8/s400/very+cute+puppies+and+kittens09.jpg",
    "https://s-media-cache-ak0.pinimg.com/736x/61/ec/ff/61ecff9521848763390c9056ebf87191.jpg",
    "https://s-media-cache-ak0.pinimg.com/736x/e4/d4/6d/e4d46d3d4e6bec19fecf6cb168cf9375.jpg",
    "http://4.bp.blogspot.com/_HOCuXB2IC34/SuhaDCdFP_I/AAAAAAAAEhU/1SJlOOuO5og/s400/1+(www.cute-pictures.blogspot.com).jpg",
    "http://www.cutenessoverflow.com/wp-content/uploads/2016/06/a.jpg",
    "https://i0.wp.com/www.cutepuppiesnow.com/wp-content/uploads/2017/03/Maltese-Puppy-2.jpg",
    "https://wallpapercave.com/wp/AYWg3iu.jpg",
]

state_definitions = {
    "initial": StateDefn("normal", dialog_options=[
        DialogOption("I found this photo using the following search terms: {search_terms}.", "Do you want to keep this picture?")
    ]),
    "no-result": StateDefn("random", no_result_state="random", dialog_options=[
        DialogOption("I have no idea what this channel is about. So here's a cute animal photo.", search="cute puppies")
    ]),
    "random": StateDefn("impatient", dialog_options=[
        DialogOption("How about a nice landscape?", search="beautiful landscape"),
        DialogOption("How about a nice moon scape?", search="beautiful moonscape"),
        DialogOption("This comes from the weird world of the microscopic.", search="beautiful microscopic"),
        DialogOption("I don't think it's relevant but it is pretty", search="most beautiful photos"),
    ]),
    "normal": StateDefn("impatient", dialog_options=[
        DialogOption("What about this one?"),
        DialogOption("I like this one. What about you?"),
        DialogOption("Let's try something a little different."),
        DialogOption("Tough crowd! What about this one?"),
    ]),
    "impatient": StateDefn("final", dialog_options=[
        DialogOption("A bad decision is better than no decision.", search="inspiration quick decision"),
        DialogOption("I found 15 quotes about indecision but I couldn't decide which to show you.", search="demotivational indecision"),
        DialogOption("Having reached the end of good taste, we now reach into modern art.", search="weird modern art"),
        DialogOption("Modern art can be exceedingly strange.", search="horrible modern art"),
    ]),
    "final": StateDefn("end", dialog_options=[
        DialogOption("Ok, ok, this is the last attempt.", search="beautiful geometric designs"),
        DialogOption("Will you please make up your mind? I have other things to do.", search="impatient foot tapping"),
    ]),
    "end": StateDefn("terminated", dialog_options=[
        DialogOption("No kidding. This is the final choice. Surely you like this cute animal?", image_list=cute_animals)
    ])
}

COLORS = ["#ffc100", "#c356ea", "#8ff243", "#71aef2", "#71aef2"]


class MessageGenerator:

    def __init__(self, image_searcher, logger=None):
        self.image_searcher = image_searcher
        self.logger = logger or toolbox.null_logger()
        self._state = {}

    def start(self, **kwargs):
        """
        Setup initial conditions on the state machine
        """
        self._state = {
            "previous_image_urls": [],
            "previous_dialog": [],
        }
        self._state.update(kwargs)
        self._change_state("initial")

    def get_state(self):
        """
        Return a JSON serializable object which contains the state of the generator state machine
        """
        return self._state

    def set_state(self, state):
        """
        Restore the state of the generator state machine
        """
        assert state is not None
        self._state = state

    def _get_user_mention(self, event):
        user = nested_get(event, "user", "name") or "You"
        # The following works during chat.postMessage, but the user reference isn't being parsed during chat.update
        # user_id = nested_get(event, "user", "id")
        # user_name = nested_get(event, "user", "name")
        # user = "%s <@%s>" % (user_name, user_id) if user_id and user_name else "You"
        return user

    def transition(self, action, event=None):
        """
        Calculate the new state of the generator based on the given action
        """
        self.logger.info("executing transition '%s'", action)

        # Sanity check - action is known
        if action not in {"init", "keep", "next", "stop", "random"}:
            self.logger.error("Unknown action=%s", action)
            return None

        # Sanity check -- state machine should not have terminated
        current_state_id = self._state["state_id"]
        if current_state_id == "terminated":
            self.logger.error("No further actions possible. State machine is terminated. Action=%s", action)
            return None

        if action == "init":
            return self._action_init(event)
        if action == "keep":
            return self._action_keep(event)
        if action == "next":
            return self._action_next(event)
        if action == "stop":
            return self._action_stop(event)
        if action == "random":
            return self._action_random(event)

        assert False, "It should be impossible to get here"

    def _action_init(self, event):
        self._action_next(event)

    def _action_keep(self, event):
        user = self._get_user_mention(event)
        image_url = self._state["previous_image_urls"][-1]
        title = user + " chose this as the photo for this channel :heart:"
        self._state["msg"] = self._build_msg(title, None, image_url, has_buttons=False)
        self.terminate()

    def _action_stop(self, event):
        user = self._get_user_mention(event)
        title = user + " didn't want to have a photo for this channel :disappointed:"
        self._state["msg"] = self._build_msg(title, None, None, has_buttons=False)
        self.terminate()

    def _action_random(self, event):
        self._change_state("random", event)

    def _action_next(self, event):
        current_state_id = self._state["state_id"]
        state_defn = state_definitions.get(current_state_id)
        if not state_defn:
            self.logger.error("Unknown state: %s", current_state_id)
            return None

        previous_dialog = self._state["previous_dialog"]
        # If we've exhausted the dialog options, move to our next state
        possible_dialogues = [x for x in state_defn.dialog_options if x.dialogue not in previous_dialog]
        if not possible_dialogues:
            return self._change_state(state_defn.next_state, event)
        dialog_option = random.choice(possible_dialogues)

        # Find a random image that we haven't shown before. If we can't find one, we change state.
        # Some dialog options have a fixed list of possible images, but most use an image search
        search_terms = self._state["search_terms"]
        previous_image_urls = self._state["previous_image_urls"]
        if dialog_option.image_list:
            possible_images = [x for x in dialog_option.image_list if x not in previous_image_urls]
            image_url = random.choice(possible_images) if possible_images else None
        else:
            image_url = self.image_searcher.random(dialog_option.search or search_terms, exclude=previous_image_urls)
        if not image_url:
            return self._change_state(state_defn.no_result_state, event)

        # Setup the template parameters that can be used in the messages
        variables = {
            "search_terms": " ".join(sorted(search_terms)),
            "image_url": image_url,
        }
        title = dialog_option.dialogue.format(**variables)
        prompt = dialog_option.prompt

        # Modify our state to reflect this transition
        self._state["previous_dialog"].append(dialog_option.dialogue)
        self._state["previous_image_urls"].append(image_url)
        self._state["msg"] = self._build_msg(title, prompt, image_url, has_next_buttons=(current_state_id != "end"))

    def _build_msg(self, title, prompt, image_url, has_buttons=True, has_next_buttons=True):
        image_attachment = {
            "pretext": "*" + title + "*",
            "attachment_type": "default",
            "image_url": image_url,
            "color": random.choice(COLORS),
        }
        button_keep = {
            "name": "photo",
            "text": "Yes, that's great",
            "type": "button",
            "style": "primary",
            "value": "keep"
        }
        button_next = {
            "name": "photo",
            "text": "No, show something else",
            "type": "button",
            "value": "next"
        }
        button_random = {
            "name": "photo",
            "text": "Random",
            "type": "button",
            "value": "random"
        }
        button_stop = {
            "name": "photo",
            "text": "Stop suggesting",
            "style": "danger",
            "type": "button",
            "value": "stop",
        }

        buttons_attachment = {
            "color": random.choice(COLORS),
            "title": prompt,
            "attachment_type": "default",
            "callback_id": "choose_photo",
            "actions": ([button_keep, button_next, button_random, button_stop] if has_next_buttons else
                        [button_keep, button_stop])
        }

        return {
            "attachments": [image_attachment, buttons_attachment] if has_buttons else [image_attachment]
        }

    def _change_state(self, new_state_id, event=None):
        self.logger.info("changing state from '%s' to '%s", self._state.get("state_id", "<not-set>"), new_state_id)
        self._state["state_id"] = new_state_id
        self.transition("init", event)

    def get_msg(self):
        """
        Return the slack message that should be shown for the current state
        """
        return self._state.get("msg")

    def terminate(self):
        self._state["state_id"] = "terminated"



