import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from koneksi import conn

from fastapi import FastAPI, HTTPException, Security, Depends, File, UploadFile, Request
from fastapi.responses import JSONResponse

import pandas as pd
import uuid

from authnya import access_security, refresh_security
from fastapi_jwt import (
    JwtAccessBearerCookie,
    JwtAuthorizationCredentials,
    JwtRefreshBearer
)

from modelsnya.modelUser import User, LoginUser

from typing import List
from datetime import date

import MySQLdb
import json
import ast
from fastapi.middleware.cors import CORSMiddleware

IMAGEDIR = "images/bukti_byr/"

app = FastAPI()
today = date.today()

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

# Alur Transaksi
# /start_transaction -> /bukaNota -> /detailPenjualan -> finalizeTransaction
# /cancel dapat dilakukan sblm finalize


def handle_penjualan_start() :
    cursor = conn.cursor()
    try:
        # q0 = "START TRANSACTION"
        # cursor.execute(q0)
        q1 = "SELECT nojual FROM temptbjual ORDER BY nojual DESC LIMIT 1"
        cursor.execute(q1)
        itemsJual = cursor.fetchone()

        # nojual = itemsJual[0] #Ambil nojual

        if itemsJual is None:
            q2 = "SELECT nojual FROM tbjual ORDER BY nojual DESC LIMIT 1"
            cursor.execute(q2)
            itemsJual2 = cursor.fetchone()

            if itemsJual2 is None : 
                idjual = "JUAL00001"
                nojual = idjual[4:9]
                resNoJual = nojual
            else:
                idjual = itemsJual2[0]
                nojual_before = idjual[4:9] # Ambil dari Index ke 4 smpe end. cth "JUAL00001"
                intNoJual = int(nojual_before) + 1
                resNoJual = str(intNoJual)
        else:
            idjual = itemsJual[0]
            nojual_before = idjual[4:9] # Ambil dari Index ke 4 smpe end. cth "JUAL00001"
            intNoJual = int(nojual_before) + 1
            resNoJual = str(intNoJual)
        
        modIdJual = "JUAL"+resNoJual.zfill(5) #modif idjual jd padleft
        return modIdJual
    
    except HTTPException as e:
        # qD = "ROLLBACK"
        # cursor.execute(qD)

        return {
            "Error" : str(e)
        }
    finally:
        cursor.close()

# Ambil Nomor Transaksi
@app.get('/startTransaction')
def start_transaction() :
    return {
        "nojual" : handle_penjualan_start()
    }

# Ini Pas Pencet Menu New Transaksi Di FrontEnd
@app.post('/bukaNota/{transaction_num}')
def submit_form(transaction_num : str) :
    cursor = conn.cursor()
    try:
        qIns = "INSERT INTO temptbjual (nojual, nofaktur, tgltransaksi, id_user, created_at) values (%s, %s, %s, %s, %s)"
        cursor.execute(qIns, (transaction_num, '1', today, 'KASIR', today))
        conn.commit()

        return {
            "Success" : "Form Berhasil Submit"
        }
        # if isCancelled:
        #     raise HTTPException(status_code=499, detail="Transaksi Dibatalkan")
        # else:
        #     conn.commit()

    except Exception as e:
        qD = "ROLLBACK"
        cursor.execute(qD)

        return {
            "Error" : str(e)
        }
    
@app.delete('/cancelTransaction/{transaction_num}') 
def cancel_transaction(transaction_num: str) :
    cursor = conn.cursor()
    try:
        q1 = "DELETE FROM temptbjual WHERE nojual = %s"
        cursor.execute(q1, (transaction_num, ))
        conn.commit()

        q2 = "DELETE FROM temptbjualdetil WHERE nojual_id = %s"
        cursor.execute(q2, (transaction_num, ))
        conn.commit()

        return {
            "message" : "Transaksi Dibatalkan"
        }
    except Exception as e:
        return {
            "Error" : str(e)
        }
    finally :
        cursor.close()

@app.post('/finalizeTransaction/{transaction_num}')
async def finalize_transaction(transaction_num: str, buktiByr: UploadFile) :
    cursor = conn.cursor()
    try :
        #Start input file. Cek Direktori Exists
        if not os.path.exists(IMAGEDIR) :
            os.makedirs(IMAGEDIR)

        #Buat Nama Unique and Define Folder
        filename = f"{uuid.uuid4()}.jpg"
        file_location = os.path.join(IMAGEDIR, filename)
        #Read Filenya
        content = await buktiByr.read()
        with open(file_location, "wb") as f:
            f.write(content)
        #End input file

        q1 = """
            INSERT INTO tbjual SELECT * FROM temptbjual WHERE nojual = %s
        """
        cursor.execute(q1, (transaction_num, ))
        conn.commit()

        q2 = """
            INSERT INTO tbjualdetil(id_barang, nojual_id, ukuran_cup, variant, ice_cube, sweetness, milk, syrup, espresso, topping, harga_awal, harga_akhir, qty, harga_seluruh, status_order, created_at, updated_at)
            SELECT id_barang, nojual_id, ukuran_cup, variant, ice_cube, sweetness, milk, syrup, espresso, topping, harga_awal, harga_akhir, qty, harga_seluruh, status_order, created_at, updated_at FROM temptbjualdetil WHERE nojual_id = %s
        """
        cursor.execute(q2, (transaction_num, ))
        conn.commit()
        
        qSubTotal = """
            SELECT SUM(harga_seluruh) FROM temptbjualdetil WHERE nojual_id = %s;
        """
        cursor.execute(qSubTotal, (transaction_num, ))
        arrSubTotal = cursor.fetchone()
        SubTotal = arrSubTotal[0]
    
        pajak = 0.11
        rumusPajak = SubTotal * pajak
        grandTotal = SubTotal + rumusPajak
        bayarCash = 1000000
        kembalian = bayarCash - grandTotal

        q2 = """
            UPDATE tbjual SET payment = %s, pajak = %s, subtotal = %s, grandtotal = %s, bayar_cash = %s, 
            kembalian = %s, buktiByr = %s, updated_at = %s where nojual = %s
        """
        cursor.execute(q2, ('CASH', pajak, SubTotal, grandTotal, bayarCash, kembalian, filename, today, transaction_num))
        conn.commit()

        qD = "DELETE FROM temptbjual WHERE nojual = %s"
        cursor.execute(qD, (transaction_num, ))
        conn.commit()

        qD1 = "DELETE FROM temptbjualdetil WHERE nojual_id = %s"
        cursor.execute(qD1, (transaction_num, ))
        conn.commit()

        return "Data Sudah Masuk"
    except Exception as e:
        conn.rollback()
        return {
            "Error" : str(e)
        }


@app.post('/detailPenjualan')
async def jualDetil(
    request: Request
) :
    cursor = conn.cursor()
    try:
        q1 = "START TRANSACTION"
        cursor.execute(q1)

        form_data = await request.form()

        id_barang = form_data['id_barang']
        # nama_barang = form_data['nama_barang']
        nojual_id = form_data['nojual_id']
        ukuran_cup = form_data['ukuran_cup']
        variant = form_data['variant']
        ice_cube = form_data['ice_cube']
        sweetness = form_data['sweetness']
        milk = form_data['milk']
        topping = form_data['topping']
        arrTopping = ast.literal_eval(topping) #Hrs ubh ke ini. klo g dibaca array ada stringnya."[]"
        # harga_awal = form_data['harga_awal']
        syrup = form_data['syrup']
        arrSyrup = ast.literal_eval(syrup)
        qty = form_data['qty']
        espresso = form_data['espresso']

        #q2 Sementara. nanti difrontend select pake id
        q2 = "SELECT * FROM tbbarang WHERE id = %s"
        cursor.execute(q2, (id_barang, ))
        colTbBarang = [kolom[0] for kolom in cursor.description]

        itemsTbBarang = cursor.fetchone() #krn make fetchone, maka arg didataframe hrs d array
        df = pd.DataFrame([itemsTbBarang], columns=colTbBarang) #buat ubh ke bentuk json
        jsonTbBarang = df.to_dict('records')[0]

        if itemsTbBarang is not None :
            q3 = f"SELECT * FROM tbtopping"
            cursor.execute(q3)

            colTbTopping = [kolom[0] for kolom in cursor.description]
            itemsTbTopping = cursor.fetchall()

            df2 = pd.DataFrame(itemsTbTopping, columns=colTbTopping)
            jsonTbTopping = df2.to_dict('records')

            temp_harga = []
            temp_harga.append(float(jsonTbBarang['harga']))

            if len(arrTopping) > 2 :
                raise ValueError("Ga Boleh Pilih Lebih Dr Dua")
            
            if len(arrSyrup) > 1 :
                raise ValueError("Ga Boleh Pilih Dari Satu")

            for i in jsonTbTopping :
                if i['nama_topping'] == ukuran_cup :
                    temp_harga.append(float(i['harga']))
                if i['nama_topping'] == milk:
                    temp_harga.append(float(i['harga']))
                if i['nama_topping'] == espresso:
                    temp_harga.append(float(i['harga']))
                for j in arrTopping :
                    if i['nama_topping'] == j :
                        temp_harga.append(float(i['harga']))

                for k in arrSyrup :
                    if i['nama_topping'] == k :
                        temp_harga.append(float(i['harga']))
            
            #Tambahan 11/03/24
            hrgStlhTopping = int(qty) * sum(temp_harga)
            #End Tambahan

            qInsDetil = "INSERT INTO temptbjualdetil values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(qInsDetil, ('', jsonTbBarang['id'], nojual_id, ukuran_cup, variant, ice_cube, sweetness, milk, json.dumps(arrSyrup), espresso, json.dumps(arrTopping), jsonTbBarang['harga'], sum(temp_harga), qty, hrgStlhTopping, 'PENDING', today, ''))
            conn.commit()

            # return sum(temp_harga)
            return hrgStlhTopping

        else :
            return "Barang Kosong"

    
    except ValueError as e:
        qD = "ROLLBACK"
        cursor.execute(qD)
        print(e)

        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        qD = "ROLLBACK"
        cursor.execute(qD)
        print(e)

        raise HTTPException(status_code=500, detail=str(e))    

# new 27/02/24
@app.get('/detailPenjualan/{trans_num}')
def getDataPenjualan(
    request: Request,
    trans_num: str
) :
    cursor = conn.cursor()
    try :
        q1 = "SELECT b.nama_barang, b.harga, b.gambar, b.source_data, temp.* FROM temptbjualdetil temp JOIN tbbarang b ON temp.id_barang = b.id WHERE temp.nojual_id = %s"
        cursor.execute(q1, (trans_num, ))
        colTempJualDetil = [kol[0] for kol in cursor.description]
        items1 = cursor.fetchall()

        df1 = pd.DataFrame(items1, columns=colTempJualDetil)

        return df1.to_dict('records')
    
    except Exception as e: 

        raise HTTPException(status_code=500, detail=str(e))
    
    finally: 
        cursor.close()


@app.post('/testing') #Msh Perlu d perbaiki. Tergantung alur FrontEnd
def insertData(
    request: Request,
) :
    # Note. conn.commit() = "COMMIT" di MySQL
    cursor = conn.cursor()
    try:
        q1 = "START TRANSACTION"
        cursor.execute(q1)

        for i in range(1,10) :
            q2 = "INSERT INTO tbjual values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(q2, ('JUAL00{angka}'.format(angka=i), 1, '2023-02-02', 'PEL002', 'CASH', 0, 20000, 50000, 'paula', 100000, 50000,'',''))
            conn.commit() #Commit ini dapat kita anggap sbg Checkpoint dalam Game.

            if i == 7 :
                qD = "DELETE FROM tbjual"
                cursor.execute(qD)
                # conn.commit() ini g blh d commit
                raise MySQLdb.Error("Anjir Kehapus WOi")

    except (MySQLdb.Error, MySQLdb.Warning) as e :
        """
        Jd Query ini alurnya, aku udah ins smpe 7 data yg sudh dicommit (checkpoint), lalu g sengaja ngehapus data 
        pas iterate ke 7, dia raise error, langsung lompat ke block except. jd ga looping smpe 9x.
        stelah itu  ak rollback ke checkpoint sebelumnya. ke 7 data yg sudah dicommit.

        kalau aku commit yg ak g sengaja delete di TRY, maka dia bkl timpa checkpointnya diQuery
        delete yang berarti checkpointnya ada di DataKosong,
        Referensi : https://www.youtube.com/watch?v=GOQVlrQohtM
        """

        print(str(e))
        qR = "ROLLBACK"
        cursor.execute(qR)

    except HTTPException as e :
        qR = "ROLLBACK"
        cursor.execute(qR)
        return {
            "error": str(e)
        }
    
    finally : 
        cursor.close()

            
"""
CASE KALAU MAU ROLLBACK SELURUH TRANSACTION JIKALAU AD ERROR
PENJELASAN : 
In your original code, with conn.commit() inside the loop, each iteration commits the changes 
immediately. Therefore, when an exception occurs, the transaction has already been committed, 
and the changes made in previous iterations are permanent.

If you want to roll back the entire transaction if any exception occurs at any point within the loop, 
you should not commit inside the loop at all. Only commit once at the end, after the loop 
has completed.

@app.post('/testing')
def insertData(
    request: Request,
    credential: JwtAuthorizationCredentials = Security(access_security)
):
    cursor = conn.cursor()
    
    try:
        q1 = "START TRANSACTION"
        cursor.execute(q1)

        for i in range(1, 10):
            ins = "INSERT INTO tbjual VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(ins, ('JUAL00{angka}'.format(angka=i), 1, '2023-02-02', 'PEL002', 'CASH', 0, 20000, 50000, 'paula', 100000, 50000, '', ''))

            if i == 7:
                qD = "DELETE FROM tbjual"
                cursor.execute(qD)
                raise HTTPException(404, detail="Anjir Kehapus")

        # Commit the changes only once after the loop
        conn.commit()

    except (MySQLdb.Error, MySQLdb.Warning) as e:
        print(str(e))
        qR = "ROLLBACK"
        cursor.execute(qR)

    except HTTPException as e:
        qR = "ROLLBACK"
        cursor.execute(qR)
        return {"error": str(e)}

    finally:
        cursor.close()



"""