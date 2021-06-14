# import libraries
import streamlit as st
import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from hashlib import sha256 as ENCRYPT
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import logging
import sys
#import time


# remove logging of googleapicliet
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)
#logging.getLogger('streamlit').setLevel(logging.ERROR)


##### get monthly data from gcp api call
def get_monthly_data(month):
    # month like 'April 2021'
    # try to get data
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets['gcp_service_account'], scopes=scope)
        gc = gspread.authorize(credentials)
        wks = gc.open(month.replace(" ", "_")).get_worksheet(0)
        data = wks.get_all_values()
        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)
        df = df[st.secrets['cols']]
        df.index = ['']*df.shape[0]
        #df.set_index(st.secrets['index_cols'], inplace=True)
        return df
    # except error getting data
    except Exception as err:
        return f'ERROR getting data. \n\n {sys.exc_info()[0]} \n\n {err}'


##### upload image with gcp api call
def get_upload(upload):
    # try to upload
    try:
        # grab credentials
        scope = ['https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets['gcp_service_account'], scopes=scope)
        service = build('drive', 'v2', credentials=credentials)

        ####################################################################
        media_body = MediaIoBaseUpload(upload, mimetype=upload.type,
                      chunksize=upload.size, resumable=True)
        body = {'title': datetime.now().strftime("%Y_%m_%d_%H_%M_%S.jpeg")}
        body['parents'] = [{'id': st.secrets['folder_id']}]
        service.files().insert(body=body, media_body=media_body).execute()
        ####################################################################
        # return string
        return 'SUCCESS'
    # except error uploading image
    except Exception as err:
        return f'ERROR uploading image. \n\n {sys.exc_info()[0]} \n\n {err}'


##### greeting
st.title('Welcome!')


##### data
with st.beta_expander("Data"):
    data_running_process_placeholder = st.empty()
    data_form = st.form(key='data_form')
    data_passphrase = data_form.text_input('Passphrase',key='data_passphrase')
    month = data_form.selectbox('Months',st.secrets['avail_months'], key='month')
    data_btn = data_form.form_submit_button(label='See Data')
    data_placeholder_message = st.empty()
    data_placeholder = st.empty()


##### upload
with st.beta_expander("Upload"):
    upload_running_process_placeholder = st.empty()
    upload_form = st.form(key='upload_form')
    upload_passphrase = upload_form.text_input('Passphrase',key='upload_passphrase')
    upload = upload_form.file_uploader('',key='file_upload', type=['jpg','jpeg'])
    upload_btn = upload_form.form_submit_button(label='Upload')
    upload_placeholder_message = st.empty()


##### see data
if data_btn:

    # check passphrase
    if not ENCRYPT(data_passphrase.strip().lower().encode()).hexdigest() == st.secrets['passphrase']:
        data_placeholder_message.error('Incorrect passphrase.')

    # else continue with correct passphrase
    else:

        # check for selected month
        if not month:
             data_placeholder_message.error('Please select a set of months.')

        # else continue with month
        else:

            # grab data (with spinner)
            with data_running_process_placeholder.beta_container():
                with st.spinner(text="Getting data....."):
                    df = get_monthly_data(month)

            # check for error grabbing data
            if type(df) == str:
                data_placeholder_message.error(df)

            # else continue to write df
            else:
                data_placeholder.table(df)


##### upload
if upload_btn:

    # check passphrase
    if not ENCRYPT(upload_passphrase.strip().lower().encode()).hexdigest() == st.secrets['passphrase']:
        upload_placeholder_message.error('Incorrect passphrase.')

    # else continue with correct passphrase
    else:

        # check for uploaded image
        if not upload:
            upload_placeholder_message.error('Please provide a file to upload.')

        # else continue with image upload
        else:

            # upload image (with spinner)
            with upload_running_process_placeholder.beta_container():
                with st.spinner(text="Uploading image....."):
                    upload_result = get_upload(upload)

            # check for success
            if upload_result == 'SUCCESS':
                upload_placeholder_message.success('SUCCESS uploading file.')

            # else we have an error
            else:
                upload_placeholder_message.error(upload_result)
