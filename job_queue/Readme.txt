-- Create a user
CREATE USER labhubuser WITH PASSWORD 'labhubpass';

-- Create your database
CREATE DATABASE labhubdb OWNER labhubuser;

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE labhubdb TO labhubuser;

-- Exit the SQL zone
\q



---Run the sql--

psql -U labhubuser -d labhubdb
labhubdb=#
\dt -- tbl list
SELECT * FROM qmodel_job;
SELECT * FROM qmodel_jobstep;
SELECT * FROM qmodel_stepconfig;

----------Token key-------
 print(token.key)
e1997396f5c992a1cc89ea5c8a518ab22bbab65f

To keep it reusable, you can even export the token in your terminal like this:

export AUTH_TOKEN=e1997396f5c992a1cc89ea5c8a518ab22bbab65f
curl -H "Authorization: Token $AUTH_TOKEN" http://127.0.0.1:8000/api/jobs/

🔍 How to See It in the Database (SQLite or Postgres)


python manage.py dbshell
SELECT * FROM qmodel_stepconfig;
SELECT * FROM qmodel_job;
SELECT * FROM qmodel_jobstep;


Truncate  table qmodel_job CASCADE;
Truncate  table qmodel_jobstep CASCADE;
Truncate  table  qmodel_stepconfig CASCADE;

DROP TABLE IF EXISTS qmodel_jobstep CASCADE;
DROP TABLE IF EXISTS qmodel_job CASCADE;
DROP TABLE IF EXISTS qmodel_stepconfig CASCADE;