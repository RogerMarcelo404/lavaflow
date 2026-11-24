CREATE ROLE lavaflow_app WITH LOGIN PASSWORD 'lavaflow72026';


CREATE DATABASE lavaflow
    OWNER lavaflow_app
    ENCODING 'UTF8'
    TEMPLATE template0;
