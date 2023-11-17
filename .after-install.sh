#!/usr/bin/env bash
cd /opt
chmod g+w ratemon/
chmod g+ws -R ratemon/.secure
sg cms_ratemon_librarian ratemon/.secure/.secureReplace.sh
