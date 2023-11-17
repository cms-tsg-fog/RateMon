#!/usr/bin/env bash

# copy password files as hidden files to this directory

cd /opt/ratemon/.secure

secure_dir="/nfshome0/centraltspro/secure/"

hook_file='/cmsnfsratemon/ratemon/.mattermost_hook.txt'

hook=$(cat $hook_file)

yaml_file='../mattermostHook.yaml'

hook_dummy='your-mattermost-hook'

sed -i "s/$hook_dummy/$hook/g" $yaml_file
