from koneksi import conn
from fastapi import FastAPI, HTTPException, Security, Depends, File, UploadFile, Request
from fastapi.responses import JSONResponse, FileResponse

import pandas as pd
import json
import ast
import uuid
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

logging.basicConfig(level=logging.DEBUG)

IMAGEDIR = "images/bukti_byr"

from authnya import access_security, refresh_security
from fastapi_jwt import (
    JwtAccessBearerCookie,
    JwtAuthorizationCredentials,
    JwtRefreshBearer
)

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

# Cek Autentikasi. Setiap function router, dikasih parameter. cth loggedIn = authMiddle. 
# Biar dia cek dlu sblm masuk ke router. g perlu dipake dlm function
def checkLogin(
    credential: JwtAuthorizationCredentials = Security(access_security)
) :
    if not credential :
        raise HTTPException(status_code=401, detail="Admin Unauthorized")
    return credential.subject

authMiddle = Depends(checkLogin)
# End Otentikasi

@app.get('/buktibayar/{filename}')
def get_img(filename: str): 
    img_path = os.path.join(IMAGEDIR, filename)
    return FileResponse(img_path, media_type="image/png")

@app.get('/dataOrderan')
def getDataOrder(
    loggedIn = authMiddle
) : 
    cursor = conn.cursor()
    try:
        #Inspect aja satu satu pakai print() klo bingung
        query = """
            SELECT j.nojual, j.tgltransaksi, j.grandtotal, j.pelanggan_id, j.buktiByr, b.nama_barang, b.gambar, jd.* FROM tbjual j 
            JOIN tbjualdetil jd ON j.nojual = jd.nojual_id
            JOIN tbbarang b ON jd.id_barang = b.id
            ORDER BY j.nojual DESC, j.tgltransaksi DESC
        """

        cursor.execute(query)
        column_names = [kolom[0] for kolom in cursor.description]
        items = cursor.fetchall()
        #Buat dia ke bentuk Json dengan dataFrame
        df = pd.DataFrame(items, columns=column_names)

        # Bagian ini ceritany mw buat nested json object. dimana parentny adlh tbjual
        # dan childny adlh tbjualdetil. tujuanny agar g ad redudansi pas d panggil ke frontend
        # Semacam nosql gt lah relasi one to many.

        # Init Empty Dict utk simpan hasilny
        data = {}

        for index,row in df.iterrows() :
            nojual = row['nojual']
            # Jika nojual tidak ada divariable data maka tambahin ke dalam variabel data
            """
            Without this check, if there are multiple tbjualdetil records with the same nojual, 
            the code would keep replacing the jualdetil list of the nojual entry in data, 
            instead of appending to it. As a result, for each nojual, 
            only the last tbjualdetil record would be kept in the jualdetil list, 
            and the others would be lost. This is why the check if nojual not in data: is necessary.
            """
            if nojual not in data:
                #ini adalah key, bukan index. jadi kaya data['jual0001'] gt
                data[nojual] = {
                    # ini fields dari tbjual j
                    'nojual': nojual,
                    'tgltransaksi': row['tgltransaksi'].strftime('%Y-%m-%d'),
                    'grandtotal': row['grandtotal'],
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

            # tambah varjualdetil ke jualdetil array yg diletak di data['nojual']
            if nojual in data: 
                #mengapa manggil datanya spt ini ? 
                """
                {
                    "JUAL00001": {
                        "nojual": "JUAL00001",
                        "tgltransaksi": "2024-03-18",
                        "grandtotal": 95460,
                        "pelanggan_id": "123",
                        "buktiByr": "bukti.jpg",
                        "status_order": "PENDING",
                        "jualdetil": []
                    }
                }
                ini masih bentuk object / dict, belum bentuk array. 
                sehingga ini adlh contoh datanya
                """
                data[nojual]['jualdetil'].append(jualdetil)
            else: 
                print(f"Nojual {nojual} does not exist in tbjual.")

        
        data = list(data.values()) #disini diubahlah data yg bentuk dict menjadi array, lalu key yang "JUAL0001" dihapus
        json_data = json.dumps(data) # ini bentuk json, tp string, bkn json asli.

        return json_data # nanti difrontend, wajib kasih JSON.parse(res.data)    
        #Supaya kebaca dalam bentuk json asli.
    except HTTPException as e: 
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    
    finally :
        cursor.close()


@app.put('/dataOrderan/{nojual}')
async def updateData(
    request: Request,
    nojual: str,
    loggedIn = authMiddle,
) : 
    cursor = conn.cursor()
    try:
        # Pakai multipart/form-data di requestnya
        form_data = await request.form()

        if form_data['status_orderan'] == 'process' :
            #Proses 
            q0 = "SELECT grandtotal FROM tbjual WHERE NOJUAL = %s"
            cursor.execute(q0, (nojual, ))

            colNames = [kol[0] for kol in cursor.description]
            items = cursor.fetchall()

            df = pd.DataFrame(items, columns=colNames)
            jsonDF = df.to_dict('records')

            gTotal = jsonDF[0]['grandtotal']
            bayarCash = form_data['bayar_cash']

            kembalian = 0
            rumus = int(bayarCash) - int(gTotal)
            if rumus == 0 :
                kembalian = 0
            elif rumus < 0: 
                raise HTTPException(status_code=402, detail="Bayaran Kurang dari Total")
            else:
                kembalian = rumus
            
            q1 = "UPDATE tbjual SET status_order = 'BREWING', bayar_cash = %s, kembalian = %s WHERE nojual = %s"
            cursor.execute(q1, (bayarCash, kembalian,  nojual))

            q2 = "UPDATE tbjualdetil SET status_order = 'BREWING' WHERE nojual_id = %s"
            cursor.execute(q2, (nojual, ))

            conn.commit()
            return "Bisa Update"
        else:
            # Ini Update Status jadi Done
            q1 = "UPDATE tbjual SET status_order = 'DONE' WHERE nojual = %s"
            cursor.execute(q1, (nojual, ))

            q2 = "UPDATE tbjualdetil SET status_order = 'DONE' WHERE nojual_id = %s"
            cursor.execute(q2, (nojual, ))

            conn.commit()
            return "Bisa Update"

    except HTTPException as e:
        q1 = "ROLLBACK"
        cursor.execute(q1)

        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    finally:
        cursor.close() 




@app.get('/dataPenjualan')
def getDataOrder(
    loggedIn = authMiddle
) : 
    cursor = conn.cursor()
    try:
        qJual = """
            SELECT 
                DATE_FORMAT(tgltransaksi, '%Y-%m') AS month, 
                COUNT(*) AS totalSales 
            FROM 
                tbjual 
            WHERE 
                tgltransaksi >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) 
            GROUP BY 
                month
            ORDER BY 
                month ASC
        """
        cursor.execute(qJual)
        colJual = [kolom[0] for kolom in cursor.description]
        itemJual = cursor.fetchall()

        # Buat Ke bentuk json dgn dataframe
        dfJual = pd.DataFrame(itemJual, columns=colJual) # ini blm bntk json
        arrJual = dfJual.to_dict('records') # ini bentuk json
        return arrJual
    
        #sbnrny qty ga boleh 0. ini sementara aja pake if
        # qJualDetil = "SELECT *, IF(qty>0, qty, 1) AS qtyAlias FROM tbjualdetil WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) "
        # cursor.execute(qJualDetil)
        # colJualDetil = [kolom[0] for kolom in cursor.description]
        # itemJualDetil = cursor.fetchall()

        # # Buat Ke bentuk json dgn dataframe
        # dfJualDetil = pd.DataFrame(itemJualDetil, columns=colJualDetil) # ini blm bntk json
        # arrJualDetil = dfJualDetil.to_dict('records') # ini bentuk json
        # return arrJualDetil

    except HTTPException as e: 
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    
    finally :
        cursor.close()

@app.get('/dataItemTerjual')
def getDataItemTerjual(
    loggedIn = authMiddle
) : 
    cursor = conn.cursor()
    try:
        #Query untuk statistik pembelian item terbanyak
        qTerbanyak = """
            SELECT b.nama_barang, jd.id_barang, COUNT(jd.id_barang) AS countdata 
            FROM tbjualdetil jd JOIN tbbarang b ON jd.id_barang = b.id 
            GROUP BY jd.id_barang 
            ORDER BY countdata DESC 
            LIMIT 6
        """
        cursor.execute(qTerbanyak)
        column_terbanyak = [kolom[0] for kolom in cursor.description]
        itemTerbanyak = cursor.fetchall()

        # Buat Ke bentuk json dgn dataframe
        dfTerbanyak = pd.DataFrame(itemTerbanyak, columns=column_terbanyak) # ini blm bntk json
        arrTerbanyak = dfTerbanyak.to_dict('records') # ini bentuk json
        #End Query untuk statistik pembelian item terbanyak

        # Start Query Penjualan Gelas Minuman Bulan ini
        qThisMonth = """
            SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, SUM(IF(qty>0, qty, 1)) AS totalSales 
            FROM tbjualdetil WHERE YEAR(created_at) = YEAR(CURDATE()) 
            AND MONTH(created_at) = MONTH(CURDATE()) 
            GROUP BY month
        """
        cursor.execute(qThisMonth)
        colThisMonth = [kolom[0] for kolom in cursor.description]
        itemThisMonth = cursor.fetchall()

        dfThisMonth = pd.DataFrame(itemThisMonth, columns=colThisMonth)
        arrThisMonth = dfThisMonth.to_dict('records')[0]
        # End Penjualan Gelas Minuman

        return {
            'arrTerbanyak': arrTerbanyak,
            'arrThisMonth': arrThisMonth,
        }
    except HTTPException as e: 
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    
    finally :
        cursor.close()

@app.get('/dataOmset/{optValue}')
def Omset(
    optValue: str,
    loggedIn = authMiddle,
) :
    cursor = conn.cursor()
    try:
        kondisi = ""
        if optValue == "hari":
            kondisi = "WHERE DATE(tgltransaksi) = DATE(CURDATE())"
        if optValue == "bulan":
            kondisi = "WHERE MONTH(tgltransaksi) = MONTH(CURDATE())"
        if optValue == "tahun":
            kondisi = "WHERE YEAR(tgltransaksi) = YEAR(CURDATE())"

        qOmset = f"""
            SELECT SUM(grandtotal) AS grandtotal FROM tbjual {kondisi}
        """ 
        cursor.execute(qOmset)
        colOmset = [kolom[0] for kolom in cursor.description]
        itemOmset = cursor.fetchall()

        dfOmset = pd.DataFrame(itemOmset, columns=colOmset)
        arrOmset = dfOmset.to_dict('records')[0]

        qTrans = f"""
            SELECT COUNT(*) AS jlhTrans FROM tbjual {kondisi}
        """
        cursor.execute(qTrans)
        colTrans = [kolom[0] for kolom in cursor.description]
        itemTrans = cursor.fetchall()

        dfTrans = pd.DataFrame(itemTrans, columns=colTrans)
        arrTrans = dfTrans.to_dict('records')[0]

        return {
            'omset': arrOmset,
            'transaksi': arrTrans
        }
    except HTTPException as e:
        return JSONResponse(content={"error": str(e)}, status_code=e.status_code)
    finally:
        cursor.close()




