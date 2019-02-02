import sqlite3
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

#cur.execute("select * from users")
#cur.execute("select count(*) from users where followsMe=3")
#cur.execute("SELECT count(ScreenName) FROM users WHERE lastUpdate > 1507766400")
#cur.execute("SELECT count(*) FROM users WHERE followsMe in (0, 3)")
cur.execute("select count(*) from users")
#cur.execute("select * from users WHERE ScreenName in ('Mother_of_Tanks','BSidesJackson','Chief_McConnell','subtlepattern','yinnus','WebBreacher', 'zeroSteiner', 'thepacketrat')")

#cur.execute("delete from users WHERE ScreenName in ('McAfee_News')")

print cur.fetchall()
conn.commit()
conn.close()
