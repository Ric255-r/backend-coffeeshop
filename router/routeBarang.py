# Bisa Lihat Contoh di RouteTesting.py
# Referensi https://tutorial101.blogspot.com/2023/02/fastapi-upload-image.html
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modelsnya.modelBarang import Barang, BuatGambar, BuatDeleteGbr
from koneksi import conn

from fastapi import FastAPI, HTTPException, Security, Depends, File, UploadFile, Request
from fastapi.responses import JSONResponse, FileResponse

import pandas as pd
import json
import ast
import uuid
from fastapi.middleware.cors import CORSMiddleware


IMAGEDIR = "images/"

from authnya import access_security, refresh_security
from fastapi_jwt import (
    JwtAccessBearerCookie,
    JwtAuthorizationCredentials,
    JwtRefreshBearer
)

from modelsnya.modelUser import User, LoginUser

from typing import List


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

# Bs pk cara ini, atau cara masukin credential ke masing2 param function spt routeUser/me
def checkLogin(credential: JwtAuthorizationCredentials = Security(access_security)) :
    if not credential : 
        raise HTTPException(status_code=401, detail="Unauthorized Woi")
    return credential.subject

authmiddle = Depends(checkLogin)
#End Cara

@app.get('/images/{filename}')
def get_img(filename: str) :
    img_path = os.path.join(IMAGEDIR, filename)
    return FileResponse(img_path, media_type="image/png")

@app.get('/barang')
def indexBrg(loggedIn = authmiddle) :
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM tbbarang"
        cursor.execute(query)

        column_names = [kolom[0] for kolom in cursor.description]

        items = cursor.fetchall()

        if not items : 
            raise HTTPException(status_code=404, detail="Item G Ad")
        
        # dataFrame
        df = pd.DataFrame(items, columns=column_names)
        df['gambar'] = df['gambar'].apply(lambda x_gbr: json.loads(x_gbr) if x_gbr.strip() else x_gbr)

        return df.to_dict('records') # Convert to dict instead of list jadiny JSON
    except HTTPException as e: 
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    
    finally :
        cursor.close()

# Diatas Adalah Cara Load DataFrame pakai Lambda,
# Yg ini aku g pake lambda. buat func tersendiri supaya tau cara kerjanya
def gambarJson(x) :
    if x.strip() :
        return json.loads(x)
    else:
        return x
@app.get('/barang/{item_id}')
def single_brg(item_id: int, loggedIn = authmiddle):
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM tbbarang WHERE id = %s"
        cursor.execute(query, (item_id,))

        column_names = [kol[0] for kol in cursor.description] 
        items = cursor.fetchall() # Ini biarin pake fetchall aja, biar return array.
        # kalo pake fetchone() dia return 1 records aj, lalu items di dataframe hrs diarraykan

        # df = pd.DataFrame([items], columns=column_names) cth klo pake fetchone()
        df = pd.DataFrame(items, columns=column_names) 
        df['gambar'] = df['gambar'].apply(gambarJson) # g ush isi parameter. penjelasan d routeTesting

        # Start Ambil DataTopping
        query2 = "SELECT * FROM tbtopping ORDER BY harga ASC, nama_topping"
        cursor.execute(query2)

        column_names2 = [kol[0] for kol in cursor.description]
        items2 = cursor.fetchall()
        df2 = pd.DataFrame(items2, columns=column_names2)
        #End Data Topping

        return {
            'dataBarang': df.to_dict('records')[0], # ini returnny jd obj krn cmn ambil 1
            'dataTopping' : df2.to_dict('records')
        }
    except Exception as e:
        return {
            "Error" : str(e)
        }
    finally :
        cursor.close()

# INi udah jalan, kalau muncul stream error atau error apapun, buka tab baru postman
@app.post('/barang')
async def addData(
    request: Request, 
    loggedIn = authmiddle,
    gambar: List[UploadFile] = File(...)
) :
    cursor = conn.cursor()
    try: 
        uploaded_file = []
        form_data = await request.form()

        # Ambil data dr FormData
        nama_barang = form_data['nama_barang']
        harga = form_data['harga']
        deskripsi = form_data['deskripsi']

        for file in gambar : # Ambil Gbr di Python Ntah np hrs d jadiin parameter
            file.filename = f"{uuid.uuid4()}.jpg"
            content = await file.read()

            #Simpan FIlenya
            with open(f"{IMAGEDIR}{file.filename}", "wb") as f:
                f.write(content)

            uploaded_file.append(file.filename)
        
        # Convert the list to a JSON-formatted string
        gambar_json = json.dumps(uploaded_file)

        query = "INSERT INTO tbbarang (nama_barang, harga, deskripsi, gambar) values(%s, %s, %s, %s)"
        cursor.execute(query, (nama_barang, harga, deskripsi, gambar_json))
        conn.commit()
        return "Bisa Isi"

    except Exception as e: 
        return {
            "Error": str(e)
        }
    finally:
        cursor.close()

@app.post('/barang/{id}')
async def update_data(
    id: int, 
    request: Request,
    gambar: List[UploadFile] = File(...),
    loggedIn = authmiddle
) :
    try :
        cursor = conn.cursor()

        uploaded_file = []

        form_data = await request.form()
        #Ambil Form Data
        nama_barang = form_data['nama_barang']
        harga = form_data['harga']
        deskripsi = form_data['deskripsi']

        for file in gambar:
            file.filename = f"{uuid.uuid4()}.jpg"
            content = await file.read()

            #simpan filenya
            with open(f"{IMAGEDIR}{file.filename}", "wb") as f:
                f.write(content) 

            uploaded_file.append(file.filename)
        
        gambarJson = json.dumps(uploaded_file)        
        query = "UPDATE tbbarang SET nama_barang=%s, harga=%s, deskripsi=%s where id = %s"
        # Convert the list to a JSON-formatted string
        # gambar_json = json.dumps(isi.gambar)
        cursor.execute(query, (nama_barang, harga, deskripsi, id))
        conn.commit()
        cursor.close()

    except Exception as e: 
        return {
            "Error": str(e)
        }
    
@app.delete('/barang/{id}')
def delete_item(id : int, loggedIn = authmiddle) :
    try :
        cursor = conn.cursor()
        query = "DELETE FROM tbbarang where id = %s"
        cursor.execute(query, (id,)) # Harus dikoma stelah id. krn single-element bentuk tuple.
        conn.commit()
        cursor.close()
        return {
            "message": "Sukses Hapus"
        }
    except Exception as e: 
        return {
            "error": str(e)
        }

# Besok Coba Update Gambar Aja. note 05/02/2024
@app.put('/updateGambar/{id}')
async def update_gambar(
    id: int, 
    gambar: List[UploadFile] = File(...), 
    loggedIn = authmiddle
) :
    try: 
        cursor = conn.cursor()
        q1 = "SELECT * FROM tbbarang WHERE id = %s"
        cursor.execute(q1, (id,))

        # print("Cursor Desc : ", cursor.description) buat debug aja

        items = cursor.fetchone()

        listIsi = list(items) # ini returnny list lengkap record. tp bentuk string.
        gbr = listIsi[4]  # ini returnny "[\"cappucino.jpg\", \"coffee.jpg\"]"
        convertGbr = ast.literal_eval(gbr) #Convert Ke List Beneran

        print(f"Isi COnvert Gbr adlh {convertGbr}")

        # convertGbr = ["panas.jpg", "dingin.jpg"]
        for i in gambar :
            i.filename = f"{uuid.uuid4()}.jpg"
            content = await i.read()

            with open(f"{IMAGEDIR}{i.filename}", "wb") as f :
                f.write(content)

            print(i)
            convertGbr.append(i.filename)

        # Convert the list back to a JSON-formatted string
        updated_gambar_str = json.dumps(convertGbr)

        q2 = "UPDATE tbbarang set gambar = %s WHERE id = %s"
        cursor.execute(q2, (updated_gambar_str, id))
        conn.commit()
        
        cursor.close()

        return single_brg(id)

        return "Bisa Update"

        # Ini Klo Mw Return Full Isiny. Yg Di Model uncomment jg
        # updated_isi = BuatGambar(
        #     nama_barang=str(listIsi[1]),
        #     harga=float(listIsi[2]),
        #     deskripsi=str(listIsi[3]),
        #     gambar=convertGbr
        # )
        # return updated_isi
    
    except Exception as e : 
        return {
            "Error" : str(e)
        }
    
@app.put('/deleteGambar/{id}')
def delete_gbr(id: int, isi: BuatDeleteGbr, loggedIn = authmiddle) :
    try: 
        cursor = conn.cursor()
        q1 = "SELECT * FROM tbbarang WHERE id = %s"
        cursor.execute(q1, (id,))

        items = cursor.fetchone()
        listIsi = list(items)
        gbr = listIsi[4]
        convertGbr = ast.literal_eval(gbr)

        if isi.gambar in convertGbr : 
            indexnya = convertGbr.index(isi.gambar)
        else: 
            if len(convertGbr) == 0 :
                raise HTTPException(status_code=422, detail="Foto Sudah Kosong")
            
            raise HTTPException(status_code=404, detail="Item G Ad")
        
        print(indexnya)
        try:
            removed_img = convertGbr.pop(indexnya) #Macam Splice, Hapus Berdasarkan Index
            print(f"Removed Image {removed_img}")
            print("Updated List: ", convertGbr)

            updated_gambar_str = json.dumps(convertGbr)

            q2 = "UPDATE tbbarang SET gambar = %s WHERE id = %s"
            cursor.execute(q2, (updated_gambar_str, id))
            conn.commit()

            return single_brg(id)
        except IndexError :
            print("Invalid Index")
        finally: # Walaupun Kondisiny Jalan/Nda, ttp Close Cursor
            cursor.close()

    except Exception as e :
        return {
            "error" : str(e)
        }

# Testing File Upload. Ini udh Jalan
@app.post("/upload")
async def create_upload(files: List[UploadFile] = File(...), loggedIn = authmiddle):
    uploaded_file = []

    for file in files :
        file.filename = f"{uuid.uuid4()}.jpg"
        content = await file.read()

        #Simpan FIlenya
        with open(f"{IMAGEDIR}{file.filename}", "wb") as f:
            f.write(content)

        uploaded_file.append(file.filename)

    return uploaded_file
    


