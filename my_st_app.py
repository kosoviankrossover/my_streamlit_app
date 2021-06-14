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


############### helper functions -----------------------------------------------

##### keep states to move between portions (pages) of the app
@st.cache(allow_output_mutation=True, show_spinner=False)
def grab_states():
    return {"login": None, # move from login to main page
            "username": None,
            "password": None,
            "admin": None} # admin user vs main user


##### modify months if 'All' selected
def months_check(months):
        # check for 'All' selection in months
        if 'All' in months:

            # if admin user
            if states['admin']:
                months = st.secrets['avail_months_admin'][2:]

            # else main user
            else:
                months = st.secrets['avail_months_main'][2:]

        # return any modification
        return months


##### get monthly data from gcp api call
gcp_creds = st.secrets['gcp_service_account']
@st.cache(allow_output_mutation=True, show_spinner=False)
def get_monthly_data(month):
    # month like 'April 2021'
    global gcp_creds
    # grab credentials
    scope = ['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(gcp_creds, scopes=scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(month.replace(" ", "_")).get_worksheet(0)
    data = wks.get_all_values()
    headers = data.pop(0)
    df = pd.DataFrame(data, columns=headers)
    return df

##### get data
def get_data(months):
    # return a dictionary like (month: df of monthly data)
    df_dict = {}

    # try to get data
    try:

        # loop through list of months
        for month in months:

            # grab monthly data
            df_dict[month] = get_monthly_data(month)

        # if no error, return dict
        return df_dict

    # except error
    except Exception as err:
        return f'ERROR obtaining data. \n\n {sys.exc_info()[0]} \n\n {err}'


##### filter data
def my_filter(data, x, y, cols, cols_disp):
    # data is a dictionary like (month: df)
    # filter for value x on column y

    # try to filter data
    try:

        # loop through the data
        for m, df in data.items():

            # if x exists in the df, then filter for it
            if x in df[y].values:
                df = df[df[y].values == x]

            # else, create df to notfiy of no data found
            else:
                temp = np.array(['data not found']*df.shape[1]).reshape(-1, df.shape[1])
                df = pd.DataFrame(temp, columns=df.columns)

            # subset columns
            df = df[cols]
            df.columns = cols_disp

            # change index to the associated month
            df.index = [m]*df.shape[0]

            # replace df
            data[m] = df

        # merge dfs
        df = pd.concat(data.values())

        # tranpose df
        df = df.transpose()

        # no error, then return df
        return df

    # except error filter data
    except Exception as err:
        return f'ERROR filtering data. \n\n {sys.exc_info()[0]} \n\n {err}'


############### beginning states  ----------------------------------------------

# states
states = grab_states()



############### load login page ------------------------------------------------

# no cached info -- serve login page
if not states['login']:

    # instantiate buttons that may not be otherwise
    data_btn = None
    upload_btn = None
    logout = None

    # greeting
    st.title('Welcome!')


    # -------------------------- login form ------------------------------------
    login_form = st.form(key='login_form')
    username = login_form.text_input('Username',key='username')
    password = login_form.text_input('Password',key='password')
    login_btn = login_form.form_submit_button(label='Login')
    login_error = st.empty() # place to load error if needed



############### load mian page -------------------------------------------------

# cached info -- serve main page
if states["login"]:

    # instantiate login button (that may not be otherwise)
    login_btn = None

    # instantiate potential upload button (that may not be otherwise)
    upload_btn = None


    # ------------------------- running process placeholder --------------------
    running_process_placeholder = st.empty()


    # --------------------------- data form ----------------------------------
    data_form = st.form(key='data_form')
    data_form.write("Select a set of months from which to see data.")
    # if admin user
    if states['admin']:
        months = data_form.multiselect('',st.secrets['avail_months_admin'][1:], key='months')
        accounts_list = list(st.secrets['selections'].values())
        accounts_list.insert(0,'All')
        account = data_form.selectbox('', accounts_list, key='account')
    # else main user
    else:
        months = data_form.multiselect('',st.secrets['avail_months_main'][1:], key='months')
    data_btn = data_form.form_submit_button(label='See Data')
    data_placeholder_success = st.empty()
    data_placeholder = st.empty()


    # --------------------------- upload form ----------------------------------
    # add upload form
    if states['admin']:
        upload_form = st.form(key='upload_form')
        upload_form.write("Choose photo to upload.") # instruction
        upload = upload_form.file_uploader('',key='file_up', type=['jpg','jpeg'])
        upload_btn = upload_form.form_submit_button(label='Upload')
        upload_placeholder_message = st.empty()


    # -------------------------- logout button ---------------------------------
    logout = st.button(label='Logout')



############### actions for login page -----------------------------------------

# login
if login_btn:

    # clean user inputs
    clean_username = username.strip().lower()
    clean_password = password.strip().lower()


    # check for valid main user
    if (clean_username, clean_password) in st.secrets['accounts'].items():

        # update states
        states.update({'login':True,
                       'username':clean_username,
                       'password':clean_password})

        # rerun app to load main page as main user
        st.experimental_rerun()


    # check for valid admin user
    encrypt_user = ENCRYPT(clean_username.encode()).hexdigest()
    encrypt_pass = ENCRYPT(clean_password.encode()).hexdigest()
    if encrypt_user==st.secrets['admin_user'] and encrypt_pass==st.secrets['admin_pass']:

        # update states
        states.update({'login':True,
                       'username':encrypt_user,
                       'password':encrypt_pass,
                       "admin":True})

        # rerun app to load main page as admin user
        st.experimental_rerun()


    # having done nothing else, then we must have an error; wait for good input
    login_error.error('Incorrect username-password combination.')



############### actions for main page ------------------------------------------

# see data
if data_btn and states['login']:

    # if no set of months selected, then stop and display error
    if not months:
         data_placeholder_success.error('Please select a set of months.')

    # else, continue with the set of months collected
    else:

        # appropriately modify months if 'All' selected
        months = months_check(months)

        # get data (with spinner)
        with running_process_placeholder.beta_container():
            with st.spinner(text="Getting data....."):
                data = get_data(months)

        # look for error from grabbing the data
        if type(data) is not dict:
            data_placeholder_success.error(data)

        # else, continue with the data collected
        else:

            # if admin user
            if states['admin']:

                # if 'All' accounts selected, write full dfs to app
                if account == 'All':

                    # try-error
                    try:

                        # write the dfs to the months placeholder
                        with data_placeholder.beta_container():

                            # loop through the data
                            for m, df in data.items():

                                # subset columns
                                df = df[st.secrets['admin_COLS']]
                                df.columns = st.secrets['admin_COLS_disp']
                                # clear index for output look
                                df.index = ['']*df.shape[0]
                                st.write(f'**{m}**')
                                st.write(df)

                    # error loading 'ALL'
                    except Exception as err:
                        data_placeholder_success.error(f'ERROR writing data. \n\n {sys.exc_info()[0]} \n\n {err}')

                # else, filter the dfs and write the merged df as a table
                else:

                    # reverse account-selection map
                    # inv_map: selection -> account
                    inv_map = {v: k for k, v in st.secrets['selections'].items()}

                    # filter data
                    df = my_filter(data, inv_map[account],
                                    st.secrets['col_account'],
                                    st.secrets['admin_COLS'],
                                    st.secrets['admin_COLS_disp'])

                    # error in filter fun
                    if type(df) == str:
                        data_placeholder_success.error(df)

                    # else no error in filter fun
                    else:

                        # with data_placeholder.beta_container():
                        #     cols = st.beta_columns(df.shape[1])
                        #     for i in range(df.shape[1]):
                        #         cols[i] = st.write(df[df.columns[i]])

                        # write merged df to the app
                        data_placeholder.write(df)

            # else main account
            else:

                # filter data
                df = my_filter(data, states['username'],
                                st.secrets['col_user'],
                                st.secrets['main_COLS'],
                                st.secrets['main_COLS_disp'])

                # error in filter fun
                if type(df) == str:
                    data_placeholder_success.error('ERROR writing data.')

                # else no error in filter fun
                else:

                    # write merged df to app
                    data_placeholder.write(df)


# upload
if upload_btn and states['login']:

    # check for uploaded image
    if upload:

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

            # load success message
            upload_placeholder_message.success('SUCCESS uploading file.')
            #st.balloons()

        # except error uploading file
        except Exception as err:
            upload_placeholder_message.error(f'ERROR uploading file. \n\n {sys.exc_info()[0]} \n\n {err}')

    # else no uploaded image
    else:
        upload_placeholder_message.error('Please provide a file to upload.')



############### logout ---------------------------------------------------------
if logout:
    st.caching.clear_cache()
    st.experimental_rerun()
