# Copyright (C) 2015, Richa Sehgal
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import tempfile
import shutil
import zipfile

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import WebKit

from sugar3 import mime
from sugar3.activity import activity
from sugar3.datastore import datastore
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME

class WebConsole():
    def __init__(self, act):
        self._activity = act

        src_path = os.path.join(activity.get_bundle_path(),
                                "data/web-console.html")
        self._src_uri = "file://" + src_path

        parent_dir = os.path.join(act.get_activity_root(),
                                  "Web_Console_Files")
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        self._storage_dir = tempfile.mkdtemp(dir=parent_dir)
        self._index_html_path = os.path.join(self._storage_dir, "index.html")
        self._load_status_changed_hid = None
        self._file_path = None
        self._untitled = "untitled"
        self._title = "untitled"

        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() == self._src_uri:
            self._activity._primary_toolbar._go_webconsole.set_icon_name('run_webconsole')
            self._activity._primary_toolbar._go_webconsole.show()

    def __del__(self):
        shutil.rmtree(self._storage_dir)

    def _get_file_text(self, pattern):
        browser = self._activity._tabbed_view.props.current_browser
        frame = browser.get_main_frame()

        original_title = frame.get_title()
        if original_title is None:
            original_title = self._untitled
        text_script = \
            "var saveTextBtn = document.getElementById('internal-use-trigger-" + pattern + "-text');" \
            "saveTextBtn.click();" \
            "var savedTextDiv = document.querySelector('#internal-use-" + pattern + "-text');" \
            "var text = savedTextDiv.value; " \
            "document.title = text;"
        browser.execute_script(text_script)
        file_text = frame.get_title()

        reset_title_script = "document.title = '" + original_title + "';"
        browser.execute_script(reset_title_script)

        return file_text

    def _add_to_journal(self, file_path, mimetype):
        jobject = datastore.create()

        jobject.metadata['title'] = self._title
        jobject.metadata['description'] = "Saved from web console"

        jobject.metadata['mime_type'] = mimetype
        jobject.file_path = file_path
        datastore.write(jobject)

    def _load_status_changed_cb(self, widget, param):
        status = widget.get_load_status()
        if status == WebKit.LoadStatus.FINISHED:
            self._open_file_path(self._file_path)
            browser = self._activity._tabbed_view.props.current_browser
            browser.disconnect(self._load_status_changed_hid)
            self._file_path = None

    def _open_with_source(self, file_path):
        browser = self._activity._tabbed_view.props.current_browser
        browser.load_uri(self._src_uri);
        browser.grab_focus();
        self._file_path = file_path

        self._load_status_changed_hid = browser.connect(
            'notify::load-status', self._load_status_changed_cb)

    def _open_empty(self):
        browser = self._activity._tabbed_view.props.current_browser
        browser.load_uri(self._src_uri);
        browser.grab_focus();
        # Set title
        fill_title_script = "document.title = '" + self._title + "';"
        browser.execute_script(fill_title_script)

    def open_new_tab(self):
        self._activity._primary_toolbar._go_webconsole.set_icon_name('run_webconsole')
        self._activity._primary_toolbar._go_webconsole.show()
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() == self._src_uri:
            self.run()
        else:
            browser.get_source(self._open_with_source, self._open_empty)

    def run(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Save a file from Web Console")
            return
        file_text = self._get_file_text('run')
        # Write to file
        with open(self._index_html_path, 'w') as f:
            f.write(file_text)
        text_script = \
            "var iframe = document.getElementById('iframe');" \
            "iframe.src = '" + self._index_html_path + "';"
        browser.execute_script(text_script)
        # Set title
        title = self._escape_string(self._get_title(file_text))
        if title != self._untitled:
            self._title = title
        fill_title_script = "document.title = '" + self._title + "';"
        browser.execute_script(fill_title_script)

    def save_file(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Save a file from Web Console")
            return
        file_text = self._get_file_text('save')
        # Write to file
        with open(self._index_html_path, 'w') as f:
            f.write(file_text)
        num_files = len([f for f in os.listdir(self._storage_dir)])
        if num_files == 1:
            path = self._index_html_path
            mimetype = "text/html"
        else:
            save_name = os.path.basename(os.path.normpath(self._storage_dir))
            path = shutil.make_archive(save_name, 'zip', self._storage_dir)
            mimetype = "application/zip"
        # Set title
        title = self._escape_string(self._get_title(file_text))
        if title != self._untitled:
            self._title = title
        fill_title_script = "document.title = '" + self._title + "';"
        browser.execute_script(fill_title_script)
        self._add_to_journal(path, mimetype)

    def open_file(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Open a file from Web Console")
            return

        chooser = ObjectChooser(parent=self._activity)
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    if 'mime_type' not in jobject.metadata or not jobject.metadata['mime_type']:
                        mimetype = Gio.content_type_guess(jobject.file_path, None)[0]
                        jobject.metadata['mime_type'] = mimetype
                    else:
                        mimetype = jobject.metadata['mime_type']

                    if mimetype == 'application/zip':
                        zip_object = zipfile.ZipFile(jobject.file_path, 'r')
                        valid = False
                        for name in zip_object.namelist():
                            if name == 'index.html':
                                valid = True
                                break;
                        if not valid:
                            self._activity._alert("No index.html file in the zip folder.")
                            return
                        zip_object.extractall(self._storage_dir)
                    elif mimetype == 'text/html':
                        shutil.copyfile(jobject.file_path, self._index_html_path)
                    else:
                        self._activity._alert("Only zip or html file can be opened.")
                        return
                    self._open_file_path(self._index_html_path)
                    title = jobject.metadata.get('title', self._untitled)
                    if title != self._untitled and self._title == self._untitled:
                        self._title = title
                        fill_title_script = "document.title = '" + self._title + "';"
                        browser.execute_script(fill_title_script)
        finally:
            chooser.destroy()
            del chooser

    def add_image(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Open a file from Web Console")
            return
        chooser = ObjectChooser(parent=self._activity,
                                what_filter=mime.GENERIC_TYPE_IMAGE,
                                filter_type=FILTER_TYPE_GENERIC_MIME)
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    image_name = self._basename_strip(jobject)
                    image_path = os.path.join(self._storage_dir, image_name)
                    shutil.copyfile(jobject.file_path, image_path)
        finally:
            chooser.destroy()
            del chooser

    def _get_javascript_input(self, data):
        start_head = data.find("<head>")
        end_head = data.find("</head>")
        start_script_tag = data.find("<script")
        if start_script_tag < 0 or start_head < 0 or start_head > end_head:
            return ""
        if len(data) == start_script_tag + 7:
            return ""
        end_script_tag = data.find(">", start_script_tag)
        end_script = data.find("</script>")
        if (start_head > start_script_tag or end_head < end_script or
                end_script_tag > end_script):
            return ""
        if (data.find("src=", start_script_tag, end_script_tag) > 0 or
                data.find("src =", start_script_tag, end_script_tag) > 0):
            return ""
        return data[end_script_tag + 1 : end_script]

    def _get_css_input(self, data):
        start_head = data.find("<head>")
        end_head = data.find("</head>")
        start_style_tag = data.find("<style")
        if start_style_tag < 0 or start_head < 0 or start_head > end_head:
            return ""
        if len(data) == start_style_tag + 6:
            return ""
        end_style_tag = data.find(">", start_style_tag)
        end_style = data.find("</style>")
        if (start_head > start_style_tag or end_head < end_style or
                end_style_tag > end_style):
            return ""
        return data[end_style_tag + 1 : end_style]

    def _get_html_input(self, data):
        start = data.find("<body>")
        end = data.find("</body>")
        if start > -1 and end > -1 and start < end:
            return data[start + 6 : end]
        return ""

    def _get_title(self, data):
        start = data.find("<title>")
        end = data.find("</title>")
        if start > -1 and end > -1 and start < end:
            return data[start + 7 : end]
        return self._untitled

    def _escape_string(self, string):
        return string.replace("'", "\\\'").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")

    # TODO(richa): Change comments like <!-- to /* for JS.
    def _open_file_path(self, file_path):
        browser = self._activity._tabbed_view.props.current_browser
        f = open(file_path, 'r')
        data = f.read()

        js = self._escape_string(self._get_javascript_input(data))
        css = self._escape_string(self._get_css_input(data))
        html = self._escape_string(self._get_html_input(data))
        self._title = self._escape_string(self._get_title(data))

        fill_js_script = \
            "var div = document.getElementById('js');" \
            "div.value = '" + js + "';"
        browser.execute_script(fill_js_script)

        fill_css_script = \
            "var div = document.getElementById('css');" \
            "div.value = '" + css + "';"
        browser.execute_script(fill_css_script)

        fill_html_script = \
            "var div = document.getElementById('html');" \
            "div.value = '" + html + "';"
        browser.execute_script(fill_html_script)

        fill_title_script = "document.title = '" + self._title + "';"
        browser.execute_script(fill_title_script)


    def _basename_strip(self, jobject):
        name = jobject.metadata.get('title', 'untitled')
        name = name.replace(os.sep, ' ').strip()
        root, mime_extension = os.path.splitext(jobject.file_path)
        if not name.endswith(mime_extension):
            name += mime_extension
        return name
