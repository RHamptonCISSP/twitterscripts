import sqlite3
conn = sqlite3.connect('twitterbot.db')
c = conn.cursor()

# Create table
#c.execute('''CREATE TABLE users (id integer primary key, ScreenName varchar(255), whitelisted boolean, followsMe boolean, lastUpdate datetime)''')
#Uses affinity.  In fact only text and integers are used
#https://sqlite.org/datatype3.html

c.execute('''CREATE TABLE users (id integer primary key, ScreenName text, whitelisted integer, followsMe integer, lastUpdate integer)''')

# Save (commit) the changes
conn.commit()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()

