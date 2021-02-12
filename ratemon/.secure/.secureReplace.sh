#!/usr/bin/env bash

secure_dir="/nfshome0/centraltspro/secure/"
hlt_connect_file="cms_hlt_r.txt"
trg_connect_file="cms_trg_r.txt"

# copy password files as hidden files to this directory

#for file in $hlt_connect_file $trg_connect_file
#do
#    if [ -s $secure_dir$file ]
#    then
#        if ! [ -s ./.$file ]
#        then
#            cp $secure_dir$file ./.$file
#        fi
#    fi
#done

# extract passwords

hlt_connect_file="${secure_dir}cms_hlt_r.txt"
trg_connect_file="${secure_dir}cms_trg_r.txt"

if [ -s $hlt_connect_file ]
then
    hlt_connect_pass=$(cat $hlt_connect_file)
fi

if [ -s $trg_connect_file ]
then
    trg_connect_pass=$(cat $trg_connect_file)
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
