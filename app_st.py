import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import base64
import math

from functions.functions_data import get_global_daily, get_global_daily_v2, get_rolling, get_rolling_values
from functions.functions_graphics import plot_engagements_users, plot_metrics, plot_engagements_users_comparative
from functions.functions_data import get_engagement_list_v2, get_rolling_v2

#Set title, icon, and layout
st.set_page_config(
     page_title="FinHabits",
     page_icon="guitar",
     layout="wide")

#function to get group of age
def get_group_age(number):
    if 18 <= number <= 29:
        return "18-29"
    elif 30 <= number <= 39:
        return "30-39"
    elif 40 <= number <= 49:
        return "40-49"
    elif 50 <= number <= 59:
        return "50-59"
    elif 60 <= number <= 69:
        return "60-69"
    elif 70 <= number <= 79:
        return "70-79"
    else:
        return "80+"

#function to load data
@st.cache_data()
def load_data():
    #read the data
    path_to_csv = "data/attribution_detected.csv"
    df = pd.read_csv(path_to_csv, parse_dates=['EventDateTime'], dtype={'CurrentPlatform': str,
                                                                        'CurrentType': str,
                                                                        'Platform': str,
                                                                        'Version': str})
    #change data type
    df['EventDateTime'] = pd.to_datetime(df['EventDateTime'])

    #import csv with total balance 
    path_to_csv_total_balance = "data/20230609-users.csv"
    df_total_balance = pd.read_csv(path_to_csv_total_balance)
    df_total_balance = df_total_balance.rename(columns = {'userId':'UserId'})


    #merge csv
    df = df.merge(df_total_balance, left_on='UserId', right_on='UserId', how='left')    

    #User_client
    #if totalBalance is greater 3 then is a Client, else is an User
    df['User_Client'] = df['totalBalance'].apply(lambda x: 'Client' if x > 3 else 'User')
    #get group of age
    df["Group_age"] = df["Age"].apply(lambda x: get_group_age(x))
    #Abreviaturas de los estados de USA
    df_states = pd.read_csv("data/abreviaturas_USA.csv")

    return df, df_states

@st.cache_data()
def convert_df(df):
    return df.to_csv().encode('utf-8')


#load data and create a copy
df, df_states = load_data()
df_filter = df.copy()

#tabs 
tab1, tab2, tab3 = st.tabs(["Engagements users", "Engagements Metrics", "Comparative"])

#diccionario, abreviatura : state
#'Alabama' : 'AL'
df_states = df_states[df_states["Abreviatura"].isin(df.UserState.unique())]
diccionario_abreviaturas = pd.Series(df_states.Abreviatura.values,index=df_states.State).to_dict()

#bins of age
age_bins = {
   "18-29" : (18,29), 
   "30-39" : (30,39),
   "40-49" : (40,49),
   "50-59" : (50,59),
   "60-69" : (60,69),
   "70-79" : (70,79)
}

age_list = list(age_bins.keys())

#gender list for the selectbox
gender_list = list(df[df.UserGender.notna()].UserGender.unique())

#UserMaritalStatus list for the selectbox
maritalstatus_list = list (df[df.UserMaritalStatus.notna()].UserMaritalStatus.unique())

#platform list
platform_list = ["iOS", "Android"]

#state list
state_list = list(diccionario_abreviaturas.keys())

#dates
max_date = pd.to_datetime(df.EventDateTime.max())
min_date = pd.to_datetime(df.EventDateTime.min())

#user_client
userClient_list = list(df[df.User_Client.notna()].User_Client.unique() )

#UTMCampaign list, but order by value_count
utmCampaign_list = df.UTMCampaign.value_counts().reset_index()
utmCampaign_list = list(utmCampaign_list["UTMCampaign"])

#paginacion del df
def paginate_dataframe(dataframe, page_size = 10, page_num = 1):
    #cuantos resultados por pagina 
    offset = page_size*(page_num-1)
    return dataframe[offset:offset + page_size]

#valores por default 
if "sd" not in st.session_state:
    st.session_state["min_date"] = dt.date(min_date.year, min_date.month,min_date.day)

if "en" not in st.session_state:
    st.session_state["max_date"] = dt.date(max_date.year, max_date.month,max_date.day)

if "rq" not in st.session_state:
    st.session_state["rolling"] = 7

if "age" not in st.session_state:
    st.session_state["index_age"] = 0

if "platform" not in st.session_state:
    st.session_state["index_platform"] = 0

if "state" not in st.session_state:
    st.session_state["index_state"] = 0

if "gender" not in st.session_state:
    st.session_state["index_gender"] = 0

if "maritalstatus" not in st.session_state:
    st.session_state["index_maritalstatus"] = 0

if "userClient" not in st.session_state:
    st.session_state["index_userClient"] = 0

if "UTMCampaign" not in st.session_state:
    st.session_state["index_UTMCampaign"] = 0

#limpiar el form 
def clear_form():
    st.session_state["sd"] = dt.date(min_date.year, min_date.month,min_date.day)
    st.session_state["en"] = dt.date(max_date.year, max_date.month,max_date.day)
    st.session_state["rq"] = 7
    #selects
    st.session_state["age"] = "All"
    st.session_state["platform"] = "All"
    st.session_state["state"] = "All"
    st.session_state["gender"] = "All"
    st.session_state["maritalstatus"] = "All"
    st.session_state["userClient"] = "All"
    st.session_state["UTMCampaign"] = "All"
   
#contenedor
# Using "with" notation
with st.sidebar:
    #year-month-day
    start_date = st.date_input(label='Start date', key="sd", value = st.session_state["min_date"])
    #year-month-day
    end_date = st.date_input(label='End date', key="en", value = st.session_state["max_date"])
    #rolling quantity
    rolling_quantity = st.number_input(label='Rolling Quantity',step=1, key="rq", value = st.session_state["rolling"] )
    #filtros adicionales 
    st.text("Filter")
    filters_text = []
    
    #Filter to user_client     
    userClient_filter = st.selectbox( "userClient", ["All",]  + (userClient_list) , key = "userClient", index = st.session_state["index_userClient"])
    if userClient_filter != "All":
        #filter df
        df_filter = df_filter[df_filter['User_Client'] == userClient_filter]
        filters_text.append("userClient: " + userClient_filter) 
    
    #Filter to age
    age_filter = st.selectbox( "Age Bins", ["All"] + (age_list), key = "age", index = st.session_state["index_age"])
    #filter df
    if age_filter != "All":
        df_filter = df_filter[df_filter['Age'].between( age_bins[age_filter][0], age_bins[age_filter][1] )]
        filters_text.append("Age: " + age_filter ) 

    #Filter to platform     
    platform_filter = st.selectbox( "Platform",["All"] + platform_list, key = "platform", index = st.session_state["index_platform"])
    #filter df
    if platform_filter != "All":
        df_filter = df_filter[df_filter['Mobile_Device'] == platform_filter]
        filters_text.append("Mobile_Device: " + platform_filter ) 

    #Filter to UTMcampaign
    UTMCampaign_filter = st.selectbox( "UTMCampaign", ["All",]  + (utmCampaign_list) , key = "UTMCampaign", index = st.session_state["index_UTMCampaign"])
    if UTMCampaign_filter != "All":
        #filter df
        df_filter = df_filter[df_filter['UTMCampaign'] == UTMCampaign_filter]
        filters_text.append("UTMCampaign: " + UTMCampaign_filter) 

    #Filter to state     
    #Use the key of the diccionary, i mean, the name of the state
    state_filter = st.selectbox( "State",["All",]  + state_list, key = "state", index = st.session_state["index_state"])
    #filter df
    if state_filter != "All":
        df_filter = df_filter[df_filter['UserState'] == diccionario_abreviaturas[state_filter]]
        filters_text.append("State: " + state_filter) 

    #Filter to gender     
    gender_filter = st.selectbox( "Gender", ["All",]  + (gender_list), key = "gender", index = st.session_state["index_gender"])
    #filter df
    if gender_filter != "All":
        df_filter = df_filter[df_filter['UserGender'] == gender_filter]
        filters_text.append("Gender: " + gender_filter) 

    #Filter to marital status     
    maritalStatus_filter = st.selectbox( "Marital status", ["All",]  + (maritalstatus_list) , key = "maritalstatus", index = st.session_state["index_maritalstatus"])
    if maritalStatus_filter != "All":
        #filter df
        df_filter = df_filter[df_filter['UserMaritalStatus'] == maritalStatus_filter]
        filters_text.append("Marital Status: " + maritalStatus_filter) 
    
    #reset inputs
    clear = st.button(label="Clear", on_click=clear_form)
    #this data is used in both plots

engagement_list = get_engagement_list_v2(df = df_filter, start_date= str(start_date), end_data= str(end_date)  )
#En el primer tab, show the first plot
with tab1:
    #data for the plot
    global_metrics = get_global_daily(engagement_list)
    rolled = get_rolling(global_metrics,int(rolling_quantity), engagement_list)
    #plot 
    fig = plot_engagements_users(rolled, str(rolling_quantity) +' days')

    #plot in streamlit
    st.plotly_chart(
        fig, 
        theme="streamlit", use_container_width=True, height=800
    )

    #show active filters
    if filters_text:
        st.subheader("With filters")
        for f in filters_text:
            st.write(f)

    with st.expander("See table"):
        # Show the first 10 records of the filtered DataFrame
        st.subheader("Filtered Data")
        #paginacion 
        number = st.number_input('Pagina', value=1,min_value=1, max_value=math.ceil(len(engagement_list.index) / 10), step=1)
        #pag 1 de n paginas 
        st.write("Pagina " + str(number) + " de " + str(math.ceil(len(engagement_list.index) / 10)))
        #muestra la tabla 
        st.table(paginate_dataframe(engagement_list[['UserId', 'EventDateTime', 'Language', 
                                    'Age', 'UserState', 'Mobile_Device',
                                'UserGender', 'UserMaritalStatus']], 10, number))
#The second plot
with tab2:
    #data for the plot
    rolling = get_rolling_values(engagement_list, rolling_quantity)
    #plot 
    fig2 = plot_metrics(rolling,  str(rolling_quantity) +' days')

    #plot in streamlit
    st.plotly_chart(
        fig2, 
        theme="streamlit", use_container_width=True, height=800
    )

    #show active filters
    if filters_text:
        st.subheader("With filters")
        for f in filters_text:
            st.write(f)
        
    with st.expander("See table"):
        st.subheader("Filtered Data")
        number = st.number_input('Pagina', value=1,min_value=1, max_value=math.ceil(len(engagement_list.index) / 10), step=1, key = "paginacion_em")

        st.table(paginate_dataframe(engagement_list[['UserId', 'EventDateTime', 'Language', 
                                    'Age', 'UserState', 'Mobile_Device',
                                'UserGender', 'UserMaritalStatus']], 10, number))
with tab3:
    comparative_dictionary ={
        'User' : [userClient_list, "User_Client"], 
        'Age' : [age_list, "Group_age"], 
        'Platform' : [platform_list, "Mobile_Device"] , 
        'UTMCampaign':  [utmCampaign_list, "UTMCampaign"], 
        'State':  [state_list, "UserState"], 
        'Gender':  [gender_list, "UserGender"], 
        'Marital status':  [maritalstatus_list, "UserMaritalStatus"]
    }
    #options for Comparative by
    option = st.selectbox(
    'Comparative by',
    ('User', 'Age', 'Platform', 'UTMCampaign', 'State', 'Gender', 'Marital status'))
    #multiselect for elements for comparation 
    options = st.multiselect(
        'Choose',
        comparative_dictionary[option][0], comparative_dictionary[option][0][0])

    if option == 'State':
        list_states = []
        for opt_state in options:
            list_states.append(diccionario_abreviaturas[opt_state])
        global_metrics_v2 = get_global_daily_v2(engagement_list[engagement_list[comparative_dictionary[option][1]].isin(list_states)], comparative_dictionary[option][1])
        #calculate data
        rolled_v2 = get_rolling_v2(global_metrics_v2,int(rolling_quantity), engagement_list, comparative_dictionary[option][1])
        #fig
        fig_comparative = plot_engagements_users_comparative(rolled_v2.reset_index(), str(rolling_quantity) +' days', comparative_dictionary[option][1], list_states)
    else:
        global_metrics_v2 = get_global_daily_v2(engagement_list[engagement_list[comparative_dictionary[option][1]].isin(options)], comparative_dictionary[option][1])
        #calculate data
        rolled_v2 = get_rolling_v2(global_metrics_v2,int(rolling_quantity), engagement_list, comparative_dictionary[option][1])
        #fig
        fig_comparative = plot_engagements_users_comparative(rolled_v2.reset_index(), str(rolling_quantity) +' days', comparative_dictionary[option][1], options)

    #plot in streamlit
    st.plotly_chart(
        fig_comparative, 
        theme="streamlit", use_container_width=True, height=800
    )

    #show active filters
    if filters_text:
        st.subheader("With filters")
        for f in filters_text:
            st.write(f)
#download the data 
st.download_button(
    label="Download data as CSV",
    data=convert_df(engagement_list),
    file_name='data.csv',
    mime='text/csv',
)
