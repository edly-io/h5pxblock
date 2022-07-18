"""XBlock to play H5P content in open edX."""

import concurrent.futures
import json
import hashlib
import mimetypes
import re
import os
import stat
import logging
import pkg_resources
import shutil
import xml.etree.ElementTree as ET

from django.conf import settings
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone
from webob import Response

from xblock.completable import CompletableXBlockMixin
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Float, Boolean, Dict, DateTime, Integer, UNIQUE_ID
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin


# Make '_' a no-op so we can scrape strings
# TODO: use i18n service
_ = lambda text: text

log = logging.getLogger(__name__)

H5P_ROOT = os.path.join(settings.MEDIA_ROOT, "h5pxblockmedia")
H5P_URL = os.path.join(settings.MEDIA_URL, "h5pxblockmedia")
MAX_WORKERS = getattr(settings, "THREADPOOLEXECUTOR_MAX_WORKERS", 10)


@XBlock.needs('user')
class H5PPlayerXBlock(StudioEditableXBlockMixin, XBlock, CompletableXBlockMixin):
    """
    H5P XBlock provides ability to host and play h5p content inside open edX course.
    It also provide ability to route xAPI event to LRS.
    """
    player_id = String(
        display_name=_("H5P Player Id"),
        help=_("Unique ID for player instance"),
        default=UNIQUE_ID,
        scope=Scope.settings,
    )

    display_name = String(
        display_name=_("Display Name"),
        help=_("Display name for this module"),
        default="H5P Content",
        scope=Scope.settings,
    )

    h5p_content_json_path = String(
        help=_("Path of h5p content root json"),
        default="/resource/h5pxblock/public/js/samples/multiple-choice-713",
        scope=Scope.settings,
    )

    show_frame = Boolean(
        display_name=_("Show H5P player frame"),
        help=_("whether to show H5P player frame and button"),
        default=False,
        scope=Scope.settings
    )

    show_copyright = Boolean(
        display_name=_("Show copyright button"),
        help=_("whether to show copyright button"),
        default=False,
        scope=Scope.settings
    )

    show_h5p = Boolean(
        display_name=_("Show h5p icon"),
        help=_("whether to show h5p icon"),
        default=False,
        scope=Scope.settings
    )

    show_fullscreen = Boolean(
        display_name=_("Show fullscreen button"),
        help=_("whether to show fullscreen button"),
        default=False,
        scope=Scope.settings
    )

    interaction_data = Dict(
        help=_("User previous content interaction states"),
        default={},
        scope=Scope.user_state
    )

    has_author_view = True
    editable_fields = (
        'display_name', 'show_frame', 'show_copyright', 'show_h5p', 'show_fullscreen',
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the H5PPlayerXBlock, shown to students
        when viewing courses.
        """
        html = self.resource_string("static/html/h5pxblock.html")
        frag = Fragment(html.format(h5pblock=self))
        frag.add_javascript_url('https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/main.bundle.js')
        frag.add_javascript(self.resource_string("static/js/src/h5pxblock.js"))
        user_service = self.runtime.service(self, 'user')
        user = user_service.get_current_user()
        frag.initialize_js(
            'H5PPlayerXBlock',
            json_args={
                ""
                "player_id": self.player_id,
                "frame": self.show_frame,
                "copyright": self.show_copyright,
                "icon": self.show_h5p,
                "fullScreen": self.show_fullscreen,
                "user_full_name": user.full_name,
                "user_email": user.emails[0],
                "userData": json.dumps(self.interaction_data),
                "customJsPath": self.runtime.local_resource_url(self, "public/js/h5pcustom.js"),
                "h5pJsonPath": self.h5p_content_json_path
            }
        )
        return frag

    @XBlock.handler
    def user_interaction_data(self, request, suffix=''):
        """
        Handles to retrieve and save user interactions with h5p content
        """
        if request.method == "POST":
            try:
                data_json = json.loads(request.POST['data'])
                self.interaction_data = data_json
            except ValueError:
                return JsonHandlerError(400, "Invalid JSON").get_response()
        # import pdb; pdb.set_trace()
        return Response(json.dumps(self.interaction_data))


    @XBlock.json_handler
    def finish_handler(self, data, suffix=''):
        """
        Handler to injest results when h5p content triggers finish event
        """
        # TODO:
        return {"data": data}

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("H5PPlayerXBlock",
             """<h5pxblock/>
             """),
            ("Multiple H5PPlayerXBlock",
             """<vertical_demo>
                <h5pxblock/>
                <h5pxblock/>
                <h5pxblock/>
                </vertical_demo>
             """),
        ]
