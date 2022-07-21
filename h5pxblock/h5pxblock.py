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
_ = lambda text: text

log = logging.getLogger(__name__)

H5P_ROOT = os.path.join(settings.MEDIA_ROOT, "h5pxblockmedia")
H5P_URL = os.path.join(settings.MEDIA_URL, "h5pxblockmedia")
MAX_WORKERS = getattr(settings, "THREADPOOLEXECUTOR_MAX_WORKERS", 10)


@XBlock.needs('user')
class H5PPlayerXBlock(StudioEditableXBlockMixin, XBlock, CompletableXBlockMixin):
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
        help=_("Path of h5p content root json"),
        default="/resource/h5pxblock/public/js/samples/audio-recorder-142-1214919",
        scope=Scope.settings,
    )

    h5p_file = String(
        display_name=_("Upload h5p file"),
        scope=Scope.settings,
    )

    h5p_file_meta = Dict(scope=Scope.content)

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
    path_index_page = String(
        display_name=_("Path to the index page in h5p file"),
        scope=Scope.settings,
    )

    has_author_view = True
    editable_fields = (
        'display_name', 'show_frame', 'show_copyright', 'show_h5p', 'show_fullscreen', 'h5p_content_json_path'
    )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def _file_storage_path(self):
        """
        Get file path of storage.
        """
        path = "h5pxblockmedia/{loc.org}/{loc.course}/{loc.block_id}".format(
            loc=self.location,
        )
        return path

    @property
    def local_storage_path(self):
        return os.path.join(
            H5P_ROOT, str(self.location.org), str(self.location.course), str(self.location.block_id)
        )

    @property
    def s3_storage(self):
        return "S3" in default_storage.__class__.__name__

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    def _unpack_files(self, h5p_file):
        """
        Unpacks zip file using unzip system utility
        """
        # Now unpack it into H5P_ROOT to serve to students later
        self._delete_local_storage()
        local_path = self.local_storage_path
        os.makedirs(local_path)

        if hasattr(h5p_file, "temporary_file_path"):
            os.system(
                "unzip {} -d {}".format(h5p_file.temporary_file_path(), local_path)
            )
        else:
            temporary_path = os.path.join(H5P_ROOT, h5p_file.name)
            temporary_zip = open(temporary_path, "wb")
            h5p_file.open()
            temporary_zip.write(h5p_file.read())
            temporary_zip.close()
            os.system("unzip {} -d {}".format(temporary_path, local_path))
            os.remove(temporary_path)

    def get_sha1(self, file_descriptor):
        """
        Get file hex digest (fingerprint).
        """
        block_size = 8 * 1024
        sha1 = hashlib.sha1()
        # changes made for juniper (python 3.5)
        while True:
            block = file_descriptor.read(block_size)
            if not block:
                break
            sha1.update(block)
        file_descriptor.seek(0)
        return sha1.hexdigest()

    def update_subdir_permissions(self):
        """
        Extends existing permissions of all the the sub-directories with the Owner Execute permission (S_IXUSR).

        All sub-directories of the h5p-package must have executable permissions for the Directory Owner otherwise
        Studio will raise Permission Denied error on scorm package upload.
        """
        for path, subdirs, files in os.walk(self.local_storage_path):
            for name in subdirs:
                dir_path = os.path.join(path, name)
                st = os.stat(dir_path)
                os.chmod(dir_path, st.st_mode | stat.S_IXUSR)

    def set_fields_xblock(self):

        self.path_index_page = "index.html"
        try:
            tree = ET.parse("{}/imsmanifest.xml".format(self.local_storage_path))
        except IOError:
            pass
        else:
            namespace = ""
            for node in [
                node
                for _, node in ET.iterparse(
                    "{}/imsmanifest.xml".format(self.local_storage_path),
                    events=["start-ns"],
                )
            ]:
                if node[0] == "":
                    namespace = node[1]
                    break
            root = tree.getroot()

            if namespace:
                resource = root.find(
                    "{{{0}}}resources/{{{0}}}resource".format(namespace)
                )
                schemaversion = root.find(
                    "{{{0}}}metadata/{{{0}}}schemaversion".format(namespace)
                )
            else:
                resource = root.find("resources/resource")
                schemaversion = root.find("metadata/schemaversion")

            if resource is not None:
                self.path_index_page = resource.get("href")

        self.h5p_file = os.path.join(
            H5P_URL,
            "{}/{}/{}/{}".format(
                self.location.org,
                self.location.course,
                self.location.block_id,
                self.path_index_page,
            ),
        )

    def _upload_file(self, file_path):
        self._fix_content_type(file_path)
        path = self.get_remote_path(file_path)
        with open(file_path, "rb") as content_file:
            default_storage.save(path, content_file)
        log.info('S3: "{}" file stored at "{}"'.format(file_path, path))

    def _delete_existing_files(self, path):
        """
        Recusively delete all files under given path
        """
        dir_names, file_names = default_storage.listdir(path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            tracker_futures = []
            for file_name in file_names:
                file_path = "/".join([path, file_name])
                tracker_futures.append(
                    executor.submit(default_storage.delete, file_path)
                )
                log.info('S3: "{}" file deleted'.format(file_path))

        for dir_name in dir_names:
            dir_path = "/".join([path, dir_name])
            self._delete_existing_files(dir_path)

    def _store_unziped_files_to_s3(self):
        self._delete_existing_files(self._file_storage_path())
        local_path = self.local_storage_path
        file_paths = []
        for path, subdirs, files in os.walk(local_path):
            for name in files:
                file_paths.append(os.path.join(path, name))

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            tracker_futures = {
                executor.submit(self._upload_file, file_path): file_path
                for file_path in file_paths
            }
            for future in concurrent.futures.as_completed(tracker_futures):
                file_path = tracker_futures[future]
                try:
                    future.result()
                except Exception as exc:
                    log.info(
                        "S3: upload of %r generated an exception: %s" % (file_path, exc)
                    )

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

    def studio_view(self, context=None):
        """
        The primary view of the H5PPlayerXBlock, shown to studio
        when viewing courses.
        """
        context_html = self.get_context_studio()
        template = self.render_template("static/html/studio.html", context_html)
        frag = Fragment(template)
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
    def studio_submit(self, request, suffix=""):
        if hasattr(request.params["file"], "file"):
            h5p_file = request.params["file"].file

            # First, save scorm file in the storage for mobile clients
            self.h5p_file_meta["sha1"] = self.get_sha1(h5p_file)
            self.h5p_file_meta["name"] = h5p_file.name
            self.h5p_file_meta["path"] = self._file_storage_path()
            self.h5p_file_meta["last_updated"] = timezone.now().strftime(
                DateTime.DATETIME_FORMAT
            )
            self.h5p_file_meta["size"] = h5p_file.size
            self._unpack_files(h5p_file)
            self.update_subdir_permissions()
            self.set_fields_xblock()
            if self.s3_storage:
                self._store_unziped_files_to_s3()
                # Removed locally unzipped files once we have store them on S3
                self._delete_local_storage()

        # changes made for juniper (python 3.5)
        return Response(
            json.dumps({"result": "success"}),
            content_type="application/json",
            charset="utf8",
        )

    def _delete_local_storage(self):
        path = self.local_storage_path
        if os.path.exists(path):
            shutil.rmtree(path),

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

    def get_context_studio(self):
        return {
            "field_h5p_file": self.fields["h5p_file"],
            "h5p_xblock": self,
        }
