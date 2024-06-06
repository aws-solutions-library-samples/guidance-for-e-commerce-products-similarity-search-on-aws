import streamlit as st
import psycopg2
import boto3
import os
import json
import numpy as np
from pgvector.psycopg2 import register_vector

# PostgreSQL connection parameters

dbsecret = os.environ.get('DBSECRET')

smclient = boto3.client('secretsmanager')
response  = smclient.get_secret_value(SecretId=dbsecret)
secret_data = json.loads(response['SecretString'])
username = secret_data.get('username')
password = secret_data.get('password')
host = secret_data.get('host')
port = secret_data.get('port')

ENDPOINT_NAME = os.environ.get('ENDPOINTNAME')
sagemakerclient = boto3.client('runtime.sagemaker')

# Function to connect to PostgreSQL database
def connect_to_db():
    try:
        conn = psycopg2.connect(host=host, database='demodb', user=username, password=password, port=port)
        register_vector(conn)
        return conn
    except Exception as e:
        st.error("Error connecting to the database: {}".format(e))

# Main function to display products catalog and search functionality
def main():
    # Set page title and favicon
    st.set_page_config(page_title="Products Catalog", page_icon=":moneybag:")

    # Set custom CSS styles
    st.markdown(
        """
        <style>
            body {
                background-color: #f0f2f6;
                color: #333;
            }
            .st-ba, .st-cv, .st-cw, .st-dh, .st-dm, .st-ei, .st-el, .st-ep, .st-es {
                max-width: 1200px;
                margin: auto;
            }
            .st-dh {
                padding-top: 50px;
            }
            .st-cv {
                padding-bottom: 50px;
            }
            .st-cw {
                padding: 20px;
                background-color: #fff;
                border-radius: 10px;
                box-shadow: 0px 0px 10px 0px rgba(0,0,0,0.1);
            }
            .st-cw img {
                border-radius: 5px;
                box-shadow: 0px 0px 5px 0px rgba(0,0,0,0.2);
            }
            .st-dm {
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title('Products Catalog')

    # Sidebar search box
    search_query = st.sidebar.text_input("Search products", "")

    # Connect to database
    conn = connect_to_db()

    if conn:
        cur = conn.cursor()
        if search_query:
            payload = json.dumps({'inputs' : search_query })
            response = sagemakerclient.invoke_endpoint(EndpointName=ENDPOINT_NAME, ContentType='application/json', Body=payload)
            r = json.loads(response['Body'].read().decode())
            search_embedding = [sublist[0] for sublist in r][0]
            cur.execute("""SELECT id, url, description, embedding
                            FROM demo.products
                            ORDER BY embedding <-> %s limit 2;""", (np.array(search_embedding),))
            products = cur.fetchall()
        else:
            cur.execute("SELECT id, url, description, embedding FROM demo.products LIMIT 10")
            products = cur.fetchall()

        # Display products
        for product in products:
            st.markdown("<hr>", unsafe_allow_html=True)
            #st.subheader(product[2])
            st.image(product[1], caption=product[2], width=200)
            st.write("Description: ", product[2])
            #st.write("Price: $", product[3])

        cur.close()
        conn.close()
    else:
        st.error("Error connecting to the database")

if __name__ == '__main__':
    main()
