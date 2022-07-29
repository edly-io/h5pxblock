"""XBlock to play H5P content in open edX."""

import json
import os
import logging
import pkg_resources

from django.conf import settings
from django.core.files.storage import default_storage
from django.template import Context, Template
from django.utils import timezone
from webob import Response

from xblock.completable import CompletableXBlockMixin
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Scope, String, Boolean, Integer, Dict, DateTime, UNIQUE_ID
from xblock.fragment import Fragment
from h5pxblock.utils import str2bool, unpack_and_upload_on_cloud, unpack_package_local_path


# Make '_' a no-op so we can scrape strings
_ = lambda text: text

log = logging.getLogger(__name__)

H5P_ROOT = os.path.join(settings.MEDIA_ROOT, "h5pxblockmedia")
H5P_URL = os.path.join(settings.MEDIA_URL, "h5pxblockmedia")


@XBlock.wants('user')
@XBlock.wants('i18n')
class H5PPlayerXBlock(XBlock, CompletableXBlockMixin):
    """
    H5P XBlock provides ability to host and play h5p content inside open edX course.
    It also provides ability to route xAPI event to LRS.
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
        display_name=_("Uploade H5P content"),
        help=_("Upload H5P content"),
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

    is_scorable = Boolean(
        display_name=_("Is Scorable"),
        help=_(
            "Select True if this component will save score"
        ),
        default=False,
        scope=Scope.settings,
    )

    save_freq = Integer(
        display_name=_("User content state save frequency"),
        help=_(
            "How often current user content state should be autosaved (in seconds). \
                Set it to zero if you don't want to save content state."
        ),
        default=0,
        scope=Scope.settings,
    )

    interaction_data = Dict(
        help=_("User previous content interaction states"),
        default={},
        scope=Scope.user_state
    )

    h5p_content_meta = Dict(scope=Scope.content)
    has_author_view = True

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    @property
    def store_content_on_local_fs(self):
        return default_storage.__class__.__name__ == 'FileSystemStorage'

    @property
    def get_block_path_prefix(self):
        # In worbench self.location is a mock object so we have to use usage_id
        if 'Workbench' in self.runtime.__class__.__name__:
            return str(self.scope_ids.usage_id)
        else:
            return os.path.join(self.location.org, self.location.course, self.location.block_id)

    @property
    def h5p_content_url(self):
        return "{}/{}".format(H5P_URL, self.get_block_path_prefix)

    @property
    def local_storage_path(self):
        return os.path.join(
            H5P_ROOT, self.get_block_path_prefix
        )

    @property
    def cloud_storage_path(self):
        return os.path.join(
            'h5pxblockmedia', self.get_block_path_prefix
        )

    def get_context_studio(self):
        return {
            "field_display_name": self.fields["display_name"],
            "h5p_content_json_path": self.fields["h5p_content_json_path"],
            "show_frame": self.fields["show_frame"],
            "show_copyright": self.fields["show_copyright"],
            "show_h5p": self.fields["show_h5p"],
            "show_fullscreen": self.fields["show_fullscreen"],
            "is_scorable": self.fields["is_scorable"],
            "save_freq": self.fields["save_freq"],
            "h5p_xblock": self,
        }

    def author_view(self, context=None):
        html = self.render_template("static/html/author_view.html", context)
        frag = Fragment(html)
        return frag

    def studio_view(self, context=None):
        context = self.get_context_studio()
        template = self.render_template("static/html/studio.html", context)
        frag = Fragment(template)
        frag.add_css(self.resource_string("static/css/studio.css"))
        frag.add_javascript(self.resource_string("static/js/src/studio.js"))
        frag.initialize_js(
            "H5PStudioXBlock",
            json_args={
                "uploading_txt": self.ugettext("Uploading"),
                "uploaded_txt": self.ugettext("Uploaded"),
                "extracting_txt": self.ugettext("Extracting")
            }
        )
        return frag

    def student_view(self, context=None):
        """
        The primary view of the H5PPlayerXBlock, shown to students
        when viewing courses.
        """
        context = {
            "h5pblock": self,
        }
        template = self.render_template("static/html/h5pxblock.html", context)
        frag = Fragment(template)
        frag.add_javascript_url('https://cdn.jsdelivr.net/npm/h5p-standalone@3.5.1/dist/main.bundle.js')
        frag.add_javascript(self.resource_string("static/js/src/h5pxblock.js"))
        user_service = self.runtime.service(self, 'user')
        user = user_service.get_current_user()
        save_freq = self.save_freq if self.save_freq > 0 else False
        frag.initialize_js(
            'H5PPlayerXBlock',
            json_args={
                "player_id": self.player_id,
                "frame": self.show_frame,
                "copyright": self.show_copyright,
                "icon": self.show_h5p,
                "fullScreen": self.show_fullscreen,
                "saveFreq": save_freq,
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

        return Response(json.dumps(self.interaction_data))

    @XBlock.handler
    def studio_submit(self, request, suffix=""):
        self.display_name = request.params["display_name"]
        self.show_frame = str2bool(request.params["show_frame"])
        self.show_copyright = str2bool(request.params["show_copyright"])
        self.show_h5p = str2bool(request.params["show_h5p"])
        self.show_fullscreen = str2bool(request.params["show_fullscreen"])
        self.is_scorable = str2bool(request.params["is_scorable"])
        self.save_freq = request.params["save_freq"]
        self.icon_class = "problem" if self.is_scorable else "h5p"

        if hasattr(request.params["h5p_content_bundle"], "file"):
            h5p_package = request.params["h5p_content_bundle"].file

            meta_data = {
                "name": h5p_package.name,
                "upload_time": timezone.now().strftime(DateTime.DATETIME_FORMAT),
                "size": h5p_package.size,
            }
            self.h5p_content_meta = meta_data
            if self.store_content_on_local_fs:
                unpack_package_local_path(h5p_package, self.local_storage_path)
                self.h5p_content_json_path = self.h5p_content_url
            else:
                unpack_and_upload_on_cloud(
                    h5p_package, default_storage, self.cloud_storage_path
                )
                self.h5p_content_json_path = default_storage.url(self.cloud_storage_path)

        return Response(
            json.dumps({"result": "success"}),
            content_type="application/json",
            charset="utf8",
        )

    @XBlock.json_handler
    def result_handler(self, data, suffix=''):
        """
        Handler to injest results when h5p content triggers completion or rescorable events
        """
        save_completion, save_score = False, False
        try:
            self.emit_completion(1.0)
            save_completion = True
        except BaseException as exp:
            log.error("Error while marking completion %s", exp)

        try:
            if self.is_scorable and data['result'] and data['result']['score']:
                grade_dict = {
                    'value': data['result']['score']['raw'],
                    'max_value': data['result']['score']['max'],
                    'only_if_higher': True,
                }
                self.runtime.publish(self, 'grade', grade_dict)
                save_score = True
        except BaseException as exp:
            log.error("Error while publishing score %s", exp)

        return Response(
            json.dumps({"result": {"save_completion": save_completion, "save_score": save_score}}),
            content_type="application/json",
            charset="utf8",
        )

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
