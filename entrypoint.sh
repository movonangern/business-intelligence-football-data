#!/bin/bash

sleep 20

if [ ! -f exists ]; then
    python fill_database.py
    python clean_data.py
    touch exists
fi

cd streamlit
streamlit run Startseite.py