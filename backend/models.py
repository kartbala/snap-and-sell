from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel
from backend.database import get_connection, DEFAULT_DB_PATH


# --- Pydantic models ---

class ListingCreate(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    condition: str | None = None
    asking_price: float | None = None
    min_price: float | None = None
    original_price: float | None = None
    purchase_date: str | None = None
    purchase_source: str | None = None
    location: str | None = None


class ListingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    condition: str | None = None
    asking_price: float | None = None
    min_price: float | None = None
    original_price: float | None = None
    purchase_date: str | None = None
    purchase_source: str | None = None
    status: str | None = None
    location: str | None = None


class ListingResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    category: str | None = None
    condition: str | None = None
    asking_price: float | None = None
    min_price: float | None = None
    original_price: float | None = None
    purchase_date: str | None = None
    purchase_source: str | None = None
    status: str
    location: str | None = None
    created_at: str
    updated_at: str


class OfferCreate(BaseModel):
    listing_id: int
    buyer_name: str
    buyer_phone: str
    buyer_email: str | None = None
    offer_amount: float
    message: str | None = None


class OfferResponse(BaseModel):
    id: int
    listing_id: int
    buyer_name: str
    buyer_phone: str
    buyer_email: str | None = None
    offer_amount: float
    message: str | None = None
    status: str
    response_message: str | None = None
    created_at: str


class PhotoResponse(BaseModel):
    id: int
    listing_id: int
    file_path: str
    is_primary: bool


# --- CRUD functions ---

def create_listing(data: ListingCreate, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """INSERT INTO listings (title, description, category, condition,
           asking_price, min_price, original_price, purchase_date,
           purchase_source, location)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.title, data.description, data.category, data.condition,
         data.asking_price, data.min_price, data.original_price,
         data.purchase_date, data.purchase_source, data.location),
    )
    conn.commit()
    lid = cursor.lastrowid
    conn.close()
    return lid


def get_listing(lid: int, db_path: str = DEFAULT_DB_PATH) -> ListingResponse | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (lid,)).fetchone()
    conn.close()
    if row is None:
        return None
    return ListingResponse(**dict(row))


def list_listings(
    status: str | None = None, db_path: str = DEFAULT_DB_PATH
) -> list[ListingResponse]:
    conn = get_connection(db_path)
    if status:
        rows = conn.execute(
            "SELECT * FROM listings WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM listings ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [ListingResponse(**dict(r)) for r in rows]


def update_listing(
    lid: int, data: ListingUpdate, db_path: str = DEFAULT_DB_PATH
) -> bool:
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        return False
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [lid]
    conn = get_connection(db_path)
    cursor = conn.execute(
        f"UPDATE listings SET {set_clause} WHERE id = ?", values
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def batch_update_status(
    ids: list[int], new_status: str, db_path: str = DEFAULT_DB_PATH
) -> int:
    if not ids:
        return 0
    conn = get_connection(db_path)
    placeholders = ", ".join("?" for _ in ids)
    now = datetime.now().isoformat()
    cursor = conn.execute(
        f"UPDATE listings SET status = ?, updated_at = ? WHERE id IN ({placeholders})",
        [new_status, now] + ids,
    )
    conn.commit()
    count = cursor.rowcount
    conn.close()
    return count


def delete_listing(lid: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    conn = get_connection(db_path)
    cursor = conn.execute("DELETE FROM listings WHERE id = ?", (lid,))
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def create_offer(data: OfferCreate, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """INSERT INTO offers (listing_id, buyer_name, buyer_phone, buyer_email,
           offer_amount, message)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data.listing_id, data.buyer_name, data.buyer_phone, data.buyer_email,
         data.offer_amount, data.message),
    )
    conn.commit()
    oid = cursor.lastrowid
    conn.close()
    return oid


def list_offers(
    listing_id: int | None = None, db_path: str = DEFAULT_DB_PATH
) -> list[OfferResponse]:
    conn = get_connection(db_path)
    if listing_id:
        rows = conn.execute(
            "SELECT * FROM offers WHERE listing_id = ? ORDER BY created_at DESC",
            (listing_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM offers ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [OfferResponse(**dict(r)) for r in rows]


def update_offer_status(
    oid: int, status: str, message: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> bool:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "UPDATE offers SET status = ?, response_message = ? WHERE id = ?",
        (status, message, oid),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def add_photo(
    listing_id: int, file_path: str, is_primary: bool,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO photos (listing_id, file_path, is_primary) VALUES (?, ?, ?)",
        (listing_id, file_path, int(is_primary)),
    )
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def get_photos(
    listing_id: int, db_path: str = DEFAULT_DB_PATH
) -> list[PhotoResponse]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM photos WHERE listing_id = ? ORDER BY is_primary DESC",
        (listing_id,),
    ).fetchall()
    conn.close()
    return [PhotoResponse(**{**dict(r), "is_primary": bool(r["is_primary"])}) for r in rows]
