# Pakai JwtAuth yg Ini 
# https://k4black.github.io/fastapi-jwt/
from datetime import timedelta
import json
from fastapi import FastAPI, Security, HTTPException, Request
from authnya import access_security, refresh_security
from fastapi_jwt import (
    JwtAccessBearerCookie,
    JwtAuthorizationCredentials,
    JwtRefreshBearer
)
from fastapi.responses import JSONResponse
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modelsnya.modelBarang import Barang, BuatGambar, BuatDeleteGbr
from modelsnya.modelUser import User, LoginUser
from koneksi import conn
import pandas as pd
from passlib.hash import sha256_crypt
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/login')
def auth(isi: LoginUser) :
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM tbuser WHERE email=%s"
        cursor.execute(query, (isi.email,))

        column_names = [kol[0] for kol in cursor.description]
        items = cursor.fetchall()

        if not items :
            raise HTTPException(status_code=404, detail="User Tidak Ditemukan")
        
        stored_pass = items[0][2] #passwd

        if not sha256_crypt.verify(isi.passwd, stored_pass) :
            raise HTTPException(status_code=401, detail="Password Salah")
        
        df = pd.DataFrame(items, columns=column_names)

        cursor.close()
        
        # subject (actual payload) is any json-able python dict
        # subject = {"username": "username", "role": "User"}
        subject = df.to_dict('records')[0]

        # Remove the 'passwd' key from the subject dictionary
        subject.pop('passwd', None)

        # Create new access/refresh tokens pair
        access_token = access_security.create_access_token(subject=subject)
        refresh_token = refresh_security.create_refresh_token(subject=subject)

        return {"access_token": access_token, "refresh_token": refresh_token, "usernya": subject}
    except HTTPException as e :
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
        
    
@app.post("/register")
def register(isi: User) :
    cursor = conn.cursor()
    try:
        hashed_password = sha256_crypt.hash(isi.passwd)
        query = "INSERT INTO tbuser (email, passwd, status_user, roles) values (%s, %s, %s, %s)"
        cursor.execute(query, (isi.email, hashed_password, 'Karyawan', 'Admin'))
        conn.commit() 
        cursor.close()
        return isi
    except Exception as e:
        return {
            "Error" : str(e)
        }


@app.post("/refresh")
def refresh(credentials: JwtAuthorizationCredentials = Security(refresh_security)):
    # Update access/refresh tokens pair
    # We can customize expires_delta when creating
    access_token = access_security.create_access_token(subject=credentials.subject)
    refresh_token = refresh_security.create_refresh_token(subject=credentials.subject, expires_delta=timedelta(days=2))

    return {"access_token": access_token, "refresh_token": refresh_token}

@app.get("/me")
def read_curr_users(credential: JwtAuthorizationCredentials = Security(access_security)) :
    if not credential :
        raise HTTPException(status_code=401, detail="Unauthorized Woi")
    
    return {
        "email": credential['email'],
        "status_user": credential['status_user'],
        "roles": credential['roles']
    }

@app.get('/pesanan')
def pesanan(
    credential: JwtAuthorizationCredentials = Security(access_security)
) :
    if not credential:
        raise HTTPException(status_code=401, detail="Unaothorized cok")
    
    cursor = conn.cursor()
    try:
        #ini whereny hrsny pake kode pelanggan, sementara select biasa aj
        #ini carany sama kaya routeAdmin.py ada penjelasannya.
        #mau buat nested json jualdetil
        q1 = """
            SELECT j.nojual, j.tgltransaksi, j.grandtotal, j.pelanggan_id, j.buktiByr, b.nama_barang,
            b.gambar, jd.* FROM tbjual j JOIN tbjualdetil jd ON j.nojual = jd.nojual_id
            JOIN tbbarang b ON jd.id_barang = b.id
        """

        cursor.execute(q1)
        colNames = [kolom[0] for kolom in cursor.description]
        items = cursor.fetchall()

        df = pd.DataFrame(items, columns=colNames)
        data = {}

        for index,row in df.iterrows():
            nojual = row['nojual']
            if nojual not in data:
                data[nojual] = {
                    'nojual' : nojual,
                    'tgltransaksi': row['tgltransaksi'].strftime('%Y-%m-%d'),
                    'grandtotal' : row['grandtotal'],
                    'pelanggan_id': row['pelanggan_id'],
                    'buktiByr': row['buktiByr'],
                    'status_order': row['status_order'],
                    'jualdetil': []
                }

            # Buat dict utk fields tbjualdetil. amvil dari select jd.*
            jualdetil = {
                'id': row['id'],
                'id_barang': row['id_barang'],
                'nojual_id': row['nojual_id'],
                'ukuran_cup': row['ukuran_cup'],
                'variant': row['variant'],
                'ice_cube': row['ice_cube'],
                'sweetness': row['sweetness'],
                'milk': row['milk'],
                'syrup': row['syrup'],
                'espresso': row['espresso'],
                'topping': row['topping'],
                'harga_awal': row['harga_awal'],
                'harga_akhir': row['harga_akhir'],
                'qty': row['qty'],
                'harga_seluruh' : row['harga_seluruh'],
                'status_order': row['status_order'],
                'created_at': "",
                'updated_at': "",
                'nama_barang': row['nama_barang'],
                'gambar': row['gambar']
            }

            if nojual in data:
                data[nojual]['jualdetil'].append(jualdetil)
                # print(data[nojual])
            else:
                print(f"Nojual {nojual} does not exist in tbjual.")
            

        listData = list(data.values())
        json_data = json.dumps(listData)

        return json_data
    except HTTPException as e :
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    
    finally:
        cursor.close()

@app.get('/datauser/{jenisUser}')
def getAllUser(
    jenisUser: str,
    credential: JwtAuthorizationCredentials = Security(access_security)
):
    if not credential:
        raise HTTPException(status_code=401, detail="Unaothorized cok")
    
    cursor = conn.cursor()
    try:
        kondisi = ""
        if jenisUser == "Karyawan":
            kondisi = "WHERE status_user = 'Karyawan' OR roles = 'Admin'"
        else:
            kondisi = "WHERE status_user = 'Pelanggan'"

        q1 = f"SELECT * FROM tbuser {kondisi}"
        cursor.execute(q1)
        colNames = [kolom[0] for kolom in cursor.description]
        items = cursor.fetchall()

        df = pd.DataFrame(items, columns=colNames)

        return df.to_dict('records')
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    finally:
        cursor.close()
