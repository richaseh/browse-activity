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

from filepicker import FilePicker
import os
import tempfile

from gi.repository import WebKit

from sugar3.activity import activity
from sugar3.datastore import datastore

class WebConsole():
    def __init__(self, act):
        self._activity = act

        src_path = os.path.join(activity.get_bundle_path(),
                                "data/web-console.html")
        self._src_uri = "file://" + src_path

        self._storage_dir = os.path.join(act.get_activity_root(),
                                         "Web_Console_Files")
        self._load_status_changed_hid = None
        self._file_path = None

    def _get_file_text(self):
        browser = self._activity._tabbed_view.props.current_browser
        frame = browser.get_main_frame()

        original_title = frame.get_title()
        if original_title is None:
            original_title = ""
        text_script = \
            "var saveTextBtn = document.getElementById('internal-use-trigger-save-text');" \
            "saveTextBtn.click();" \
            "var savedTextDiv = document.querySelector('#internal-use-saved-text');" \
            "var text = savedTextDiv.value; " \
            "document.title = text;"
        browser.execute_script(text_script)
        file_text = frame.get_title()

        reset_title_script = "document.title = '" + original_title + "';"
        browser.execute_script(reset_title_script)

        return file_text

    def _add_to_journal(self, title, file_path):
        jobject = datastore.create()

        jobject.metadata['title'] = title
        jobject.metadata['description'] = "Saved from web console"

        jobject.metadata['mime_type'] = "text/html"
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

    def open_new_tab(self):
        browser = self._activity._tabbed_view.props.current_browser
        browser.get_source(self._open_with_source, self._open_empty)

    def save_file(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Save a file from Web Console")
            return
        file_text = self._get_file_text()
        if not os.path.exists(self._storage_dir):
            os.makedirs(self._storage_dir)
        fd, dest_path = tempfile.mkstemp(dir=self._storage_dir)
        # Write to file
        os.write(fd, file_text)
        os.close(fd)

        self._add_to_journal(dest_path, dest_path)

    def open_file(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Open a file from Web Console")
            return
        picker = FilePicker(self._activity)
        chosen = picker.run()
        picker.destroy()
        self._open_file_path(chosen)

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
        return ""

    def _escape_string(self, string):
        return string.replace("'", "\\\'").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")

    def _open_file_path(self, file_path):
        browser = self._activity._tabbed_view.props.current_browser
        f = open(file_path, 'r')
        data = f.read()

        js = self._escape_string(self._get_javascript_input(data))
        css = self._escape_string(self._get_css_input(data))
        html = self._escape_string(self._get_html_input(data))
        title = self._escape_string(self._get_title(data))

        fill_js_script = \
            "var div = document.getElementById('js');" \
            "div.value = '" + js + "';" \
        browser.execute_script(fill_js_script)

        fill_css_script = \
            "var div = document.getElementById('css');" \
            "div.value = '" + css + "';"
        browser.execute_script(fill_css_script)

        fill_html_script = \
            "var div = document.getElementById('html');" \
            "div.value = '" + html + "';"
        browser.execute_script(fill_html_script)

        fill_title_script = "document.title = '" + title + "';"
        browser.execute_script(fill_title_script)
