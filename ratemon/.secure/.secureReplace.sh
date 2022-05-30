#!/usr/bin/env bash

# copy password files as hidden files to this directory

cd /opt/ratemon/.secure

secure_dir="/nfshome0/centraltspro/secure/"
hlt_connect_file="cms_hlt_r.txt"
trg_connect_file="cms_trg_r.txt"

for file in $hlt_connect_file $trg_connect_file
do
    if [ -s $secure_dir$file ]
    then
        cp $secure_dir$file ./.$file
    fi
done

if [ -s .$hlt_connect_file ]
then
    hlt_connect_pass=$(cat .$hlt_connect_file)
fi

if [ -s .$trg_connect_file ]
then
    trg_connect_pass=$(cat .$trg_connect_file)
fi

# replace passwords in YAML file

yaml_file="../dbConfig.yaml"

hlt_connect_dummy="__cms_hlt_r_pass__"
trg_connect_dummy="__cms_trg_r_pass__"

if ! [ -z $hlt_connect_pass ]
then
    sed -i "s/$hlt_connect_dummy/$hlt_connect_pass/" $yaml_file
fi

if ! [ -z $trg_connect_pass ]
then
    sed -i "s/$trg_connect_dummy/$trg_connect_pass/" $yaml_file
fi

hook_file="../mattermost_hook.txt"

if [ -s .$hook_file ]
then
    hook=$(cat .$hook_file)
fi

yaml_file="../mattermostHook.yaml"

hook_dummy='your-mattermost-hook'

if ! [ -z $hook ]
then
    sed -i "s/$hook/$hook_dummy" $yaml_file
fi
