from pydantic import BaseModel, Field
from typing import Optional, List

class Barang(BaseModel) :
    nama_barang: str
    harga: float
    deskripsi: str
    # gambar: Optional[list] = Field([])

class BuatGambar(BaseModel) :
    # nama_barang: Optional[str] = Field(None)
    # harga: Optional[float] = Field(None)
    # deskripsi: Optional[str] = Field(None)
    gambar: list

class BuatDeleteGbr(BaseModel) :
    gambar: str
