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


    def open_new_tab(self):
        browser = self._activity._tabbed_view.props.current_browser
        browser.open_new_tab(self._src_uri)

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

    def _get_javascript_input(self, data):
        start = data.find("<script>")
        end = data.find("</script>")
        if start > -1 and end > -1 and start < end:
            return data[start + 8 : end]
        return ""

    def _get_css_input(self, data):
        start = data.find("<style>")
        end = data.find("</style>")
        if start > -1 and end > -1 and start < end:
            return data[start + 7 : end]
        return ""

    def _get_html_input(self, data):
        start = data.find("<body>")
        end = data.find("</body>")
        if start > -1 and end > -1 and start < end:
            return data[start + 6 : end]
        return ""

    def open_file(self):
        browser = self._activity._tabbed_view.props.current_browser
        if browser.get_uri() != self._src_uri:
            self._activity._alert("It looks like the Web Console is not open." +
                                  "You can only Open a file from Web Console")
            return
        picker = FilePicker(self._activity)
        chosen = picker.run()
        picker.destroy()
        f = open(chosen, 'r')
        data = f.read()

        js = self._get_javascript_input(data).replace("'", "\\\'")
        css = self._get_css_input(data).replace("'", "\\\'")
        html = self._get_html_input(data).replace("'", "\\\'")

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
