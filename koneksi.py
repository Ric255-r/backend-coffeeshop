import MySQLdb

#Config DB
db_config = {
    'host': 'localhost',
    'user': 'root',
    'passwd' : '',
    'db' : 'db_testkasir'
}

#Buat Koneksi
conn = MySQLdb.connect(**db_config)
